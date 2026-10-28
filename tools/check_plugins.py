# -*- coding: utf-8 -*-
"""检查 dlc/interactions/*.py 有没有碰桌宠的下划线属性(p._xxx / pet._xxx / self.pet._xxx)。
插件只该用 docs/接口规范.md 里列出的公开接口; 内部字段随时会改, 用了就容易悄悄坏掉。
用法: python tools/check_plugins.py [插件目录]      有问题返回 1
"""
import ast
import sys
from pathlib import Path

PET_NAMES = {"p", "pet"}


def _is_pet(node):
    if isinstance(node, ast.Name):
        return node.id in PET_NAMES
    return (isinstance(node, ast.Attribute) and node.attr == "pet"
            and isinstance(node.value, ast.Name) and node.value.id == "self")


def check_file(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    bad = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr.startswith("_") and not node.attr.startswith("__")
                and _is_pet(node.value)):
            bad.append((node.lineno, node.attr))
    return bad


def main(argv):
    d = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / "dlc" / "interactions"
    total = 0
    for f in sorted(d.glob("*.py")):
        for line, attr in check_file(f):
            print(f"{f.name}:{line}: 用了内部属性 {attr}")
            total += 1
    print("ok, 插件只用了公开接口" if total == 0 else f"共 {total} 处")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
