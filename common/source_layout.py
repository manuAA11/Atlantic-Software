"""Read canonical sources behind approved compatibility entry points."""
import ast
from pathlib import Path


def resolve_source(path):
    path = Path(path).resolve()
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'common':
            aliases = [item.name for item in node.names if item.asname == '_implementation']
            if len(aliases) == 1 and aliases[0] == path.stem:
                canonical = path.parent.parent / 'common' / (aliases[0] + '.py')
                if not canonical.is_file():
                    raise FileNotFoundError(canonical)
                return canonical
    return path
