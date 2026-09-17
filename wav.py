"""提示音设置：音效文件管理、试听与任务结束提示音播放"""
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog

from adb import get_gui_logger

gui_logger = get_gui_logger()


def get_wav_folder():
    """音效文件目录"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "wav")


# ---------------------------- 设置页 ----------------------------

def create_variables(settings_tab):
    """创建设置页提示音变量"""
    parent = settings_tab.parent
    settings_tab.settings_sound_var = tk.BooleanVar(value=parent.sound_enabled)
    settings_tab.settings_sound_file_var = tk.StringVar(value=getattr(parent, 'sound_file', ''))


def apply_settings(settings_tab):
    """把设置页的提示音参数写回父对象"""
    parent = settings_tab.parent
    old_enabled = parent.sound_enabled
    parent.sound_enabled = settings_tab.settings_sound_var.get()
    parent.sound_file = settings_tab.settings_sound_file_var.get()
    settings_tab._log_change(old_enabled, parent.sound_enabled,
                            "提示音已开启", "提示音已关闭")


def create_section(settings_tab, parent_frame):
    """构建提示音设置区"""
    sound_group = ttk.LabelFrame(parent_frame, text="提示音设置", padding="8")
    sound_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
    settings_tab._add_section_help(sound_group,
        "任务正常结束时播放的提示音（在 wav 目录中读取）。\n"
        "“音效”下拉框选择要播放的 .wav 文件，可点“试听”先确认效果；\n"
        "“添加”从电脑中导入 wav 文件；\n"
        "“删除”移除下拉框中选中的文件；“刷新列表”用于手动放入文件后重新读取。\n"
        "未选择文件或文件不存在时，自动播放 wav 目录中的第一个文件。\n"
        "手动点击“停止”结束任务时不会播放。")

    # 开关行
    top_row = ttk.Frame(sound_group)
    top_row.pack(fill=tk.X, pady=2)
    ttk.Checkbutton(top_row, text="启用提示音", variable=settings_tab.settings_sound_var,
                    command=settings_tab.save_settings).pack(side=tk.LEFT)

    # 音效文件选择
    file_row = ttk.Frame(sound_group)
    file_row.pack(fill=tk.X, pady=2)
    ttk.Label(file_row, text="音效:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=2)
    settings_tab.sound_combo = ttk.Combobox(file_row, width=14, state="readonly",
                                            textvariable=settings_tab.settings_sound_file_var)
    settings_tab.sound_combo.pack(side=tk.LEFT, padx=2)
    settings_tab.sound_combo.bind("<<ComboboxSelected>>", lambda e: settings_tab.save_settings())
    ttk.Button(file_row, text="试听", width=5,
               command=lambda: preview(settings_tab)).pack(side=tk.LEFT, padx=1)

    # 操作按钮
    btn_row = ttk.Frame(sound_group)
    btn_row.pack(fill=tk.X, pady=2)
    ttk.Button(btn_row, text="添加", width=6,
               command=lambda: add_file(settings_tab)).pack(side=tk.LEFT, padx=1)
    ttk.Button(btn_row, text="删除", width=6,
               command=lambda: delete_file(settings_tab)).pack(side=tk.LEFT, padx=1)
    ttk.Button(btn_row, text="刷新列表", width=8,
               command=lambda: refresh_list(settings_tab)).pack(side=tk.LEFT, padx=1)

    # 初始化音效列表
    refresh_list(settings_tab)


def refresh_list(settings_tab):
    """刷新音效文件列表"""
    wav_folder = get_wav_folder()
    files = []
    if os.path.exists(wav_folder):
        for f in sorted(os.listdir(wav_folder)):
            if f.lower().endswith('.wav'):
                files.append(f)
    settings_tab.sound_combo['values'] = files
    current = settings_tab.settings_sound_file_var.get()
    if current in files:
        settings_tab.sound_combo.set(current)
    elif files:
        settings_tab.sound_combo.set(files[0])
        settings_tab.settings_sound_file_var.set(files[0])


def add_file(settings_tab):
    """添加音效文件"""
    gui_logger.info("[设置] 点击按钮: 添加音效文件")
    wav_folder = get_wav_folder()
    os.makedirs(wav_folder, exist_ok=True)
    file_path = filedialog.askopenfilename(
        title="选择WAV音频文件",
        filetypes=[("WAV音频", "*.wav"), ("所有文件", "*.*")]
    )
    if file_path:
        try:
            filename = os.path.basename(file_path)
            dest = os.path.join(wav_folder, filename)
            shutil.copy2(file_path, dest)
            refresh_list(settings_tab)
            settings_tab.settings_sound_file_var.set(filename)
            settings_tab.save_settings()
        except Exception as e:
            pass


def delete_file(settings_tab):
    """删除选中的音效文件"""
    gui_logger.info("[设置] 点击按钮: 删除音效文件")
    filename = settings_tab.settings_sound_file_var.get()
    if not filename:
        return
    wav_folder = get_wav_folder()
    filepath = os.path.join(wav_folder, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            refresh_list(settings_tab)
            settings_tab.save_settings()
        except Exception as e:
            pass


def preview(settings_tab):
    """试听选中的音效文件"""
    gui_logger.info("[设置] 点击按钮: 试听音效")
    filename = settings_tab.settings_sound_file_var.get()
    if not filename or not filename.lower().endswith('.wav'):
        return
    wav_folder = get_wav_folder()
    wav_path = os.path.join(wav_folder, filename)
    if os.path.exists(wav_path):
        try:
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            pass


# ---------------------------- 运行期播放 ----------------------------

def play(tab):
    """播放提示音（非手动停止时调用）"""
    if not hasattr(tab.parent, 'sound_enabled') or not tab.parent.sound_enabled:
        return
    try:
        wav_folder = get_wav_folder()
        if not os.path.exists(wav_folder):
            return
        # 优先使用用户选择的音效文件
        sound_file = getattr(tab.parent, 'sound_file', '')
        if sound_file and sound_file.lower().endswith('.wav'):
            wav_path = os.path.join(wav_folder, sound_file)
            if os.path.exists(wav_path):
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
        # 没有选择文件或文件不存在，尝试播放第一个wav
        wav_files = [f for f in os.listdir(wav_folder) if f.lower().endswith('.wav')]
        if wav_files:
            wav_path = os.path.join(wav_folder, wav_files[0])
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        pass