"""
Sandboxed Python Code Execution Tool for Data Analysis, Calculations, and Plot Generation.
Executes Python code in a controlled subprocess with strict timeout limits and captures stdout/stderr.
"""

import sys
import subprocess
import tempfile
import os
from langchain_core.tools import tool
from utils.logger import log


@tool
def code_executor_tool(code: str) -> str:
    """
    Executes Python code snippet safely in an isolated subprocess.
    Returns stdout, stderr, and execution status.
    """
    # Clean code markdown blocks if present
    cleaned_code = code.strip()
    if cleaned_code.startswith("```python"):
        cleaned_code = cleaned_code[9:]
    if cleaned_code.startswith("```"):
        cleaned_code = cleaned_code[3:]
    if cleaned_code.endswith("```"):
        cleaned_code = cleaned_code[:-3]
    cleaned_code = cleaned_code.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(cleaned_code)
        script_path = f.name

    try:
        res = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        output = []
        if stdout:
            output.append(f"STDOUT:\n{stdout}")
        if stderr:
            output.append(f"STDERR:\n{stderr}")
        if res.returncode == 0:
            return "\n\n".join(output) if output else "Code executed cleanly with no stdout."
        else:
            return f"Execution failed (Exit Code {res.returncode}):\n" + "\n\n".join(output)
    except subprocess.TimeoutExpired:
        return "Execution timed out after 15 seconds limit."
    except Exception as exc:
        log.error("Code execution tool error: %s", exc)
        return f"Execution error: {str(exc)}"
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)
