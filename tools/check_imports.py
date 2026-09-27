"""找出未使用的 import，以及重复定义的同名函数（重构收尾用）。

环境里没有 pyflakes / ruff，这个脚本用 ast 做最基本的检查：

- 顶层 ``import x`` / ``from m import a, b`` 之后没有出现过的名字
- 同一文件里重复定义的顶层函数名（往往是复制粘贴留下的死代码）

用法::

    python tools/check_imports.py            # 扫描项目
    python tools/check_imports.py main.py ui # 只扫描指定路径
"""

from __future__ import annotations

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"tools", "__pycache__", ".venv", "venv", "_baseline", "platform-tools"}


def iter_python_files(paths):
    for path in paths:
        full = os.path.join(ROOT, path)
        if os.path.isfile(full) and full.endswith(".py"):
            yield full
        elif os.path.isdir(full):
            for dirpath, dirnames, filenames in os.walk(full):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for name in filenames:
                    if name.endswith(".py"):
                        yield os.path.join(dirpath, name)


def collect_bound_names(tree):
    """收集整个文件里出现过的所有标识符（含属性名之外的普通名字）。"""
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            pass  # 属性名不算，靠 base 的 Name 覆盖
        elif isinstance(node, ast.Str) and False:
            pass
    return used


def check_file(path):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source, filename=path)
    used = collect_bound_names(tree)

    problems = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name not in used:
                    problems.append(f"L{node.lineno}: 未使用的 import {name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                name = alias.asname or alias.name
                if name == "*":
                    continue
                if name not in used:
                    problems.append(
                        f"L{node.lineno}: 未使用的 import {name} (from {node.module})")

    seen = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in seen:
                problems.append(
                    f"L{node.lineno}: {node.name} 与 L{seen[node.name]} 重复定义")
            seen[node.name] = node.lineno

    return problems


def main():
    targets = sys.argv[1:] or ["."]
    total = 0
    for path in sorted(iter_python_files(targets)):
        problems = check_file(path)
        if problems:
            rel = os.path.relpath(path, ROOT)
            print(rel)
            for line in problems:
                print("  " + line)
            total += len(problems)

    print()
    if total:
        print(f"发现 {total} 处可疑项")
        return 1
    print("未发现未使用的 import 或重复定义")
    return 0


if __name__ == "__main__":
    sys.exit(main())
