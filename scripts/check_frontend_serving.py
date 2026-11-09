"""Run with python scripts/check_frontend_serving.py; no backend services needed."""
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

source = Path(__file__).resolve().parents[1] / "backend/app/main.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
# Execute the real production-index and static-mount configuration without API/DB imports.
nodes = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "get_frontend_index":
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "dist_dir" for t in node.targets):
        nodes.append(node)
    elif isinstance(node, ast.If) and ast.unparse(node.test) == "dist_dir.is_dir()":
        nodes.append(node)
routes = next(node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "FRONTEND_ROUTES" for t in node.targets))
assert "market" in ast.literal_eval(routes), "Market deep links must serve the SPA"
assert len(nodes) == 3
code = compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec")
with TemporaryDirectory() as tmp:
    frontend = Path(tmp)
    (frontend / "index.html").write_text("Vite source", encoding="utf-8")
    mounts = []
    namespace = {
        "Path": Path, "frontend_dir": frontend,
        "app": SimpleNamespace(mount=lambda *args, **kwargs: mounts.append((args, kwargs))),
        "StaticFiles": lambda **kwargs: kwargs,
    }
    exec(code, namespace)
    assert not namespace["get_frontend_index"]().exists(), "Must not fall back to source HTML"
    assert mounts == [], "No frontend source directories may be exposed"
    dist = frontend / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("Built React app", encoding="utf-8")
    exec(code, namespace)
    assert namespace["get_frontend_index"]() == dist / "index.html"
    assert [(args[0], args[1]["directory"]) for args, _ in mounts] == [
        ("/assets", str(dist / "assets")), ("/static", str(dist)),
    ]
print("PASS: dist-only serving, no source fallback or legacy/source mounts")
