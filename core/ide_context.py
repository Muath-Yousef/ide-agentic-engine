import subprocess
import os
from typing import Dict, Any, List

class IDEContext:
    """
    Aggregates real-time workspace data to provide environmental awareness 
    to the AgentOrchestrator.
    """
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = workspace_path

    def get_git_diff(self) -> str:
        """Fetch uncommitted git diffs to show the agent what the user is currently working on."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_git_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def format_context_prompt(self, active_file: str = "", cursor_line: int = 0, open_files: List[str] = None) -> str:
        """
        Formats all contextual IDE data into a compressed System Prompt block.
        """
        open_files = open_files or []
        branch = self.get_git_branch()
        diff = self.get_git_diff()
        
        prompt = "<IDE_CONTEXT>\n"
        prompt += f"Current Git Branch: {branch}\n"
        
        if active_file:
            prompt += f"Active Document: {active_file}\n"
            if cursor_line > 0:
                prompt += f"Cursor is on line: {cursor_line}\n"
                
        if open_files:
            prompt += "Other open documents:\n"
            for f in open_files:
                prompt += f"- {f}\n"
                
        if diff:
            # We truncate the diff if it's too large to save tokens
            diff_lines = diff.splitlines()
            if len(diff_lines) > 200:
                diff = "\n".join(diff_lines[:100]) + "\n... [diff truncated] ...\n" + "\n".join(diff_lines[-100:])
            prompt += f"\nUncommitted Changes:\n```diff\n{diff}\n```\n"
            
        prompt += "</IDE_CONTEXT>"
        return prompt
