# Agent Architecture

## Overview

This is a **system agent** — a Python CLI that uses an agentic loop to answer questions by reading documentation, source code, and querying the backend API. It combines documentation lookup, code analysis, and system state queries into a unified agent.

## Architecture Evolution

### Task 1: Simple LLM Call
```
User Question → Load Config → Call LLM → JSON Output
```

### Task 2: Documentation Agent
```
User Question + Tools → LLM ──→ list_files/read_file ──→ back to LLM
                             ↓
                        JSON output
```

### Task 3: System Agent (Current)
```
User Question + Tools → LLM ──→ choose tool ──→ execute ──→ back to LLM
                             ↓
                        (repeat until answer)
                             ↓
                        JSON output
```

## LLM Provider

**Provider:** OpenRouter  
**Model:** `meta-llama/llama-3.3-70b-instruct:free`

### Configuration

LLM credentials are read from environment variables:
- `LLM_API_KEY`: OpenRouter API key (required, from `.env.agent.secret`)
- `LLM_API_BASE`: OpenRouter base URL (from `.env.agent.secret`)
- `LLM_MODEL`: Model name (from `.env.agent.secret`)

Backend API credentials:
- `LMS_API_KEY`: Backend authentication (from `.env.docker.secret`)
- `AGENT_API_BASE_URL`: Backend URL (optional, defaults to `http://localhost:42002`)

**Important:** All configuration is read from environment variables, not hardcoded. This allows the autochecker to inject different credentials for evaluation.

## Tools

The agent has three tools to gather information:

### 1. `list_files`

List files and directories in a path.

- **Parameters:** `path` — relative directory path from project root
- **Returns:** Newline-separated list of files and directories
- **Security:** Prevents path traversal attacks

**When to use:** Explore project structure to find documentation

### 2. `read_file`

Read file contents from the project.

- **Parameters:** `path` — relative file path from project root
- **Returns:** Full file contents as string
- **Security:** Prevents path traversal attacks

**When to use:** Read documentation, source code, or configuration files

### 3. `query_api`

Make HTTP requests to the backend API.

- **Parameters:**
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `path` (string) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) — JSON request body for POST/PUT
- **Returns:** JSON string with:
  ```json
  {
    "status_code": 200,
    "body": "response content"
  }
  ```
- **Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret`

**When to use:** Query system state, database content, analytics, framework info

## Agentic Loop

The loop in `run_agent_loop()` operates as follows:

1. **Initialize:** Create message list with user question
2. **Call LLM:** Send messages + tool definitions to LLM with system prompt
3. **Check Response:** Does LLM want to call tools?
   - **Yes:** Execute each tool, append results to messages, loop back to step 2
   - **No:** Extract answer and source, exit loop
4. **Max Iterations:** Stop after 10 iterations (safety limit)
5. **Output:** Return answer, source reference, and all tool calls made

### System Prompt Strategy

The system prompt guides the LLM to:
- Use `list_files` to explore documentation structure
- Use `read_file` to find answers in wiki and source code
- Use `query_api` for system facts and data queries
- Chain tools when needed (e.g., query API for error, then read code to debug)

## Output Format

```json
{
  "answer": "Full text answer to the question",
  "source": "wiki/file.md#section or empty string",
  "tool_calls": [
    {
      "tool": "tool_name",
      "args": {"param": "value"},
      "result": "string result"
    }
  ]
}
```

- `answer` — Final answer to the question
- `source` — Wiki file reference if applicable (optional for API queries)
- `tool_calls` — All tool calls made with arguments and results

## Tool Selection Logic

The LLM uses the following logic to choose tools:

| Question Type | Tool | Example |
|---------------|------|---------|
| Documentation lookup | `list_files` → `read_file` | "How do I resolve a merge conflict?" |
| Code/framework lookup | `read_file` | "What framework does the backend use?" |
| System facts (database) | `query_api` | "How many items are in the database?" |
| Analytics queries | `query_api` | "What is the completion rate for lab-99?" |
| Bug diagnosis | `query_api` → `read_file` | Query API for error, read code to find bug |

## Implementation Details

### Components

1. **`load_config()`** — Reads all config from environment variables
2. **Tools:**
   - `list_files()` — List directory contents with security checks
   - `read_file()` — Read files with security checks
   - `query_api()` — Make authenticated API requests
3. **`execute_tool()`** — Dispatcher for tool execution
4. **`get_tool_schemas()`** — Returns OpenAI-compatible function calling schemas
5. **`call_llm_with_tools()`** — Calls LLM with tools enabled
6. **`run_agent_loop()`** — Main agentic loop (max 10 iterations)
7. **`main()`** — CLI entry point

### Path Security

Both `list_files()` and `read_file()` use `pathlib.Path.resolve()` to prevent directory traversal:
- Rejects paths with `..`
- Rejects absolute paths
- Ensures target resolves within project directory
- Returns error message if path is unsafe

### API Authentication

The `query_api()` tool:
- Reads `LMS_API_KEY` from environment
- Reads `AGENT_API_BASE_URL` from environment (defaults to localhost:42002)
- Adds `Authorization: Bearer {LMS_API_KEY}` header
- Returns JSON with status_code and response body
- Handles timeouts and connection errors gracefully

### Error Handling

- Missing env vars → stderr + exit 1
- API timeout (> 60s) → stderr + exit 1
- API errors (4xx/5xx) → Returned in tool result
- Path traversal attempts → Error returned from tool
- Max iterations reached → Returns answer from last response
- `content: null` in LLM response → Handled with `(content or "")`

## Dependencies

- `httpx>=0.28.0` — HTTP client for both LLM and API calls
- `python-dotenv>=1.2.0` — Load environment variables
- `pathlib` — Safe path handling (stdlib)
- `re` — Regex for source extraction (stdlib)

## Running the Agent

```bash
# Single question
uv run agent.py "What framework does the backend use?"

# Batch evaluation
uv run run_eval.py

# Tests
pytest tests/test_agent.py -v
```

## Example Interactions

### Documentation Lookup
```bash
$ uv run agent.py "What files are in the wiki?"
```

The agent lists wiki files and returns the list.

### Framework Detection
```bash
$ uv run agent.py "What Python framework does this use?"
```

The agent reads `backend/app/main.py` or `README.md` and identifies FastAPI.

### Data Query
```bash
$ uv run agent.py "How many items are in the database?"
```

The agent calls `GET /items/` and extracts the count from the response.

### Bug Diagnosis
```bash
$ uv run agent.py "What's wrong with the /analytics endpoint?"
```

The agent:
1. Calls `GET /analytics/completion-rate` to see the error
2. Reads the error message
3. Examines `backend/app/routes/analytics.py` to find the bug
4. Explains the issue

## Lessons Learned

Through iterative development and benchmark testing:

1. **Tool Descriptions Matter**: Clear, concise descriptions help the LLM choose the right tool
2. **Parameter Guidance**: Specific examples in parameter descriptions improve accuracy
3. **Error Responses as Data**: Even error responses from API calls provide useful context
4. **Chaining Tools**: Multi-step reasoning (query API, then read code) requires good system prompts
5. **Environment Variables**: Always read config from environment, never hardcode
6. **Null Handling**: LLM's `content` field can be `null` even when present; use `(content or "")`
7. **Rate Limiting**: OpenRouter free tier is rate-limited; test carefully with `--index N`
8. **Timeout Values**: 30 seconds for API calls, 60 seconds for LLM; adjust based on model speed
