from pathlib import Path
import ast

def test_lagna_field_has_label():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    labels = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "FIELD_LABELS":
                    labels = ast.literal_eval(node.value)
    assert labels is not None
    assert labels["lagna"] == "लग्न"
