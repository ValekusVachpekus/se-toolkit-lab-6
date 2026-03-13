#!/usr/bin/env python3
"""Agent CLI that calls an LLM and returns structured JSON answers."""

import json
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv


def load_config() -> dict[str, str]:
    """Load LLM configuration from .env.agent.secret."""
    load_dotenv(".env.agent.secret")
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    
    if not api_key or not api_base or not model:
        print(
            "Error: Missing LLM configuration in .env.agent.secret",
            file=sys.stderr,
        )
        sys.exit(1)
    
    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def call_llm(question: str, config: dict[str, str]) -> str:
    """Call the LLM and get an answer."""
    system_prompt = (
        "You are a helpful AI assistant. "
        "Answer the user's question concisely and accurately."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{config['api_base']}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        print("Error: Request timed out (> 60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: LLM API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    data = response.json()
    
    if "choices" not in data or len(data["choices"]) == 0:
        print("Error: Invalid LLM response structure", file=sys.stderr)
        sys.exit(1)
    
    answer = data["choices"][0]["message"]["content"]
    return answer.strip()


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: agent.py <question>", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    config = load_config()
    answer = call_llm(question, config)
    
    result: dict[str, Any] = {
        "answer": answer,
        "tool_calls": [],
    }
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
