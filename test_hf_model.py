"""Diagnostic script to test Hugging Face Model API connection."""

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

def test_huggingface_connection():
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    model_name = "Qwen/Qwen3-VL-8B-Instruct"

    print(f"Testing HF API Connection...")
    print(f"Token found: {'Yes (' + token[:6] + '***)' if token else 'No'}")
    print(f"Target Model: {model_name}")

    if not token or token.startswith("hf_your"):
        print("ERROR: HF_TOKEN is missing or not set to a valid token in .env!")
        return False

    try:
        client = InferenceClient(api_key=token)
        print("Sending test prompt to Hugging Face Inference API...")
        
        # Test chat completion with model
        messages = [
            {"role": "system", "content": "You are a helpful e-commerce dispute assistant."},
            {"role": "user", "content": "Hello! Confirm if the API is operational."}
        ]

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=100
        )

        content = response.choices[0].message.content
        print("\nSUCCESS! Model response received:")
        print("--------------------------------------------------")
        print(content)
        print("--------------------------------------------------")
        return True

    except Exception as e:
        print(f"\nInferenceClient direct call failed: {e}")
        print("Trying HuggingFace Hub client with text_generation fallback...")

        try:
            # Fallback test with text_generation API
            res = client.text_generation(
                prompt="Confirm if Hugging Face model API is working properly.",
                model=model_name,
                max_new_tokens=50
            )
            print("\nSUCCESS (text_generation)! Model response:")
            print(res)
            return True
        except Exception as e2:
            print(f"Fallback call failed: {e2}")
            return False


if __name__ == "__main__":
    test_huggingface_connection()
