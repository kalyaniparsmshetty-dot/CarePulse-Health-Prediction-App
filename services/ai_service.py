"""Google Gemini integration (the ONLY module that talks to the AI service).

Privacy: only age (derived) and three measurements are sent. Names, emails,
exact dates of birth, user remarks and account details are never sent.
"""

from dataclasses import dataclass
import time


DISCLAIMER = (
    "AI-generated information is for educational purposes only and is not a "
    "medical diagnosis. Consult a qualified healthcare professional for medical advice."
)

SYSTEM_INSTRUCTION = (
    "You write short, cautious, educational remarks about blood test values. "
    "You are not a doctor. Never give a diagnosis, never prescribe or suggest "
    "medication or doses, and never claim certainty. Explain in plain language "
    "what each value may generally indicate. Mention that interpretation depends "
    "on context, including fasting status, symptoms, laboratory reference ranges, "
    "and medical history. Encourage consultation with a qualified healthcare "
    "professional when values look unusual. "
    "Write a complete answer of about 100 to 150 words. "
    "Use short paragraphs, no headings, and complete sentences. "
    "Do not stop in the middle of a sentence."
)


ERROR_MESSAGES = {
    "not_configured": (
        "AI assessments are unavailable because no Gemini API key is configured."
    ),
    "invalid_key": (
        "The AI service rejected the configured API key. Check GEMINI_API_KEY."
    ),
    "rate_limit": (
        "The AI service is busy (rate limit reached). Please retry later."
    ),
    "service_busy": (
        "Gemini is temporarily experiencing high demand. Please try again shortly."
    ),
    "timeout": (
        "The AI service took too long to respond. Please retry."
    ),
    "network": (
        "The AI service could not be reached. Check the internet connection and retry."
    ),
    "empty": (
        "The AI service returned an empty answer. Please retry."
    ),
    "unexpected": (
        "The AI assessment could not be completed. Please retry later."
    ),
}


@dataclass
class AIResult:
    """Stores the result of an AI assessment."""

    ok: bool
    text: str = ""
    error_category: str = ""

    @property
    def message(self):
        return ERROR_MESSAGES.get(self.error_category, "")


def build_prompt(age, glucose, haemoglobin, cholesterol):
    """Create a prompt containing only age and the three measurements."""

    return (
        f"Provide an educational review for an adult aged {age} years.\n\n"
        f"Glucose: {glucose:g} mg/dL\n"
        f"Haemoglobin: {haemoglobin:g} g/dL\n"
        f"Cholesterol: {cholesterol:g} mg/dL\n\n"
        "Explain briefly what each measurement may generally indicate. "
        "Use cautious language, mention the importance of laboratory reference "
        "ranges and clinical context, and recommend professional medical advice "
        "for unusual values. Give a complete answer in plain English. "
        "Do not diagnose a condition or recommend medication."
    )


def _call_gemini(prompt, api_key, model, timeout_seconds):
    """Send the request to Gemini."""

    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=int(timeout_seconds * 1000)
        ),
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_output_tokens=1200,
            ),
        )

        return response.text

    finally:
        client.close()


def _get_error_code(exc):
    """Safely get the HTTP error code from an exception."""

    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _classify(exc):
    """Convert technical errors into safe user-friendly categories."""

    name = type(exc).__name__.lower()
    code = _get_error_code(exc)
    error_text = str(exc).lower()

    if code == 429 or "resource_exhausted" in error_text:
        return "rate_limit"

    if code in (401, 403) or "api key" in error_text or "permission" in name:
        return "invalid_key"

    if code == 503 or "unavailable" in error_text:
        return "service_busy"

    if (
        code == 504
        or "timeout" in name
        or "timed out" in error_text
        or "deadline" in error_text
    ):
        return "timeout"

    if (
        "connect" in name
        or "network" in name
        or "connection" in error_text
        or "dns" in error_text
    ):
        return "network"

    return "unexpected"


def generate_assessment(
    age,
    glucose,
    haemoglobin,
    cholesterol,
    api_key,
    model,
    timeout_seconds=45,
):
    """Generate a cautious educational assessment with one retry."""

    if not api_key:
        return AIResult(
            False,
            error_category="not_configured",
        )

    prompt = build_prompt(
        age,
        glucose,
        haemoglobin,
        cholesterol,
    )

    # Make at most two attempts for temporary Gemini server problems.
    max_attempts = 2

    for attempt in range(max_attempts):

        try:
            text = _call_gemini(
                prompt,
                api_key,
                model,
                timeout_seconds,
            )

            text = (text or "").strip()

            if not text:
                return AIResult(
                    False,
                    error_category="empty",
                )

            return AIResult(
                True,
                text=text,
            )

        except Exception as exc:

            error_category = _classify(exc)

            # Retry only temporary server availability and timeout errors.
            if (
                error_category in ("service_busy", "timeout")
                and attempt < max_attempts - 1
            ):
                time.sleep(2)
                continue

            return AIResult(
                False,
                error_category=error_category,
            )

    return AIResult(
        False,
        error_category="unexpected",
    )