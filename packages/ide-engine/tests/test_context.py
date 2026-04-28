import pytest
from core.ide_context import IDEContext

def test_ide_context_git():
    ctx = IDEContext()
    # Mocking or running in a git repo should return strings
    branch = ctx.get_git_branch()
    assert isinstance(branch, str)

def test_ide_context_format():
    ctx = IDEContext()
    prompt = ctx.format_context_prompt(
        active_file="test.py",
        cursor_line=42,
        open_files=["test.py", "main.py"]
    )
    
    assert "<IDE_CONTEXT>" in prompt
    assert "Active Document: test.py" in prompt
    assert "Cursor is on line: 42" in prompt
    assert "main.py" in prompt
    assert "</IDE_CONTEXT>" in prompt
