"""Generate source lookup documentation without importing application code.

Run from any working directory:
    python scripts/generate_learning_atlas.py

This extracts declared contracts, not inferred behavior or runtime guarantees.
"""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "learning" / "SOURCE_ATLAS.md"


def relative_link(path: Path, line: int) -> str:
    return f"../../{path.relative_to(ROOT).as_posix()}#L{line}"


def code(value: str) -> str:
    return "`" + value.replace("`", "'").replace("|", "&#124;").replace("\n", " ") + "`"


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    result = f"{prefix}{node.name}({ast.unparse(node.args)})"
    if node.returns is not None:
        result += f" -> {ast.unparse(node.returns)}"
    return result


def functions(tree: ast.AST, owner: str = ""):
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef):
            yield from functions(node, f"{owner}{node.name}.")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield owner, node
            # Include nested factory callbacks, whose captured collaborators matter.
            yield from functions(node, f"{owner}{node.name}.<locals>.")


def routes(path: Path, tree: ast.Module):
    prefix = ""
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if ast.unparse(node.value.func) == "APIRouter":
                prefix = next(
                    (ast.literal_eval(k.value) for k in node.value.keywords if k.arg == "prefix"),
                    "",
                )
    for owner, node in functions(tree):
        if owner:
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr
            if ast.unparse(decorator.func.value) != "router" or method not in {"get", "post", "patch", "delete", "put"}:
                continue
            route_path = ast.literal_eval(decorator.args[0])
            keywords = {item.arg: item.value for item in decorator.keywords}
            response = ast.unparse(keywords["response_model"]) if "response_model" in keywords else "handler-defined"
            status = ast.unparse(keywords["status_code"]) if "status_code" in keywords else "200 (default)"
            hidden = "include_in_schema" in keywords and ast.literal_eval(keywords["include_in_schema"]) is False
            yield (
                method.upper(), "/api/v1" + prefix + route_path,
                node.name, node.lineno, response, status, hidden,
            )


def main() -> None:
    lines = [
        "# Source atlas",
        "",
        "Generated from the current source by `python scripts/generate_learning_atlas.py`. "
        "No application modules, database connections, or GPU libraries are imported. "
        "This is a lookup index, not a substitute for the explained "
        "[contracts](ROUTES_AND_CONTRACTS.md) and [walkthrough](CODE_WALKTHROUGH.md).",
        "",
        "Signatures preserve declared arguments/defaults/annotations. Missing return annotations "
        "do not mean a function returns nothing. Docstrings describe intent and can lag behavior. "
        "Source line links are a snapshot and move when code changes.",
        "",
        "## Registered application route declarations",
        "",
        "These include hidden compatibility aliases. FastAPI's own documentation endpoints "
        "are framework-generated and are not listed here.",
        "",
        "| Method | Full path | Handler | Response model | Declared status | Hidden alias |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    files = sorted((ROOT / "backend/src/castle_qa").rglob("*.py"))
    parsed = [(path, ast.parse(path.read_text(encoding="utf-8-sig"))) for path in files]
    route_count = 0
    for path, tree in parsed:
        if path.parent.name != "routers":
            continue
        for method, route, name, lineno, response, status, hidden in routes(path, tree):
            route_count += 1
            lines.append(
                f"| {method} | {code(route)} | [{name}]({relative_link(path, lineno)}) "
                f"| {code(response)} | {code(status)} | {'yes' if hidden else ''} |"
            )
    lines += ["", "## Python implementation contracts", ""]
    function_count = 0
    for path, tree in parsed:
        entries = list(functions(tree))
        if not entries:
            continue
        lines += [f"### {path.relative_to(ROOT).as_posix()}", ""]
        for owner, node in entries:
            function_count += 1
            doc = ast.get_docstring(node)
            description = " ".join(doc.split()) if doc else "No docstring; inspect the linked implementation."
            description = description.replace("|", "&#124;")
            lines += [
                f"- [{owner}{node.name}, line {node.lineno}]({relative_link(path, node.lineno)}): {code(signature(node))}",
                f"  {description}",
                "",
            ]
    lines += ["## Frontend source exports", "", "A lexical index of top-level exported declarations. "
              "Interfaces/types describe compile-time contracts; exported functions/components can execute.", ""]
    frontend_count = 0
    for path in sorted((ROOT / "frontend/src").rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        entries = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if re.match(r"^export (?:async )?(?:interface|type|function|const|class|default)\b", line):
                frontend_count += 1
                entries.append(f"- [Line {lineno}]({relative_link(path, lineno)}): {code(line.strip())}")
        if entries:
            lines += [f"### {path.relative_to(ROOT).as_posix()}", "", *entries, ""]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {route_count} route declarations, "
          f"{function_count} Python functions/methods, {frontend_count} frontend exports.")


if __name__ == "__main__":
    main()
