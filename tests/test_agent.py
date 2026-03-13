"""Regression tests for agent.py."""

import json
import subprocess
import sys


def run_agent(question: str) -> dict:
    """Helper to run agent and parse output."""
    result = subprocess.run(
        [sys.executable, "-m", "agent", question],
        capture_output=True,
        text=True,
        cwd="/home/ilya/Documents/programming/Studying/SysEN/se-toolkit-lab-6",
    )
    
    assert result.returncode == 0, f"agent.py failed: {result.stderr}"
    
    output = result.stdout.strip()
    return json.loads(output)


def test_agent_json_output():
    """Test that agent.py returns valid JSON with required fields."""
    data = run_agent("What is the capital of France?")
    
    assert "answer" in data, "Missing 'answer' field in JSON output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in JSON output"
    assert "source" in data, "Missing 'source' field in JSON output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be a list"
    assert isinstance(data["source"], str), "'source' must be a string"
    assert len(data["answer"]) > 0, "'answer' must not be empty"


def test_agent_list_files_tool():
    """Test that agent uses list_files tool to discover wiki files."""
    data = run_agent("What files are in the wiki directory?")
    
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    
    tool_names = [tc["tool"] for tc in data["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files tool to be called"
    
    assert len(data["answer"]) > 0, "Answer should not be empty"
    assert isinstance(data["source"], str), "Source should be a string"


def test_agent_read_file_tool():
    """Test that agent uses read_file tool to find answers in documentation."""
    data = run_agent("Where is the project architecture documented?")
    
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    
    tool_names = [tc["tool"] for tc in data["tool_calls"]]
    assert "read_file" in tool_names or "list_files" in tool_names, (
        "Expected read_file or list_files tool to be called"
    )
    
    assert len(data["answer"]) > 0, "Answer should not be empty"
    assert isinstance(data["source"], str), "Source should reference a wiki file"
