"""
系统通知模块 - 使用 Windows Toast 通知 API（通过 winotify）
支持自定义应用名称和图标。若 winotify 未安装则回退到 PowerShell 托盘通知。
"""
import os
import sys
import subprocess

try:
    from winotify import Notification, audio
    _HAS_WINOTIFY = True
except ImportError:
    _HAS_WINOTIFY = False

# 应用名称和标识
_APP_NAME = "YYS-AUTO"
_APP_ID = "yysauto.application.v2.8"
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ICON_PATH = os.path.join(_BASE_DIR, "icon.ico")

# 如果图标文件不存在则回退为 None
if not os.path.exists(_ICON_PATH):
    _ICON_PATH = None

# 确保 Windows Toast 能关联到正确的应用名称
def _register_app_name():
    """在开始菜单创建快捷方式，帮助 Windows 关联通知来源名称"""
    if sys.platform != 'win32':
        return
    try:
        shortcuts_dir = os.path.join(
            os.environ['APPDATA'],
            r'Microsoft\Windows\Start Menu\Programs'
        )
        os.makedirs(shortcuts_dir, exist_ok=True)
        shortcut_path = os.path.join(shortcuts_dir, f'{_APP_NAME}.lnk')
        if os.path.exists(shortcut_path):
            return  # 已存在，跳过
        
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, 'pythonw.exe')
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        
        icon_path_escaped = _ICON_PATH.replace('\\', '\\\\') if _ICON_PATH else ''
        
        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("{shortcut_path}")
$sc.TargetPath = "{pythonw}"
$sc.WorkingDirectory = "{_BASE_DIR}"
{('$sc.IconLocation = "' + icon_path_escaped + '"') if icon_path_escaped else ''}
$sc.Save()

# 设置 AppUserModelID 到快捷方式属性
$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("{shortcuts_dir}")
$file = $folder.ParseName("{_APP_NAME}.lnk")
if ($file) {{
    $file.ExtendedProperty("System.AppUserModel.ID") = "{_APP_ID}"
}}
'''
        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        subprocess.run(
            ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps_script],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15
        )
    except Exception:
        pass  # 注册失败不影响通知功能

_register_app_name()

# 通知开关状态（从配置读取）
_notify_enabled = True


def set_notify_enabled(enabled: bool):
    """设置是否启用系统通知"""
    global _notify_enabled
    _notify_enabled = enabled


def is_notify_enabled() -> bool:
    """获取通知是否启用"""
    return _notify_enabled


def _show_notification(title: str, message: str, is_error: bool = False, duration: str = "short"):
    """
    发送 Windows Toast 通知
    
    Args:
        title: 通知标题
        message: 通知内容
        is_error: 是否为错误通知
        duration: "short" 或 "long"
    """
    if _HAS_WINOTIFY:
        toast = Notification(
            app_id=_APP_ID,
            title=title,
            msg=message,
            duration=duration,
            icon=_ICON_PATH
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    else:
        # 回退到 PowerShell 托盘通知
        _show_ps_notification(title, message, is_error)


def _show_ps_notification(title: str, message: str, is_error: bool):
    """PowerShell System.Windows.Forms.NotifyIcon 回退方案"""
    icon_type = 'Error' if is_error else 'Info'
    icon_path = _ICON_PATH.replace('\\', '\\\\') if _ICON_PATH else ''
    
    if icon_path:
        icon_line = f'if (Test-Path "{icon_path}") {{ $notify.Icon = New-Object System.Drawing.Icon("{icon_path}") }} else {{ $notify.Icon = [System.Drawing.SystemIcons]::Information }}'
    else:
        icon_line = '$notify.Icon = [System.Drawing.SystemIcons]::Information'
    
    ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms | Out-Null
Add-Type -AssemblyName System.Drawing | Out-Null
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Text = "{_APP_NAME}"
{icon_line}
$notify.Visible = $true
$notify.BalloonTipTitle = "{title.replace("'", "''")}"
$notify.BalloonTipText = "{message.replace("'", "''")}"
$notify.BalloonTipIcon = "{icon_type}"
$notify.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$notify.Dispose()
'''
    
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    subprocess.Popen(
        ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps_script],
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def send_complete_notification(title: str, message: str):
    """发送任务完成通知"""
    if not _notify_enabled:
        return
    _show_notification(title, message, is_error=False)


def send_error_notification(title: str, message: str):
    """发送错误通知"""
    if not _notify_enabled:
        return
    _show_notification(title, message, is_error=True)


def test_complete():
    """测试完成通知"""
    _show_notification(f"{_APP_NAME} - 任务完成", "这是一条测试用的任务完成通知", is_error=False)


def test_error():
    """测试错误通知"""
    _show_notification(f"{_APP_NAME} - 异常停止", "这是一条测试用的错误通知", is_error=True)
