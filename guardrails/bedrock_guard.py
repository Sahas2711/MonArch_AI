import os
from typing import Optional, Tuple
from utils.logger import log


def apply_bedrock_guardrail(text: str, guardrail_id: Optional[str] = None, guardrail_version: str = "1") -> Tuple[bool, str]:
    """
    Apply Amazon Bedrock Guardrail to evaluate output safety & prevent hallucinated legal citations.
    Returns (is_safe, processed_text_or_reason).
    """
    gid = guardrail_id or os.getenv("BEDROCK_GUARDRAIL_ID")
    if not gid:
        log.info("BEDROCK_GUARDRAIL_ID not set; skipping Bedrock Guardrail API call.")
        return True, text

    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.apply_guardrail(
            guardrailIdentifier=gid,
            guardrailVersion=guardrail_version,
            source="OUTPUT",
            content=[{"text": {"text": text}}]
        )

        action = response.get("action", "NONE")
        if action == "GUARDRAIL_INTERVENED":
            log.warning("Bedrock Guardrail intervened: blocked output content.")
            return False, "Output blocked by Amazon Bedrock Guardrail (potential safety violation or legal hallucination)."
        return True, text
    except Exception as exc:
        log.warning("Bedrock Guardrail evaluation failed (%s); proceeding with unblocked output.", exc)
        return True, text
