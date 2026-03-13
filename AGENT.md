# Agent Architecture

## Overview

This is a **documentation agent** — a Python CLI that uses an agentic loop to answer questions by reading project documentation. Unlike a simple chatbot, it can call tools to interact with the real world.

## Architecture

### Task 1: Simple LLM Call
```
User Question → Load Config → Call LLM → JSON Output
```

### Task 2: Agentic Loop (Current)
```
User Question + Tools → LLM ──→ tool call? ──yes──→ execute tool ──→ back to LLM
                             │
                             no
                             ▼
                          JSON output
```

## LLM Provider

**Provider:** OpenRouter  
**Model:** `meta-llama/llama-3.3-70b-instruct:free`

### Configuration

LLM credentials are stored in `.env.agent.secret`:
- `LLM_API_KEY`: OpenRouter API key (required)
- `LLM_API_BASE`: OpenRouter base URL (`https://openrouter.ai/api/v1`)
- `LLM_MODEL`: Model name (default: `meta-llama/llama-3.3-70b-instruct:free`)

This file is gitignored and must be created locally.

## Tools

The agent has two tools to navigate the project:

### `list_files`

List files and directories in a path.

- **Parameters:**
  - `path` (string) — relative directory path from project root (e.g., `wiki`, `lab/tasks`)
- **Returns:** Newline-separated list of entries
- **Security:** Prevents path traversal (no `../` or absolute paths)

**Example:**
```python
list_files("wiki")
# Returns: "architecture.md\nbackend.md\n..."
```

### `read_file`

Read the contents of a file.

- **Parameters:**
  - `path` (string) — relative file path from project root (e.g., `wiki/git-workflow.md`)
- **Returns:** Full file contents as string
- **Security:** Prevents path traversal (no `../` or absolute paths)

**Example:**
```python
read_file("wiki/git-workflow.md")
# Returns: Full markdown content
```

## Agentic Loop

The loop executes in the `run_agent_loop()` function:

1. **Initialize:** Create message list with user question
2. **Call LLM:** Send messages + tool definitions to LLM with system prompt
3. **Check Response:** Does LLM want to call tools?
   - **Yes:** Execute each tool, append results, loop back to step 2
   - **No:** Extract answer, exit loop
4. **Max Iterations:** Stop after 10 iterations (safety limit)
5. **Output:** Return answer, source reference, and all tool calls made

### System Prompt

The system prompt guides the LLM to:
- Use `list_files` to explore the wiki directory structure
- Use `read_file` to find answers in documentation  
- Always mention the file and section where the answer came from

## Output Format

```json
{
  "answer": "Full text answer to the question",
  "source": "wiki/file.md#section-anchor",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\narchitecture.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "Full file contents..."
    }
  ]
}
```

- `answer` — Final answer to the question
- `source` — Wiki file and section where answer was found (extracted via regex from answer text)
- `tool_calls` — Array of all tool calls made, with args and results

## Implementation Details

### Components

1. **`load_config()`** — Reads `.env.agent.secret`
2. **`list_files()` / `read_file()`** — Tool implementations with security checks
3. **`execute_tool()`** — Dispatcher for tool execution
4. **`get_tool_schemas()`** — Returns OpenAI-compatible function calling schemas
5. **`call_llm_with_tools()`** — Calls LLM with tools enabled
6. **`run_agent_loop()`** — Main agentic loop (max 10 iterations)
7. **`main()`** — CLI entry point

### Path Security

Both tools use `pathlib.Path.resolve()` to prevent directory traversal:
- Rejects paths with `..`
- Rejects absolute paths
- Ensures target resolves within project directory
- Returns error message if path is unsafe

### Error Handling

- Missing env vars → stderr + exit 1
- API timeout (> 60s) → stderr + exit 1
- API errors (4xx/5xx) → stderr + exit 1
- Invalid LLM response → stderr + exit 1
- Path traversal attempts → error returned from tool
- Max iterations reached → returns answer from last response

## Dependencies

- `httpx>=0.28.0` — HTTP client with OpenAI-compatible API support
- `python-dotenv>=1.2.0` — Load environment variables
- `pathlib` — Safe path handling (stdlib)
- `re` — Regex for source extraction (stdlib)

## Running the Agent

```bash
# Single question
uv run agent.py "What files are in the wiki?"

# Batch evaluation
uv run run_eval.py

# Tests
pytest tests/test_agent.py -v
```

## Example Interaction

```bash
$ uv run agent.py "How do you resolve a merge conflict?"
```

The agent will:
1. List the wiki directory to find relevant files
2. Read `wiki/git-workflow.md` (or similar)
3. Extract the merge conflict section
4. Return answer with source reference

Output:
```json
{
  "answer": "When you encounter a merge conflict, edit the file to manually select which changes to keep, then stage and commit the resolved file.",
  "source": "wiki/git-workflow.md#merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, ...},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, ...}
  ]
}
```
