"""配置文件的读写。

设置字段用一张声明式表格描述，读写共用——重构前 ``load_config`` 和 ``save_config``
各自维护一份 20 个字段的 if 分支，两边一旦不同步就会静默丢设置。

**关键约束**：``load`` 返回的 dict 必须原样保留所有未知键（``tabs``、
``window_geometry``、``preset_thresholds`` 里已废弃场景的残留项），``write`` 时整体
写回。如果改成"按已知字段重建 dict"，用户的标签页配置会被清空。
"""

from __future__ import annotations

import json
import os

# (配置键, 对象属性名)。读写共用，新增设置项只需要改这一处。
SETTINGS_FIELDS = (
    ("link_enabled", "link_enabled"),
    ("close_jiacheng_enabled", "close_jiacheng_enabled"),
    ("close_jiacheng_wait", "close_jiacheng_wait"),
    ("dinghao_wait", "dinghao_wait"),
    ("huijuan_mode", "huijuan_mode"),
    ("dj_jinsheng_stop", "dj_jinsheng_stop"),
    ("ql_fangqi", "ql_fangqi"),
    ("ql_zaici", "ql_zaici"),
    ("sound_enabled", "sound_enabled"),
    ("sound_file", "sound_file"),
    ("logging_enabled", "logging_enabled"),
    ("notify_enabled", "notify_enabled"),
    ("zoushen_enabled", "zoushen_enabled"),
    ("zoushen_trigger_min", "zoushen_trigger_min"),
    ("zoushen_trigger_max", "zoushen_trigger_max"),
    ("zoushen_duration_min", "zoushen_duration_min"),
    ("zoushen_duration_max", "zoushen_duration_max"),
    ("zoushen_whitelist", "zoushen_whitelist"),
    ("adb_ip", "adb_ip"),
    ("adb_port", "adb_port"),
)

# 保存时需要拷贝一份的字段，避免外部改动直接影响到配置内容
_COPY_ON_SAVE = ("zoushen_whitelist",)

# 配置文件缺失或损坏时使用的默认值
DEFAULT_CONFIG = {"last_tab": 0, "tabs": {}}


def load(config_file):
    """读取配置文件。

    文件不存在或不是合法 JSON 时返回 :data:`DEFAULT_CONFIG`（副本）。
    返回值保留文件里的全部键，包括本程序不认识的键。
    """
    if not os.path.exists(config_file):
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_file, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return dict(DEFAULT_CONFIG)


def apply(config, target):
    """把配置里的设置项写到 target 对象上，并同步需要通知其它模块的开关。"""
    for key, attr in SETTINGS_FIELDS:
        if key in config:
            setattr(target, attr, config[key])

    # 这两个开关要同步给日志/通知模块，且只在配置里显式出现时才同步
    if "logging_enabled" in config:
        from adb import set_logging_enabled
        set_logging_enabled(target.logging_enabled)
    if "notify_enabled" in config:
        from notification import set_notify_enabled
        set_notify_enabled(target.notify_enabled)


def collect(target, config):
    """把 target 上的设置项写进 config（原地修改，保留其它键）。"""
    for key, attr in SETTINGS_FIELDS:
        if hasattr(target, attr):
            value = getattr(target, attr)
            config[key] = list(value) if key in _COPY_ON_SAVE else value
    return config


def write(config, config_file):
    """把配置写到磁盘。写失败不影响运行（例如目录只读）。"""
    try:
        with open(config_file, 'w', encoding='utf-8') as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def load_usage_records(usage_records_file):
    """读取运行时长记录；文件缺失或损坏时返回空 dict。"""
    try:
        if os.path.exists(usage_records_file):
            with open(usage_records_file, 'r', encoding='utf-8') as handle:
                return json.load(handle)
    except (OSError, ValueError):
        pass
    return {}


def save_usage_records(records, usage_records_file):
    """写入运行时长记录。写失败不影响运行。"""
    try:
        with open(usage_records_file, 'w', encoding='utf-8') as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
