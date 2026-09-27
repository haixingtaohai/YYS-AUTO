"""项目路径常量。

所有路径都从本文件位置推导（ROOT_DIR）。不要改用 os.getcwd()：程序由
bat/run.bat 以 ``python ..\main.py`` 启动，工作目录不保证是项目根目录。

这些路径原来是散在 main.py 各处、直接用 ``__file__`` 推导的。搬进 ui/ 子包后
必须仍然指向项目根目录——否则会读不到 config.json（表现为"配置和标签页全没了"）、
找不到 png 模板文件夹。

注意 CONFIG_FILE / USAGE_RECORDS_FILE 是可变模块属性：测试会临时指向别的目录。
"""

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 任务栏图标：优先根目录，其次 png/
ICON_PATH = os.path.join(ROOT_DIR, "icon.ico")
if not os.path.exists(ICON_PATH):
    _PNG_ICON = os.path.join(ROOT_DIR, "png", "icon.ico")
    ICON_PATH = _PNG_ICON if os.path.exists(_PNG_ICON) else None

# 场景模板图片根目录
PNG_BASE_FOLDER = os.path.join(ROOT_DIR, "png")

# 配置文件与运行时长记录
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")
USAGE_RECORDS_FILE = os.path.join(ROOT_DIR, "usage_records.json")

# 使用说明文档目录
DOC_FOLDER = os.path.join(ROOT_DIR, "使用文档第一次使用必看")

# adb 可执行文件
PLATFORM_TOOLS_DIR = os.path.join(ROOT_DIR, "platform-tools")
ADB_EXE = os.path.join(PLATFORM_TOOLS_DIR, "adb.exe")
