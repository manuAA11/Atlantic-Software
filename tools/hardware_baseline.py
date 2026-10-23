"""Stable syntax digest across supported Python versions and Windows checkouts."""
import ast
import hashlib
import json


def syntax_sha256(source, *, excluded_methods=()):
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,ast.ClassDef):
            node.body=[item for item in node.body if not isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)) or item.name not in excluded_methods]
    def stable(value):
        if isinstance(value,ast.AST):
            # Python adds optional AST fields over time. Omit absent/empty fields
            # so the same source has the same signature under 3.11 and 3.14.
            return {'node':type(value).__name__,**{key:stable(item) for key,item in ast.iter_fields(value) if item is not None and item!=[]}}
        if isinstance(value,list):return [stable(item) for item in value]
        if isinstance(value,bytes):return {"bytes":value.hex()}
        if isinstance(value,complex):return {"complex":[value.real,value.imag]}
        if value is Ellipsis:return {"ellipsis":True}
        return value
    encoded=json.dumps(stable(tree),ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()
