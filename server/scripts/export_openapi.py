"""OpenAPI schema export utility script.

Responsibilities:
    - Instantiate the FastAPI application without database or external services.
    - Extract and serialize OpenAPI 3.1 specification to deterministic JSON.
    - Support output to stdout or target file path via CLI arguments.

Owner: Vivek (api) · Task: S1-VIV-1 · Requirements: —
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

# Suppress library deprecation warnings during schema export
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure server package root is on sys.path before importing app modules
SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from fastapi import FastAPI  # noqa: E402

from app.main import create_app  # noqa: E402


def export_openapi(app: FastAPI) -> str:
    """Generate deterministic JSON representation of FastAPI OpenAPI schema.

    Args:
        app: Initialized FastAPI application instance.

    Returns:
        Formatted, sorted JSON string with trailing newline.
    """
    spec = app.openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for exporting OpenAPI schema.

    Args:
        argv: Optional list of command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Export deterministic OpenAPI JSON schema from FastAPI app."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional file path to write exported OpenAPI JSON schema.",
    )
    args = parser.parse_args(argv)

    app = create_app()
    openapi_json = export_openapi(app)

    if args.output:
        output_path: Path = args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(openapi_json, encoding="utf-8")
    else:
        sys.stdout.write(openapi_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
