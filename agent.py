#!/usr/bin/env python3
"""Agent CLI with agentic loop for documentation and system queries."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


def load_config() -> dict[str, str]:
    """Load configuration from environment files."""
    load_dotenv(".env.agent.secret")
    load_dotenv(".env.docker.secret")
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    
    if not api_key or not api_base or not model:
        print(
            "Error: Missing LLM configuration in .env.agent.secret",
            file=sys.stderr,
        )
        sys.exit(1)
    
    lms_api_key = os.getenv("LMS_API_KEY")
    agent_api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    
    return {
        "llm_api_key": api_key,
        "llm_api_base": api_base,
        "llm_model": model,
        "lms_api_key": lms_api_key,
        "agent_api_base": agent_api_base,
    }


def is_safe_path(path_str: str) -> bool:
    """Check if path is safe (no traversal outside project)."""
    try:
        project_root = Path.cwd()
        target = (project_root / path_str).resolve()
        return target.is_relative_to(project_root)
    except (ValueError, RuntimeError):
        return False


def list_files(path: str) -> str:
    """List files and directories in a path."""
    if not is_safe_path(path):
        return f"Error: Path '{path}' is outside project directory."
    
    try:
        target = Path(path)
        if not target.exists():
            return f"Error: Path '{path}' does not exist."
        if not target.is_dir():
            return f"Error: '{path}' is not a directory."
        
        entries = sorted([entry.name for entry in target.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def read_file(path: str) -> str:
    """Read a file from the project."""
    if not is_safe_path(path):
        return f"Error: Path '{path}' is outside project directory."
    
    try:
        target = Path(path)
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: '{path}' is not a file."
        
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {str(e)}"


def query_api(method: str, path: str, body: str = "", config: dict[str, str] = None) -> str:
    """Query the backend API."""
    if not config:
        return "Error: No API configuration available."
    
    lms_api_key = config.get("lms_api_key")
    agent_api_base = config.get("agent_api_base", "http://localhost:42002")
    
    try:
        url = f"{agent_api_base}{path}"
        headers = {"Content-Type": "application/json"}
        
        if lms_api_key:
            headers["Authorization"] = f"Bearer {lms_api_key}"
        
        request_body = None
        if body:
            try:
                request_body = json.loads(body)
            except json.JSONDecodeError:
                return json.dumps({
                    "status_code": 400,
                    "body": "Error: Invalid JSON in request body",
                })
        
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                json=request_body,
                headers=headers,
            )
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text,
        })
    except httpx.TimeoutException:
        return json.dumps({
            "status_code": 0,
            "body": "Error: Request timed out",
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: {str(e)}",
        })


def execute_tool(tool_name: str, tool_args: dict[str, Any], config: dict[str, str] = None) -> str:
    """Execute a tool and return the result."""
    if tool_name == "list_files":
        return list_files(tool_args.get("path", ""))
    elif tool_name == "read_file":
        return read_file(tool_args.get("path", ""))
    elif tool_name == "query_api":
        return query_api(
            tool_args.get("method", "GET"),
            tool_args.get("path", ""),
            tool_args.get("body", ""),
            config,
        )
    else:
        return f"Error: Unknown tool '{tool_name}'."


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI-compatible tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": (
                    "List files and directories in a directory. "
                    "Use this to discover what documentation files are available."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Directory path relative to project root "
                                "(e.g., 'wiki', 'backend', 'lab/tasks')"
                            ),
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read the contents of a file. "
                    "Use this to find specific information in documentation or source code."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "File path relative to project root "
                                "(e.g., 'wiki/architecture.md', 'backend/app/main.py', 'README.md')"
                            ),
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": (
                    "Query the backend API to get system information and data. "
                    "Use this for questions about database state, item counts, analytics, "
                    "framework information, or any dynamic system data."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method",
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "API path starting with / (e.g., '/items/', "
                                "'/analytics/completion-rate', '/status')"
                            ),
                        },
                        "body": {
                            "type": "string",
                            "description": "JSON request body (optional, for POST/PUT requests)",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def call_llm_with_tools(
    messages: list[dict[str, Any]],
    config: dict[str, str],
) -> dict[str, Any]:
    """Call the LLM with tools enabled."""
    system_prompt = (
        "You are a helpful assistant that answers questions about a software project. "
        "You have three tools available:\n\n"
        "1. list_files() - Explore the project structure and find documentation files\n"
        "2. read_file() - Read documentation, source code, or configuration files\n"
        "3. query_api() - Query the backend API for system state and data\n\n"
        "Choose the right tool based on the question:\n"
        "- For 'how do I' or 'what is' questions about the project, use list_files() then read_file()\n"
        "- For questions about the Python framework, configuration, or code structure, use read_file()\n"
        "- For questions about data (item counts, analytics), system facts (ports, status), "
        "or dynamic information, use query_api()\n"
        "- For bug diagnosis, read the error from query_api() and then use read_file() to "
        "examine the relevant source code\n\n"
        "Always start by understanding what kind of question it is, then use the appropriate tool. "
        "After getting the answer, explain it clearly to the user."
    )
    
    headers = {"Authorization": f"Bearer {config['llm_api_key']}"}
    
    payload = {
        "model": config["llm_model"],
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "tools": get_tool_schemas(),
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{config['llm_api_base']}/chat/completions",
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
    
    return response.json()


def extract_source_from_content(content: str) -> str:
    """Extract source reference from response content."""
    import re
    
    match = re.search(r"(wiki/[\w\-./]+\.md(?:#[\w\-]+)?)", content)
    if match:
        return match.group(1)
    return ""


def run_agent_loop(
    question: str,
    config: dict[str, str],
    max_iterations: int = 10,
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Run the agentic loop.
    
    Returns: (answer, source, tool_calls_made)
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    tool_calls_made: list[dict[str, Any]] = []
    
    for iteration in range(max_iterations):
        response_data = call_llm_with_tools(messages, config)
        
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            print("Error: Invalid LLM response structure", file=sys.stderr)
            sys.exit(1)
        
        choice = response_data["choices"][0]
        message = choice["message"]
        
        has_tool_calls = "tool_calls" in message and message["tool_calls"]
        
        if has_tool_calls:
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.get("content") or "",
            }
            if "tool_calls" in message:
                assistant_message["tool_calls"] = message["tool_calls"]
            messages.append(assistant_message)
            
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                result = execute_tool(tool_name, tool_args, config)
                
                tool_calls_made.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                    }
                )
                
                messages.append(
                    {
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_call["id"],
                    }
                )
        else:
            answer = message.get("content") or ""
            source = extract_source_from_content(answer)
            return answer, source, tool_calls_made
    
    answer = message.get("content") or "No answer generated"
    source = extract_source_from_content(answer)
    return answer, source, tool_calls_made


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: agent.py <question>", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    config = load_config()
    
    answer, source, tool_calls = run_agent_loop(question, config)
    
    result: dict[str, Any] = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls,
    }
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
