# Task 3: The System Agent — Implementation Plan

## Overview

Add a `query_api` tool to the agent so it can query the deployed backend API in addition to reading documentation. This enables the agent to answer questions about system state (item counts, framework used, API endpoints, etc.).

## Tool Addition

### New Tool: `query_api`

Make HTTP requests to the backend API.

- **Parameters:**
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE)
  - `path` (string) — API path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) — JSON request body for POST/PUT

- **Returns:** JSON string with:
  ```json
  {
    "status_code": 200,
    "body": "response content"
  }
  ```

- **Authentication:** Use `LMS_API_KEY` from `.env.docker.secret` (Authorization header)
- **Base URL:** Read from `AGENT_API_BASE_URL` env var, default to `http://localhost:42002`

## Implementation Strategy

### 1. Tool Implementation
- `query_api(method: str, path: str, body: str = "") -> str` function
- Use `httpx.Client` with timeout
- Extract `LMS_API_KEY` and `AGENT_API_BASE_URL` from environment
- Handle errors gracefully (connection refused, timeouts, etc.)
- Return JSON with status_code and response body

### 2. Tool Schema Registration
Add to OpenAI-compatible schemas:
```python
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend API to get system information...",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", ...]},
        "path": {"type": "string"},
        "body": {"type": "string"}
      },
      "required": ["method", "path"]
    }
  }
}
```

### 3. System Prompt Update
Guide the LLM to:
- Use `list_files` for documentation exploration
- Use `read_file` for code/wiki lookup
- Use `query_api` for:
  - System facts (framework, database state)
  - Data queries (item counts, analytics)
  - Dynamic information
- Choose appropriate tool based on question type

### 4. Configuration
Load from environment:
- `LLM_API_KEY` — LLM provider (from .env.agent.secret)
- `LLM_API_BASE` — LLM endpoint
- `LLM_MODEL` — LLM model name
- `LMS_API_KEY` — Backend API authentication (from .env.docker.secret)
- `AGENT_API_BASE_URL` — Backend base URL (optional, default: http://localhost:42002)

### 5. Error Handling
- Connection refused → Return error message
- Timeout → Return error message
- HTTP errors (4xx, 5xx) → Return status code + error body
- Malformed JSON body → Return error

## Testing Strategy

Test 1: `query_api` tool for data queries
- Question: "How many items are in the database?"
- Expected: `query_api` tool called with GET /items/
- Expected source: Empty or API reference

Test 2: `read_file` for framework lookup
- Question: "What framework does the backend use?"
- Expected: `read_file` tool called (looking at backend code)
- Expected source: wiki or code file reference

## Benchmark Strategy

Use `run_eval.py` to test against 10 local questions:
1. Wiki lookup questions
2. System fact questions (framework, ports)
3. Data query questions (item counts)
4. Bug diagnosis questions (query API, read code)
5. Reasoning questions

Iterate on failures:
- Improve tool descriptions if tool not called
- Fix tool implementation if called but returns error
- Improve system prompt if wrong tool called
- Debug parameter handling if called with wrong args

## Expected Benchmark Results

Target: 10/10 passing on local eval.py

Success indicators:
- Agent identifies question type correctly
- Chooses appropriate tools
- Chains tools correctly (e.g., query API for error, then read code to debug)
- Extracts correct information from API responses

## Deliverables

- [ ] `plans/task-3.md` — This plan + benchmark diagnosis
- [ ] `agent.py` — Updated with query_api tool + system prompt
- [ ] `AGENT.md` — Updated with query_api documentation and lessons learned
- [ ] `tests/test_agent.py` — 2 new regression tests for system queries
