import os

class WorkspaceContext:
    """
    Reads local workspace rules (.cursorrules, .antigravityrules) to build
    the foundational system prompt for the agent.
    """
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)
        
    def get_system_prompt(self) -> str:
        """
        Constructs the base system prompt combined with any local rules found.
        """
        base_prompt = "You are a powerful AI-driven IDE Agent Engine. You have access to terminal commands and files."
        
        # Check for rules files
        rules_content = ""
        for rule_file in [".cursorrules", ".antigravityrules", ".windsurfrules"]:
            file_path = os.path.join(self.workspace_dir, rule_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    rules_content += f"\n--- Rules from {rule_file} ---\n"
                    rules_content += f.read() + "\n"
                    
        if rules_content:
            return f"{base_prompt}\n\nWorkspace Rules:\n{rules_content}"
            
        return base_prompt
