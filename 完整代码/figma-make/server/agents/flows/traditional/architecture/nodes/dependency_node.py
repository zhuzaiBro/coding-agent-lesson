"""step6: Dependency node (programmatic, no LLM)."""
from agents.utils.dependency_builder import read_template_package_json
from agents.utils.supabase_integration import request_wants_supabase


async def dependency_node(state: dict) -> dict:
    """
    Load template package.json as dependency baseline.
    Actual import scanning + dependency resolution happens in assemble_node.
    """
    print("--- DependencyNode (Programmatic) Start ---")

    template_pkg = await read_template_package_json()

    if request_wants_supabase(state):
        deps = template_pkg.setdefault("dependencies", {})
        deps.setdefault("@supabase/supabase-js", "^2.49.0")
        print("[DependencyNode] Added @supabase/supabase-js for Supabase backend")

    dep_count = len((template_pkg.get("dependencies") or {}).keys())
    print(f"[DependencyNode] Template dependencies: {dep_count} packages")

    print("--- DependencyNode (Programmatic) End ---")

    return {
        "dependency": {
            "packageJson": template_pkg,
            "dependencies": {},
            "reason": "Template baseline loaded, import scanning will complete at assembly phase",
        }
    }
