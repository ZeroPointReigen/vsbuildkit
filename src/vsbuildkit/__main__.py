
import os
from pathlib import Path
import sys


if not __package__:
    # Make CLI runnable from source tree with
    #    python src/package
    SCRIPT_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(SCRIPT_DIR.parent))


if __name__ == "__main__":
    from vsbuildkit.cli import app
    app()