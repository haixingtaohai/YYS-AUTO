"""统计各文件的注释密度（`#` 注释行 / 代码行）。

fuck-u-code 的「注释比例」指标最优区间是 10%~25%，低于 5% 判定为文档不足。
docstring 不计入注释行，所以这个数字和 docstring 覆盖率是两回事。

用法::

    python tools/comment_ratio.py
"""

from __future__ import annotations

import glob
import io
import os

FOLDERS = ("ui", "scenes")
ROOT_FILES = ("main.py", "paths.py", "presets.py", "adb.py", "wav.py",
              "notification.py", "image_recognizer.py", "image_accelerator.py")


def analyze(path):
    """返回 (代码行, 注释行)。"""
    code = comments = 0
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                comments += 1
            else:
                code += 1
    return code, comments


def main():
    paths = [f for f in ROOT_FILES if os.path.exists(f)]
    for folder in FOLDERS:
        paths += sorted(glob.glob(os.path.join(folder, "*.py")))

    rows = []
    total_code = total_comments = 0
    for path in paths:
        code, comments = analyze(path)
        total_code += code
        total_comments += comments
        ratio = comments / code * 100 if code else 0
        rows.append((ratio, code, comments, path))

    rows.sort()
    print(f"{'注释%':>7}  {'代码':>6} {'注释':>6}  文件")
    print("-" * 52)
    for ratio, code, comments, path in rows:
        flag = "  <- 偏少" if ratio < 5 else ""
        print(f"{ratio:6.1f}%  {code:6d} {comments:6d}  {path}{flag}")
    print("-" * 52)
    overall = total_comments / total_code * 100
    print(f"{overall:6.1f}%  {total_code:6d} {total_comments:6d}  合计"
          f"（最优区间 10%~25%）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
