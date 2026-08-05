"""Diagnostic script to test Hugging Face Model API connection."""

import os
import sys
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

def test_huggingface_connection():
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    model_name = "meta-llama/Llama-3.1-8B-Instruct"
    provider = os.getenv("HF_PROVIDER", "auto")
    timeout_seconds = float(os.getenv("HF_TIMEOUT_SECONDS", "20"))

    print(f"Testing HF API Connection...")
    print(f"Token found: {'Yes' if token else 'No'}")
    print(f"Target Model: {model_name}")

    if not token or token.startswith("hf_your"):
        print("ERROR: HF_TOKEN is missing or not set to a valid token in .env!")
        return False

    messages = [
        {"role": "system", "content": "You are a helpful e-commerce dispute assistant."},
        {"role": "user", "content": "Hello! Confirm if the API is operational."}
    ]

    # Try standard client first
    try:
        print("Sending test prompt via HuggingFace InferenceClient...")
        client = InferenceClient(
            model=model_name,
            provider=provider,
            token=token,
            timeout=timeout_seconds,
        )
        response = client.chat.completions.create(
            messages=messages,
            max_tokens=50
        )
        content = response.choices[0].message.content
        print("\nSUCCESS! Model response received:")
        print("--------------------------------------------------")
        print(content)
        print("--------------------------------------------------")
        return True
    except Exception as e:
        print(f"Standard InferenceClient call failed: {e}")

    try:
        print("Sending test prompt via provider: featherless-ai...")
        client = InferenceClient(provider="featherless-ai", api_key=token, timeout=10)
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=50
        )
        content = response.choices[0].message.content
        print("\nSUCCESS via provider featherless-ai! Model response received:")
        print("--------------------------------------------------")
        print(content)
        print("--------------------------------------------------")
        return True
    except Exception as e:
        print(f"Provider InferenceClient call failed: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if test_huggingface_connection() else 1)
