class TokenOptimizer:
    """
    Handles context compression, output pruning, and diff generation.
    """
    
    @staticmethod
    def prune_terminal_output(raw_output: str, max_lines: int = 100) -> str:
        """
        Prunes long terminal outputs by keeping the beginning and end.
        """
        lines = raw_output.splitlines()
        if len(lines) <= max_lines:
            return raw_output
            
        half = max_lines // 2
        pruned_output = "\n".join(lines[:half])
        pruned_output += f"\n\n... [{len(lines) - max_lines} lines omitted for context compression] ...\n\n"
        pruned_output += "\n".join(lines[-half:])
        return pruned_output

    @staticmethod
    def format_as_diff(original: str, modified: str) -> str:
        """
        Generate a unified diff to save output tokens.
        In a real scenario, the LLM would output this diff and we'd apply it.
        Here we can just provide utility to format it.
        """
        import difflib
        diff = difflib.unified_diff(
            original.splitlines(),
            modified.splitlines(),
            lineterm=''
        )
        return '\n'.join(list(diff))
