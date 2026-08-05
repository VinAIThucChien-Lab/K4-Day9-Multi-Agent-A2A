"""Diagnostic script for the OpenAI Responses API connection."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI


def test_openai_connection() -> bool:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")

    print("Testing OpenAI API connection...")
    print(f"API key found: {'Yes' if api_key else 'No'}")
    print(f"Target model: {model}")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is missing from .env")
        return False

    try:
        response = OpenAI(api_key=api_key).responses.create(
            model=model,
            input="Reply with exactly: API_OK",
        )
        print("SUCCESS! Model response received:")
        print(response.output_text)
        return True
    except Exception as exc:
        print(f"OpenAI API call failed ({type(exc).__name__}): {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test_openai_connection() else 1)
