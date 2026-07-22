@echo off
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
pip install --upgrade pip
pip install opencv-python numpy
timeout /t 2