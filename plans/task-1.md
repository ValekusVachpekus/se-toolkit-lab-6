# Task 1: Call an LLM from Code — Implementation Plan

## Overview

Build a Python CLI (`agent.py`) that takes a question, calls an LLM, and returns a JSON answer with `answer` and `tool_calls` fields.

## LLM Provider Choice

**Provider:** OpenRouter  
**Model:** `meta-llama/llama-3.3-70b-instruct:free`

**Rationale:** Free tier, no credit card required, strong tool-calling support, works from Russia.

## Architecture

### Input/Output Flow

```
CLI argument → load_config() → call_llm() → JSON stdout
```

### Implementation Details

1. **Configuration Loading** (`load_config()`)
   - Read `.env.agent.secret` using `python-dotenv`
   - Extract `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Exit with code 1 if any is missing

2. **LLM Call** (`call_llm()`)
   - Use `httpx.Client` with 60-second timeout
   - POST to `{LLM_API_BASE}/chat/completions`
   - Send system prompt + user question
   - Handle timeouts and HTTP errors gracefully
   - Extract answer from response

3. **Main Entry Point** (`main()`)
   - Check command-line argument exists
   - Call `load_config()` and `call_llm()`
   - Output JSON with `answer` and empty `tool_calls: []`
   - Only JSON on stdout; all errors to stderr

### Error Cases

- Missing env vars → stderr + exit 1
- Request timeout → stderr + exit 1
- API error (4xx/5xx) → stderr + exit 1
- Invalid JSON response → stderr + exit 1
- Missing CLI argument → stderr + exit 1

### Testing Strategy

Create `tests/test_agent.py` with:
- Run agent.py as subprocess
- Parse stdout JSON
- Verify `answer` and `tool_calls` fields exist and are correct types
- Verify answer is non-empty string
- Verify tool_calls is empty list

### Deliverables

- [ ] `agent.py` — Main CLI implementation
- [ ] `AGENT.md` — Architecture documentation
- [ ] `tests/test_agent.py` — 1 regression test
- [ ] `.env.agent.secret` — Configuration (already created)
- [ ] `plans/task-1.md` — This plan