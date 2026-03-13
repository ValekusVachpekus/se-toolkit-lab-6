# Task 2: The Documentation Agent — Implementation Plan

## Overview

Build an **agentic loop** where the LLM can call tools to read documentation and answer questions. The agent will maintain a conversation with the LLM, executing tool calls and feeding results back until the LLM provides a final answer.

## Architecture Changes from Task 1

### Task 1 (Simple LLM Call)
```
Question → LLM → Answer
```

### Task 2 (Agentic Loop)
```
Question + tools → LLM ──→ tool call? ──yes──→ execute tool ──→ back to LLM
                           │
                           no
                           ▼
                        Final answer
```

## Tool Definitions

### `list_files`
- **Purpose:** Discover available wiki files
- **Parameters:** `path` (string) — directory path relative to project root
- **Returns:** Newline-separated list of files/dirs in path
- **Security:** Resolve path, ensure it stays within project directory (no `../` traversal)
- **Error handling:** Return error message if path doesn't exist or is outside project

### `read_file`
- **Purpose:** Read file contents
- **Parameters:** `path` (string) — file path relative to project root
- **Returns:** File contents as string
- **Security:** Resolve path, ensure it stays within project directory
- **Error handling:** Return error message if file doesn't exist

## Implementation Strategy

### 1. Tool Implementation
- Define `list_files(path: str) -> str` function
- Define `read_file(path: str) -> str` function
- Both use `pathlib.Path.resolve()` to prevent directory traversal
- Both catch exceptions and return error strings

### 2. Tool Schema Registration
Define OpenAI-compatible tool schemas:
```python
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "...",
    "parameters": {
      "type": "object",
      "properties": {...},
      "required": [...]
    }
  }
}
```

### 3. Agentic Loop Implementation
```python
def agent_loop(question: str, config: dict, max_iterations: int = 10):
    messages = [{"role": "user", "content": question}]
    tool_calls_made = []
    
    for iteration in range(max_iterations):
        # Call LLM with system prompt, tools, messages
        response = call_llm_with_tools(question, messages, config)
        
        # Check for tool calls
        if response has tool_calls:
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call)
                # Add assistant message with tool_calls
                # Add tool result message
                tool_calls_made.append({
                    "tool": tool_call.name,
                    "args": tool_call.arguments,
                    "result": result
                })
        else:
            # No tool calls = final answer
            return extract_answer_and_source(response.content), tool_calls_made
    
    # Max iterations reached
    return extract_answer_and_source(last_response), tool_calls_made
```

### 4. Tool Execution
- Parse LLM's tool_calls array
- For each tool call:
  - Extract `name` and `arguments`
  - Call corresponding Python function
  - Capture result
  - Append as `{"role": "tool", "content": result}` message

### 5. System Prompt
Guide the LLM to:
- Use `list_files` to explore the wiki directory structure
- Use `read_file` to find answers in documentation
- Reference the exact section (file path + markdown heading)
- Include source in final answer

## Output Format

```json
{
  "answer": "string — the final answer",
  "source": "wiki/file.md#section-anchor",
  "tool_calls": [
    {
      "tool": "tool_name",
      "args": {"param": "value"},
      "result": "string"
    }
  ]
}
```

## Testing Strategy

Test 1: `list_files` tool usage
- Question: "What files are in the wiki?"
- Expect: `list_files` in tool_calls, answer contains file names

Test 2: `read_file` tool usage  
- Question: "How do you resolve a merge conflict?"
- Expect: `read_file` in tool_calls, source references wiki/git.md or git-workflow.md
- Verify: Answer contains merge conflict resolution steps

## Error Handling

1. **Path Traversal:** Reject paths containing `..` or absolute paths
2. **Missing Files:** Return error message from tool
3. **Max Iterations:** Stop looping after 10 iterations, return current answer
4. **Malformed Tool Calls:** Log to stderr, continue loop
5. **LLM Errors:** Same as Task 1 (stderr + exit 1)

## Deliverables

- [x] `plans/task-2.md` — This plan
- [ ] `agent.py` — Updated with tools, schemas, agentic loop
- [ ] `AGENT.md` — Updated documentation
- [ ] `tests/test_agent.py` — 2 new regression tests
