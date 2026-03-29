import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.api.schemas.common import APIResponse
from backend.api.schemas.report import BloodParameterOut, UploadReportResponse
from backend.core.disclaimer import get_disclaimer
from backend.core.image_parser import SUPPORTED_MIME_TYPES as IMAGE_TYPES
from backend.core.image_parser import ImageParseError, parse_image
from backend.core.parser import ParseError, parse_csv
from backend.core.pdf_parser import PDFParseError, parse_pdf
from backend.core.simplifier import simplify
from backend.core.validator import validate
from backend.ml.reference_ranges import get_range

logger = structlog.get_logger()

router = APIRouter()

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_CSV_EXTENSIONS = {".csv"}
_PDF_EXTENSIONS = {".pdf"}
_IMAGE_EXTENSIONS = set(IMAGE_TYPES.keys())   # .jpg .jpeg .png .webp
_ALL_SUPPORTED = _CSV_EXTENSIONS | _PDF_EXTENSIONS | _IMAGE_EXTENSIONS


def _file_extension(filename: str) -> str:
    lower = filename.lower()
    for ext in sorted(_ALL_SUPPORTED, key=len, reverse=True):
        if lower.endswith(ext):
            return ext
    return ""


@router.post("/upload", response_model=APIResponse[UploadReportResponse])
async def upload_report(
    file: UploadFile = File(...),
    age: int = Form(default=30, ge=0, le=120),
    sex: str = Form(default="male", pattern="^(male|female)$"),
) -> APIResponse[UploadReportResponse]:
    """
    Upload a blood report — CSV, PDF, or image (JPG/PNG/WEBP).

    - **file**: Blood report file
    - **age**: Patient age (affects reference ranges)
    - **sex**: Patient sex — 'male' or 'female' (affects reference ranges)
    """
    content = await file.read()

    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    filename = file.filename or ""
    ext = _file_extension(filename)

    if not ext:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file type. Supported formats: "
                f"CSV, PDF, JPG, JPEG, PNG, WEBP."
            ),
        )

    # --- Route to the right parser ---
    try:
        if ext in _CSV_EXTENSIONS:
            parse_result = parse_csv(content)

        elif ext in _PDF_EXTENSIONS:
            parse_result = parse_pdf(content)

        else:
            mime = IMAGE_TYPES[ext]
            parse_result = await parse_image(content, mime)

    except (ParseError, PDFParseError) as exc:
        return APIResponse.fail(str(exc))
    except ImageParseError as exc:
        return APIResponse.fail(str(exc))

    if not parse_result.parameters and not parse_result.unrecognized:
        return APIResponse.fail(
            "No blood parameters could be found in the uploaded file. "
            "Please check that the file contains a blood test report."
        )

    # --- Validate physical limits ---
    validation = validate(parse_result.parameters)
    validation_error_msgs = [e.message for e in validation.errors]
    valid_params = validation.valid

    # --- Reference range lookup ---
    ranges = {}
    for param in valid_params:
        ref = get_range(param.name, age=age, sex=sex)
        if ref:
            ranges[param.name] = ref

    # --- Build output parameters ---
    output_params: list[BloodParameterOut] = []
    anomaly_count = 0
    has_critical = False

    for param in valid_params:
        ref = ranges.get(param.name)
        if ref:
            p_status = ref.classify(param.value)
            critical = ref.is_critical(param.value)
            if critical:
                has_critical = True
            if p_status != "normal":
                anomaly_count += 1
        else:
            p_status = "unknown"
            critical = False

        output_params.append(BloodParameterOut(
            name=param.name,
            raw_name=param.raw_name,
            value=param.value,
            unit=param.unit or (ref.unit if ref else ""),
            status=p_status,
            is_critical=critical,
            ref_low=ref.low if ref else None,
            ref_high=ref.high if ref else None,
            ref_unit=ref.unit if ref else None,
        ))

    # --- OpenAI simplification ---
    simplification_text: str | None = None
    simplification_cached = False

    if valid_params and ranges:
        try:
            simplification_result = await simplify(valid_params, ranges)
            if simplification_result:
                simplification_text = simplification_result.summary
                simplification_cached = simplification_result.cached
        except Exception as exc:
            logger.error("simplification_failed", error=str(exc))

    disclaimer = get_disclaimer(has_critical=has_critical, anomaly_count=anomaly_count)

    response_data = UploadReportResponse(
        parameters=output_params,
        unrecognized=parse_result.unrecognized,
        validation_errors=validation_error_msgs,
        simplification=simplification_text,
        simplification_cached=simplification_cached,
        parameter_count=len(output_params),
        anomaly_count=anomaly_count,
    )

    logger.info(
        "report_uploaded",
        file_type=ext,
        parameter_count=len(output_params),
        anomaly_count=anomaly_count,
        has_critical=has_critical,
    )

    return APIResponse(
        success=True,
        data=response_data,
        disclaimer=disclaimer,
    )
