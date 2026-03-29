from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample_reports"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def normal_csv() -> bytes:
    return (SAMPLE_DIR / "normal_report.csv").read_bytes()


@pytest.fixture
def anemia_csv() -> bytes:
    return (SAMPLE_DIR / "anemia_report.csv").read_bytes()


@pytest.fixture
def diabetes_csv() -> bytes:
    return (SAMPLE_DIR / "diabetes_risk.csv").read_bytes()


@pytest.fixture
def malformed_csv() -> bytes:
    return (SAMPLE_DIR / "malformed.csv").read_bytes()
