"""
Generates appropriate medical disclaimers based on risk level.
"""

DISCLAIMER_LOW = (
    "This analysis is for informational purposes only and is NOT a substitute "
    "for professional medical advice, diagnosis, or treatment."
)

DISCLAIMER_MODERATE = (
    "Some findings in your report may require attention. This analysis is for "
    "informational purposes only — please consider consulting a healthcare professional."
)

DISCLAIMER_HIGH = (
    "Your blood report contains findings that should be evaluated by a doctor. "
    "This tool does NOT replace professional medical diagnosis or treatment. "
    "Please schedule an appointment with a qualified healthcare provider."
)

DISCLAIMER_CRITICAL = (
    "IMPORTANT: Your results contain critically abnormal values. "
    "Please seek medical attention promptly. "
    "This analysis is NOT a substitute for professional medical care."
)


def get_disclaimer(has_critical: bool = False, anomaly_count: int = 0) -> str:
    if has_critical:
        return DISCLAIMER_CRITICAL
    if anomaly_count >= 3:
        return DISCLAIMER_HIGH
    if anomaly_count >= 1:
        return DISCLAIMER_MODERATE
    return DISCLAIMER_LOW
