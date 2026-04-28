import subprocess
import os
from typing import Dict, Any, Tuple

class TerminalExecutor:
    """
    Secure wrapper for executing bash commands within the workspace.
    """
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)

    def execute(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Executes a shell command and returns the exit code, stdout, and stderr.
        """
        try:
            # We use shell=True here because agents often generate bash pipelines
            # Note: In a real production system, consider security implications
            # and potentially use a sandbox or stricter parsing.
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return -1, stdout, f"Command timed out after {timeout} seconds.\n{stderr}"
        except Exception as e:
            return -2, "", str(e)

    def run_as_tool(self, command: str) -> str:
        """
        Helper method specifically designed for the Agent to use as a Tool.
        Returns a formatted string containing both stdout and stderr for the agent to observe.
        """
        exit_code, stdout, stderr = self.execute(command)
        
        output = f"Exit Code: {exit_code}\n"
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
            output += f"STDERR:\n{stderr}\n"
            
        return output
