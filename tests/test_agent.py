"""Regression tests for agent.py."""

import json
import subprocess
import sys


def test_agent_json_output():
    """Test that agent.py returns valid JSON with required fields."""
    result = subprocess.run(
        [sys.executable, "-m", "agent", "What is the capital of France?"],
        capture_output=True,
        text=True,
        cwd="/home/ilya/Documents/programming/Studying/SysEN/se-toolkit-lab-6",
    )
    
    assert result.returncode == 0, f"agent.py failed: {result.stderr}"
    
    output = result.stdout.strip()
    data = json.loads(output)
    
    assert "answer" in data, "Missing 'answer' field in JSON output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in JSON output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be a list"
    assert len(data["answer"]) > 0, "'answer' must not be empty"
