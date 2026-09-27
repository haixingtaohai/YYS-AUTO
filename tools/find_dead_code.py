"""找出 return/break/continue/raise 之后永远执行不到的语句。

重构时用「旧串换新串」的方式改代码，很容易把原函数的尾巴留在新函数里——
`_kill_adb_server` 里就曾漏进一句 `self.on_window_close()`，导致"重启ADB并重启程序"
会先把主窗口关掉。这类问题语法检查和冒烟测试都发现不了，所以单列一个检查。

用法::

    python tools/find_dead_code.py
"""

import ast
import glob
import os

TERMINATORS = (ast.Return, ast.Break, ast.Continue, ast.Raise)

FILES = (["main.py", "paths.py", "presets.py", "adb.py", "wav.py",
          "notification.py", "image_recognizer.py", "image_accelerator.py"]
         + sorted(glob.glob("ui/*.py")) + sorted(glob.glob("scenes/*.py")))


class Finder(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.hits = []

    def _scan_body(self, body, owner):
        for index, stmt in enumerate(body[:-1]):
            if isinstance(stmt, TERMINATORS):
                nxt = body[index + 1]
                self.hits.append(
                    f"  {self.path}:{nxt.lineno} 在 {owner} 的 "
                    f"L{stmt.lineno} {type(stmt).__name__.lower()} 之后"
                )
                break

    def visit_FunctionDef(self, node):
        self._scan_body(node.body, node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node):
        self._scan_body(node.body, "if")
        self._scan_body(node.orelse, "else")
        self.generic_visit(node)

    def visit_For(self, node):
        self._scan_body(node.body, "for")
        self.generic_visit(node)

    visit_While = visit_For

    def visit_With(self, node):
        self._scan_body(node.body, "with")
        self.generic_visit(node)

    def visit_Try(self, node):
        self._scan_body(node.body, "try")
        for handler in node.handlers:
            self._scan_body(handler.body, "except")
        self._scan_body(node.orelse, "try-else")
        self._scan_body(node.finalbody, "finally")
        self.generic_visit(node)


total = 0
for path in FILES:
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    finder = Finder(path)
    finder.visit(tree)
    if finder.hits:
        print("\n".join(finder.hits))
        total += len(finder.hits)

print(f"\n发现 {total} 处死代码" if total else "未发现 return/break 之后的死代码")
