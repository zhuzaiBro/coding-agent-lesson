"""Backward-compatible aliases for compile-debug fix schema."""
from agents.flows.traditional.assembly.schemas.file_patch_schema import (
    FilePatch,
    FilePatchResult,
)

DebugFixPatch = FilePatch
DebugFixResult = FilePatchResult
