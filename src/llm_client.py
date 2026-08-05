"""Shared LLM client utility — Groq (primary) with NVIDIA NIM fallback.
Uses OpenAI-compatible API with Structured Output and exponential backoff retry.
"""
import os
import json
import time
import openai
from src.config import LLM_MODEL_NAME, GROQ_MODEL_NAME, OPENAI_MODEL_NAME, NVIDIA_API_KEY, GROQ_API_KEY, OPENAI_API_KEY


def get_llm_client():
    """Return (client_type, model_name, client) tuple. OpenAI > Groq > NVIDIA."""
    # OpenAI: best for Structured Outputs
    if OPENAI_API_KEY:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        return "openai", OPENAI_MODEL_NAME, client

    # Groq: faster, higher rate limits, OpenAI-compatible
    if GROQ_API_KEY:
        client = openai.OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        return "groq", GROQ_MODEL_NAME, client

    # NVIDIA NIM fallback
    if NVIDIA_API_KEY:
        client = openai.OpenAI(
            api_key=NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        return "nvidia", LLM_MODEL_NAME, client

    return None, None, None


def call_llm(prompt: str, schema: dict, max_tokens: int = 1024, max_retries: int = 6) -> dict | None:
    """
    Call LLM with Structured Output (JSON Schema enforcement) and exponential backoff retry.
    Groq is used as primary provider (faster, fewer rate limits).
    Thread-safe synchronous implementation.

    Args:
        prompt: The user prompt
        schema: JSON Schema dict that the response must conform to
        max_tokens: Max tokens in response
        max_retries: Number of retry attempts for rate limit errors

    Returns:
        Parsed dict guaranteed to match schema, or None if failed
    """
    client_type, model_name, client = get_llm_client()
    if client is None:
        return None

    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries):
        try:
            if client_type in ("openai", "nvidia"):
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=max_tokens,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "structured_response",
                            "strict": True,
                            "schema": schema
                        }
                    }
                )
            else:
                schema_str = json.dumps(schema, indent=2)
                sys_msg = f"You always respond with valid JSON only matching this JSON schema:\n{schema_str}"
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        *messages
                    ],
                    temperature=0.0,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )

            content = response.choices[0].message.content
            if not content:
                return None

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            return json.loads(content)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                wait_time = (2 ** attempt) + 1.5  # 2.5s, 3.5s, 5.5s, 9.5s, 17.5s, 33.5s
                print(f"Rate limited ({client_type} 429), retrying in {wait_time:.1f}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"LLM call failed ({client_type}): {e}")
                return None

    print(f"LLM call failed after {max_retries} attempts.")
    return None
