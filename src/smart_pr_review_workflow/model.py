import os

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

load_dotenv()


def get_bedrock_kwargs() -> dict:
    """Return shared Bedrock connection settings for model and embedding clients."""
    region = os.getenv("AWS_REGION", "us-east-1")
    profile = os.getenv("AWS_PROFILE") or None
    kwargs = {"region_name": region}
    if profile:
        kwargs["credentials_profile_name"] = profile
    return kwargs


def get_llm() -> ChatBedrockConverse:
    model_id = os.getenv("BEDROCK_MODEL_ID", "").strip()
    if not model_id or model_id == "your-bedrock-model-or-inference-profile-id" or model_id == "your-bedrock-chat-model-id":
        raise RuntimeError(
            "BEDROCK_MODEL_ID is still using the placeholder. Set it to a valid "
            "Bedrock model or inference-profile ID that your AWS account can invoke."
        )

    kwargs = {
        "model": model_id,
        **get_bedrock_kwargs(),
        "temperature": 0,
        "max_tokens": 800,
    }
    return ChatBedrockConverse(**kwargs)
