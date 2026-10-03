"""Compatibility entry point for current privacy and workspace browser checks."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("check_workspace_refresh.py")), run_name="__main__")
