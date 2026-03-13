# Agent Architecture

## Overview

This agent is a Python CLI (`agent.py`) that calls an LLM and returns structured JSON answers.

## LLM Provider

**Provider:** OpenRouter  
**Model:** `meta-llama/llama-3.3-70b-instruct:free`

### Configuration

LLM credentials are stored in `.env.agent.secret`:
- `LLM_API_KEY`: OpenRouter API key (required)
- `LLM_API_BASE`: OpenRouter base URL (`https://openrouter.ai/api/v1`)
- `LLM_MODEL`: Model name (default: `meta-llama/llama-3.3-70b-instruct:free`)

This file is gitignored and must be created locally.

## Architecture

### Components

1. **`load_config()`** — Reads LLM configuration from `.env.agent.secret` using `python-dotenv`.
2. **`call_llm(question, config)`** — Makes an HTTP POST request to the LLM API using `httpx` with a 60-second timeout.
3. **`main()`** — Parses command-line arguments, calls the LLM, and outputs JSON to stdout.

### Input/Output

**Input:** A question as the first command-line argument.
```bash
uv run agent.py "What does REST stand for?"
```

**Output:** A single JSON line to stdout.
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Error Handling

- Missing environment variables → Exit code 1 (error logged to stderr)
- API request timeout (> 60s) → Exit code 1
- API request failure (4xx/5xx) → Exit code 1
- Invalid response structure → Exit code 1
- Missing command-line argument → Exit code 1

All errors are written to stderr; only valid JSON goes to stdout.

## Dependencies

- `httpx>=0.28.0` — HTTP client with OpenAI-compatible API support
- `python-dotenv>=1.2.0` — Load environment variables

Both are already in `pyproject.toml`.

## Running the Agent

```bash
# Single question
uv run agent.py "Your question here"

# Batch evaluation
uv run run_eval.py
```

## Testing

```bash
# Run regression tests
pytest tests/test_agent.py -v
```
