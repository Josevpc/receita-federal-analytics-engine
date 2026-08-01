"""Entry point: `python main.py convert|query|update|clean`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from receita_analytics.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
