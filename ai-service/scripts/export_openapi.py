"""Export the actual Python API contract without running the web server.

Run from the project root: python scripts/export_openapi.py
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


if __name__ == "__main__":
    destination = PROJECT_ROOT.parent / "docs" / "ai-service.openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Exported Python API schema to {destination}")
