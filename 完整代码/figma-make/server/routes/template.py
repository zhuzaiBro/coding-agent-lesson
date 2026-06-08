import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

IGNORE_PATTERNS = {"node_modules", "dist", ".DS_Store"}


@router.get("/react-ts")
async def get_react_ts_template():
    """Serve all files under templates/react-ts/ as a JSON dict {"/path": {"code": "content"}}."""
    template_dir = Path(os.getcwd()) / "templates" / "react-ts"

    if not template_dir.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "No files found in template directory"},
        )

    result: dict[str, dict[str, str]] = {}

    for file_path in template_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # Check ignore patterns
        skip = False
        for part in file_path.parts:
            if part in IGNORE_PATTERNS:
                skip = True
                break
        if skip:
            continue

        relative = file_path.relative_to(template_dir)
        key = "/" + str(relative).replace("\\", "/")

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            result[key] = {"code": content}
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")

    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": "No files found in template directory"},
        )

    return result
