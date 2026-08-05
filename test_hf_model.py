"""Diagnostic OpenRouter call for the configured Qwen model.

The historical filename is retained so existing run instructions keep working.
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from src.config import LLM_MODEL_NAME


def test_openrouter_connection() -> bool:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    timeout = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "20"))

    print("Testing OpenRouter API connection...")
    print(f"API key found: {'Yes' if api_key else 'No'}")
    print(f"Target model: {LLM_MODEL_NAME}")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is missing from .env")
        return False

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
        )
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Chỉ trả lời bằng tiếng Việt."},
                {"role": "user", "content": "Trả lời chính xác: API_OK"},
            ],
            max_tokens=20,
        )
        print("SUCCESS! Model response received:")
        print(response.choices[0].message.content)
        return True
    except Exception as exc:
        print(f"OpenRouter API call failed ({type(exc).__name__}): {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test_openrouter_connection() else 1)
