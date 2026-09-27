"""场景模块行为对比测试（重构安全网）

用途
----
在重构前后跑同一批 fixture，把「点击坐标序列 / 日志 / random 调用 / sleep /
adb 子进程调用 / 异常 / 返回状态」录成规范化的 trace，然后逐条比对。

基线源码放在 tools/_baseline/ 下（重构前的快照）。脚本会自动识别被测模块用的是
旧接口（8~11 个位置参数、返回 4/5/6 元组）还是新接口（handle_scene(ctx)）。

用法
----
    python tools/scene_parity.py --record        # 录制基线 -> tools/_baseline/trace.json
    python tools/scene_parity.py --check         # 用当前源码比对基线
    python tools/scene_parity.py --check -v      # 有差异时打印逐条 diff

注意
----
本脚本**不会**触碰 config.json / usage_records.json：所有记录都在内存里完成。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BASELINE_SCENES = os.path.join(ROOT, "tools", "_baseline", "scenes")
LIVE_SCENES = os.path.join(ROOT, "scenes")
TRACE_FILE = os.path.join(ROOT, "tools", "_baseline", "trace.json")

# 场景 fixture 的默认点击坐标基准
CLICK_X, CLICK_Y = 777, 666


# --------------------------------------------------------------------------
# 场景规格：额外选项、返回槽位、切换目标
# --------------------------------------------------------------------------
# returns 用规范化名字；'switch' 槽位在旧接口里是布尔量，映射为目标场景名。
SCENE_SPECS = {
    "yyh": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "htdr": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "sj": {"extra": ["link_enabled", "check_teammates_ready", "mark_teammates_unready"],
           "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    # dy 的旧接口把回调叫 is_ready_callback / mark_unready_callback，新接口统一为 on_ready / on_unready
    "dy": {"extra": ["on_ready", "on_unready"],
           "extra_old": ["is_ready_callback", "mark_unready_callback"],
           "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "dj": {"extra": ["dj_jinsheng_stop"],
           "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "dg": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "k28": {"extra": ["huijuan_mode"],
            "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_putong_boss", "need_wait", "switch"],
            "switch_target": "结界突破"},
    "k281": {"extra": [],
             "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_putong_boss", "need_wait"]},
    "k280": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "yjsl": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "yl": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "ql": {"extra": ["ql_fangqi", "ql_zaici"],
           "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
    "dfw": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan", "need_wait"]},
    "jjtp": {"extra": ["huijuan_mode"],
             "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan", "switch"],
             "switch_target": "困28单人"},
    "hdpt": {"extra": [], "returns": ["stop", "current_count", "consecutive_challenge", "last_clicked_tiaozhan"]},
}

# 旧接口里 last_clicked 参数的名字（每个场景只有一个槽位，但叫法不同）。
# 注意 dfw 的 last_clicked_chufa 与其它场景的 last_clicked_tiaozhan 是同一个槽位。
CLICKED_FIELD = {
    "k28": "last_clicked_putong_boss",
    "k281": "last_clicked_putong_boss",
    "dfw": "last_clicked_chufa",
}
DEFAULT_CLICKED_FIELD = "last_clicked_tiaozhan"

# 旧形参名 -> 规范化状态键
CLICKED_STATE_KEY = {
    "last_clicked_putong_boss": "last_clicked_putong_boss",
    "last_clicked_chufa": "last_clicked_tiaozhan",
    "last_clicked_tiaozhan": "last_clicked_tiaozhan",
}

# 旧形参名 -> 规范化选项键
OPTION_ALIASES = {
    "is_ready_callback": "on_ready",
    "mark_unready_callback": "on_unready",
}

# 只有这三个场景的 handle_no_recognition 会被主循环真正调用（对应 main.py 的
# 未识别分支）：困28单人 / 困28队长累计 5 次未识别才滑一次屏，结界突破每次都调。
NO_RECOGNITION_PRESETS = {"k28": "困28单人", "k281": "困28队长", "jjtp": "结界突破"}


# --------------------------------------------------------------------------
# 测试替身
# --------------------------------------------------------------------------
def _sanitize(text):
    """去掉内存地址，保证 trace 可复现。"""
    return re.sub(r"0x[0-9a-fA-F]+", "0xADDR", str(text))


class FakeRecognizer:
    """记录所有交互的假 recognizer。"""

    def __init__(self, trace):
        self.trace = trace
        self.adb_path = "adb"
        self.device = "emulator-5554"
        self.click_x = CLICK_X
        self.click_y = CLICK_Y
        self.threshold = 0.8
        self.match_workers = 1
        self.png_folder = os.path.join(ROOT, "png", "k28")
        self.folder = None
        self.running = True
        self.tiaozhan_count = 0
        self.stop_reason = ""
        self.template_filter = None
        self.skip_sleep = False
        self.pg0_threshold = 0.9
        self.q0_threshold = 0.9
        self._run_once_script = []
        self._run_once_index = 0

    # --- 被场景调用的接口 ---
    def click(self, x, y):
        self.trace["clicks"].append([x, y])
        return True

    def stop(self):
        self.trace["reasons"].append("recognizer.stop()")
        self.running = False

    def run_once(self):
        if self._run_once_index < len(self._run_once_script):
            out = self._run_once_script[self._run_once_index]
            self._run_once_index += 1
            return out
        return None

    # --- 快照 ---
    def snapshot(self):
        return {
            "tiaozhan_count": self.tiaozhan_count,
            "stop_reason": self.stop_reason,
            "skip_sleep": self.skip_sleep,
            "running": self.running,
            "folder": self.folder,
            "adb_path": self.adb_path,
            "dynamic": {
                k: v for k, v in sorted(vars(self).items())
                if k.startswith(("tiaozhan_count_dg", "jjtp_"))
            },
        }


class Env:
    """一次用例的录制环境：patch 掉 random / sleep / subprocess。"""

    def __init__(self, trace):
        self.trace = trace
        self.original_randint = random.randint
        self.original_choice = random.choice
        self.original_sleep = None
        self.original_subprocess_run = None
        self.clock = 1_700_000_000.0

    def __enter__(self):
        def traced_randint(a, b):
            val = self.original_randint(a, b)
            self.trace["randoms"].append(["randint", a, b, val])
            return val

        def traced_choice(seq):
            seq = list(seq)
            val = self.original_choice(seq)
            idx = seq.index(val)
            self.trace["randoms"].append(["choice", seq, idx, val])
            return val

        def fake_sleep(seconds):
            self.trace["sleeps"].append(round(float(seconds), 4))
            self.clock += float(seconds)

        def fake_run(cmd, *args, **kwargs):
            self.trace["subcalls"].append(_sanitize(cmd))
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        random.randint = traced_randint
        random.choice = traced_choice
        self.original_sleep = __import__("time").sleep
        __import__("time").sleep = fake_sleep
        self.original_subprocess_run = subprocess.run
        subprocess.run = fake_run
        return self

    def __exit__(self, *exc):
        random.randint = self.original_randint
        random.choice = self.original_choice
        __import__("time").sleep = self.original_sleep
        subprocess.run = self.original_subprocess_run
        return False


# --------------------------------------------------------------------------
# 模块加载
# --------------------------------------------------------------------------
def load_module(name, scenes_dir):
    """按文件路径加载模块，避免与另一个版本同名冲突。"""
    tag = "baseline" if scenes_dir == BASELINE_SCENES else "live"
    unique = f"parity_{tag}_{name}"
    if unique in sys.modules:
        return sys.modules[unique]
    path = os.path.join(scenes_dir, f"{name}.py")
    spec = importlib.util.spec_from_file_location(unique, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    spec.loader.exec_module(module)
    return module


def uses_new_api(module):
    """新接口的 handle_scene 只有一个参数 ctx。"""
    import inspect
    params = list(inspect.signature(module.handle_scene).parameters)
    return params == ["ctx"]


# --------------------------------------------------------------------------
# 用例执行
# --------------------------------------------------------------------------
def make_result(name, x=400, y=300):
    return {"name": name, "center": (x, y), "confidence": 0.95}


def build_options(scene, overrides):
    """构造场景选项。旧接口直接展开成 kwargs，新接口塞进 SceneOptions。"""
    opts = {
        "huijuan_mode": False,
        "link_enabled": False,
        "dj_jinsheng_stop": False,
        "ql_fangqi": False,
        "ql_zaici": False,
        "on_ready": None,
        "on_unready": None,
        "check_teammates_ready": None,
        "mark_teammates_unready": None,
    }
    opts.update(overrides)
    return opts


def call_scene(module, spec, scene, rec, env, results, state, options):
    """调用 handle_scene，返回规范化后的输出字典。"""
    log = env.trace["logs"].append

    if uses_new_api(module):
        from scenes.scene_api import SceneContext, SceneOptions, SceneState

        scene_state = SceneState(
            current_count=state["current_count"],
            target_count=state["target_count"],
            count_challenge=state["count_challenge"],
            consecutive_challenge=state["consecutive_challenge"],
            last_clicked_tiaozhan=state["last_clicked_tiaozhan"],
            last_clicked_putong_boss=state["last_clicked_putong_boss"],
        )
        ctx = SceneContext(
            results=results,
            recognizer=rec,
            log=log,
            state=scene_state,
            options=SceneOptions(**options),
        )
        result = module.handle_scene(ctx)

        outs = {}
        for key in spec["returns"]:
            if key == "switch":
                outs["switch_to"] = result.switch_to
            elif key == "stop":
                outs["stop"] = bool(result.stop)
            elif key == "need_wait":
                outs["need_wait"] = bool(result.need_wait)
            else:
                outs[key] = getattr(scene_state, key)
        # 回写状态
        state["current_count"] = scene_state.current_count
        state["consecutive_challenge"] = scene_state.consecutive_challenge
        state["last_clicked_tiaozhan"] = scene_state.last_clicked_tiaozhan
        state["last_clicked_putong_boss"] = scene_state.last_clicked_putong_boss
        return outs

    # --- 旧接口 ---
    clicked_field = CLICKED_FIELD.get(scene, DEFAULT_CLICKED_FIELD)
    args = [
        results,
        rec,
        log,
        state["current_count"],
        state["target_count"],
        state["count_challenge"],
        state["consecutive_challenge"],
        state[CLICKED_STATE_KEY[clicked_field]],
    ]
    kwargs = {old: options[OPTION_ALIASES.get(old, old)]
              for old in spec.get("extra_old", spec["extra"])}
    ret = module.handle_scene(*args, **kwargs)

    outs = {}
    for key, val in zip(spec["returns"], ret):
        if key == "switch":
            outs["switch_to"] = spec["switch_target"] if val else None
        elif key.startswith("last_clicked"):
            outs[key] = bool(val)
            state[key] = bool(val)
        elif key in ("stop", "need_wait"):
            # 旧接口里 jjtp 的 stop_flag 会被 _handle_0q 的返回值覆盖成 None，
            # 主循环只写 `if stop_flag:`，None 与 False 等价。这里统一成 bool，
            # 让比较聚焦在可观察行为上。
            outs[key] = bool(val)
            state[key] = bool(val)
        else:
            outs[key] = val
            state[key] = val
    return outs


def call_no_recognition(module, rec, env, state):
    """调用 handle_no_recognition。

    主循环忽略它的返回值（只在意它的副作用：滑动屏幕、重置结界突破的内部状态），
    所以这里不记录返回值，只通过 recognizer 快照体现副作用。
    """
    if not hasattr(module, "handle_no_recognition"):
        return
    log = env.trace["logs"].append
    if uses_new_api(module):
        from scenes.scene_api import SceneContext, SceneOptions, SceneState

        ctx = SceneContext(
            results=[], recognizer=rec, log=log,
            state=SceneState(), options=SceneOptions(),
        )
        module.handle_no_recognition(ctx)
        return
    try:
        module.handle_no_recognition(rec, log, rec.device)
    except TypeError:
        module.handle_no_recognition()


def apply_no_recognition_branch(module, scene, rec, env, state):
    """复刻 main.py 未识别到图片时的循环级处理，保证下一轮看到的状态一致。"""
    state["last_clicked_tiaozhan"] = False
    preset = NO_RECOGNITION_PRESETS.get(scene)
    if preset is None:
        return
    if preset == "结界突破":
        call_no_recognition(module, rec, env, state)
        return
    # 困28单人和困28队长：累计 5 次未识别才滑一次屏
    state["last_clicked_putong_boss"] = False
    state["recognition_attempts"] += 1
    if state["recognition_attempts"] >= 5:
        call_no_recognition(module, rec, env, state)
        state["recognition_attempts"] = 0


def run_case(case, scenes_dir):
    """跑一个用例，返回完整 trace。"""
    # 每个用例都重新播种：否则用例之间会共享全局 random 流，
    # 前一个用例多消耗一次 randint 就会让后面的用例坐标整体错位。
    random.seed(case["seed"])

    trace = {
        "case": case["name"],
        "scene": case.get("scene", case["kind"]),
        "iterations": [],
        "logs": [],
        "randoms": [],
        "sleeps": [],
        "subcalls": [],
        "reasons": [],
        "clicks": [],
    }

    if case["kind"] == "close_jiacheng":
        module = load_module("guanbijiacheng", scenes_dir)
        rec = FakeRecognizer(trace)
        rec._run_once_script = [[make_result(n) for n in it] if it else None
                                for it in case["script"]]
        rec.folder = case.get("initial_folder")
        with Env(trace) as env:
            log = trace["logs"].append
            try:
                ret = module.handle_close_jiacheng(
                    rec, log, case["jiacheng_folder"], rec.device)
                trace["return"] = ret
            except Exception as exc:  # noqa: BLE001
                trace["exception"] = _sanitize(f"{type(exc).__name__}: {exc}")
        trace["final"] = rec.snapshot()
        return trace

    if case["kind"] == "dinghao":
        module = load_module("dinghao", scenes_dir)
        rec = FakeRecognizer(trace)
        with Env(trace) as env:
            log = trace["logs"].append
            try:
                module.handle_dinghao(rec, log, case.get("wait_seconds", 3), rec.device)
            except Exception as exc:  # noqa: BLE001
                trace["exception"] = _sanitize(f"{type(exc).__name__}: {exc}")
        trace["final"] = rec.snapshot()
        return trace

    # --- 普通场景 ---
    scene = case["scene"]
    spec = SCENE_SPECS[scene]
    module = load_module(scene, scenes_dir)
    options = build_options(scene, case.get("options", {}))
    state = {
        "current_count": 0,
        "target_count": case.get("target_count", 200),
        "count_challenge": case.get("count_challenge", True),
        "consecutive_challenge": 0,
        "recognition_attempts": 0,
        "last_clicked_tiaozhan": False,
        "last_clicked_putong_boss": False,
    }

    # 一个用例 = 一次运行：recognizer 全程复用。
    # 这点很关键——jjtp 的 card57 状态、dg 的 tiaozhan_count_dg 都挂在 recognizer 上，
    # 每轮新建会丢掉这些跨轮状态，与 main.py 的真实行为不符。
    rec = FakeRecognizer(trace)

    for index, iteration in enumerate(case["iterations"]):
        with Env(trace) as env:
            iteration_trace = {"index": index, "clicks": [], "logs": [],
                               "randoms": [], "sleeps": [], "subcalls": [],
                               "reasons": []}
            clicks_before = len(trace["clicks"])
            logs_before = len(trace["logs"])
            randoms_before = len(trace["randoms"])
            sleeps_before = len(trace["sleeps"])
            subcalls_before = len(trace["subcalls"])
            reasons_before = len(trace["reasons"])

            try:
                if iteration.get("no_recognition"):
                    apply_no_recognition_branch(module, scene, rec, env, state)
                else:
                    results = ([make_result(n[0], n[1], n[2]) if isinstance(n, (list, tuple))
                                else make_result(n) for n in iteration["results"]]
                               if iteration.get("results") else [])
                    outputs = call_scene(module, spec, scene, rec, env, results,
                                         state, options)
                    iteration_trace["outputs"] = outputs
            except Exception as exc:  # noqa: BLE001
                iteration_trace["exception"] = _sanitize(f"{type(exc).__name__}: {exc}")

            iteration_trace["clicks"] = trace["clicks"][clicks_before:]
            iteration_trace["logs"] = trace["logs"][logs_before:]
            iteration_trace["randoms"] = trace["randoms"][randoms_before:]
            iteration_trace["sleeps"] = trace["sleeps"][sleeps_before:]
            iteration_trace["subcalls"] = trace["subcalls"][subcalls_before:]
            iteration_trace["reasons"] = trace["reasons"][reasons_before:]
            iteration_trace["recognizer"] = rec.snapshot()
            trace["iterations"].append(iteration_trace)

    return trace


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
def basic(name, results, **kw):
    return {"kind": "scene", "name": name, "results": results, **kw}


def scene_cases(scene, seed, extra_iterations=None):
    """每个场景的通用 fixture：空结果 / 主识别 / 多轮累积。"""
    cases = [
        {"kind": "scene", "scene": scene, "name": f"{scene}:empty", "seed": seed,
         "iterations": [{"results": []}]},
        {"kind": "scene", "scene": scene, "name": f"{scene}:no_recognition_x5", "seed": seed + 1,
         "iterations": [{"no_recognition": True} for _ in range(5)]},
    ]
    if extra_iterations:
        cases.append({"kind": "scene", "scene": scene, "name": f"{scene}:main", "seed": seed + 2,
                      "iterations": extra_iterations})
    return cases


def build_fixtures():
    cases = []

    # ---- 业原火 yyh ----
    cases += scene_cases("yyh", 1001, [
        {"results": ["jujue.png"]},
        {"results": ["suoding.png", "tiaozhan.png"]},
        {"results": ["tansuoye.png"]},
        {"results": ["yyh.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["jiangli.png"]},
        {"results": ["tiaozhan.png", "shengli.png"]},
    ])

    # ---- 魂土单人 htdr ----
    cases += scene_cases("htdr", 1101, [
        {"results": ["jujue.png"]},
        {"results": ["suoding.png", "tiaozhan.png"]},
        {"results": ["tansuoye.png"]},
        {"results": ["bqds.png"]},
        {"results": ["100-tansuo.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["baozang.png"]},
        {"results": ["jiangli.png"]},
    ])

    # ---- 司机 sj：队员未准备 / 已准备 两条路径 ----
    for label, ready in (("teammates_not_ready", False), ("teammates_ready", True)):
        cases.append({
            "kind": "scene", "scene": "sj", "name": f"sj:{label}", "seed": 1201,
            "options": {
                "link_enabled": True,
                "check_teammates_ready": (lambda r=ready: r),
                "mark_teammates_unready": (lambda: None),
            },
            "iterations": [
                {"results": ["tiaozhan.png"]},
                {"results": ["jiangli.png"]},
                {"results": ["baozang.png"]},
                {"results": ["yaoqing.png"]},
                {"results": ["tiaozhan.png"]},
            ],
        })
    cases += scene_cases("sj", 1202, [
        {"results": ["jujue.png"]},
        {"results": ["shengli.png"]},
    ])

    # ---- 队员 dy：回调触发 ----
    ready_calls = []
    cases.append({
        "kind": "scene", "scene": "dy", "name": "dy:callbacks", "seed": 1301,
        "options": {
            "on_ready": (lambda: ready_calls.append("ready")),
            "on_unready": (lambda: ready_calls.append("unready")),
        },
        "iterations": [
            {"results": ["duiwu.png"]},
            {"results": ["jiangli.png"]},
            {"results": ["jieshou.png"]},
            {"results": ["baozang.png"]},
            {"results": ["jujue.png"]},
        ],
    })
    cases += scene_cases("dy", 1302, [{"results": ["jieshou.png"]}])

    # ---- 斗技 dj：jinsheng 开关两条路径 ----
    for label, stop in (("stop_on", True), ("stop_off", False)):
        cases.append({
            "kind": "scene", "scene": "dj", "name": f"dj:jinsheng_{label}", "seed": 1401,
            "options": {"dj_jinsheng_stop": stop},
            "iterations": [
                {"results": ["jinsheng.png"]},
                {"results": ["jixu.png", "jieshu.png"]},
                {"results": ["zhandou.png"]},
                {"results": ["zhandou.png"]},
                {"results": ["jujue.png"]},
                {"results": ["zhunbei.png"]},
            ],
        })
    cases += scene_cases("dj", 1402, [{"results": ["zhandou.png"]}])

    # ---- 道馆 dg：等待屏蔽 + 挑战 5 次冷却 ----
    cases += scene_cases("dg", 1501, [
        {"results": ["dengdaigz.png"]},
        {"results": ["dengdaikz.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["zhunbei.png"]},
        {"results": ["shengli.png"]},
        {"results": ["yxnjc.png"]},
        {"results": ["jujue.png", "shibai.png"]},
    ])

    # ---- 困28单人 k28：huijuan 切换 / boss+putong 屏蔽 / 奖励重置 ----
    for label, huijuan in (("huijuan_on", True), ("huijuan_off", False)):
        cases.append({
            "kind": "scene", "scene": "k28", "name": f"k28:30q_{label}", "seed": 1601,
            "options": {"huijuan_mode": huijuan},
            "iterations": [{"results": ["30q.png"]}, {"results": ["boss.png"]}],
        })
    cases += scene_cases("k28", 1602, [
        {"results": ["jujue.png"]},
        {"results": ["jjtp.png"]},
        {"results": ["ssl.png"]},
        {"results": ["boss.png", "putong.png"]},
        {"results": ["putong.png"]},
        {"results": ["baozang.png"]},
        {"results": ["xuanze.png"]},
        {"results": ["jianglik28.png"]},
        {"results": ["tansuo.png"]},
        {"results": [["boss.png", 500, 600]]},
    ])

    # ---- 困28队长 k281 ----
    cases += scene_cases("k281", 1701, [
        {"results": ["jujue.png"]},
        {"results": ["jjtp.png"]},
        {"results": ["ssl.png"]},
        {"results": ["boss.png", "putong.png"]},
        {"results": ["putong.png"]},
        {"results": ["baozang.png"]},
        {"results": ["jinru.png"]},
        {"results": ["yaoqing.png"]},
        {"results": ["jiangli.png"]},
        {"results": ["boss.png"]},
        {"results": ["boss.png"]},
        {"results": ["boss.png"]},
        {"results": ["boss.png"]},
    ])

    # ---- 困28队员 k280 ----
    cases += scene_cases("k280", 1801, [
        {"results": ["jujue.png"]},
        {"results": ["baozang.png"]},
        {"results": ["jieshou.png"]},
        {"results": ["jiangli.png"]},
        {"results": ["jianglik28.png"]},
        {"results": ["shengli.png"]},
    ])

    # ---- 英杰试炼 yjsl ----
    cases += scene_cases("yjsl", 1901, [
        {"results": ["jujue.png"]},
        {"results": ["suoding.png", "tiaozhan.png"]},
        {"results": ["gbyw.png"]},
        {"results": ["jytx.png"]},
        {"results": ["zhunbei.png"]},
        {"results": ["ccsl.png"]},
        {"results": ["100-tansuo.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["shengli.png"]},
    ])

    # ---- 御灵 yl ----
    cases += scene_cases("yl", 2001, [
        {"results": ["jujue.png"]},
        {"results": ["suoding.png", "tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["jiangli.png"]},
        {"results": ["shengli.png"]},
    ])

    # ---- 契灵 ql：放弃/再次四种组合 ----
    for label, fangqi, zaici in (("ff", True, False), ("zz", False, True),
                                 ("fz", True, True), ("zf", False, False)):
        cases.append({
            "kind": "scene", "scene": "ql", "name": f"ql:fangqi_{label}", "seed": 2101,
            "options": {"ql_fangqi": fangqi, "ql_zaici": zaici},
            "iterations": [
                {"results": ["fangqi.png"]},
                {"results": ["zaici.png"]},
                {"results": ["suoding.png"]},
                {"results": ["tancha-tiaozhan.png"]},
                {"results": ["jieqi-tiaozhan.png"]},
                {"results": ["jiangli4.png"]},
                {"results": ["jixu4.png"]},
                {"results": ["jujue.png"]},
            ],
        })

    # ---- 大富翁 dfw：固定坐标 / 随机四选一 / chufa 计数 ----
    cases += scene_cases("dfw", 2201, [
        {"results": ["jujue.png"]},
        {"results": ["suoding.png", "chufa.png"]},
        {"results": ["tishi.png"]},
        {"results": ["touzhi.png"]},
        {"results": ["qiangduo.png"]},
        {"results": ["qiangduo.png"]},
        {"results": ["chufa.png"]},
        {"results": ["chufa.png"]},
        {"results": ["dfwrk.png"]},
        {"results": ["rkjl.png"]},
        {"results": ["exit.png"]},
    ])

    # ---- 结界突破 jjtp：card57 阶梯 / jingong 异常 / 0q 切换 ----
    card57_ladder = [
        {"results": ["pg0.png"]},
        {"results": ["tuichu.png", "tuichu2.png"]},
        {"results": ["tuichu.png"]},
        {"results": ["tuichu.png"]},
        {"results": ["tuichu.png"]},
        {"results": ["tuichu.png"]},
    ]
    for label, huijuan in (("huijuan_on", True), ("huijuan_off", False)):
        cases.append({
            "kind": "scene", "scene": "jjtp", "name": f"jjtp:0q_{label}", "seed": 2301,
            "options": {"huijuan_mode": huijuan},
            "iterations": [{"results": ["0q.png"]}, {"results": ["exit.png"]}],
        })
    cases.append({
        "kind": "scene", "scene": "jjtp", "name": "jjtp:card57_ladder", "seed": 2302,
        "iterations": card57_ladder,
    })
    cases.append({
        "kind": "scene", "scene": "jjtp", "name": "jjtp:card57_numbers_skip_sleep", "seed": 2303,
        "iterations": [
            {"results": ["pg0.png", "3.png"]},
            {"results": ["tuichu.png", "2.png"]},
        ],
    })
    cases += scene_cases("jjtp", 2304, [
        {"results": ["jujue.png"]},
        {"results": ["jingong.png", "3.png"]},
        {"results": ["jingong.png", "4.png"]},
        {"results": ["jingong.png", "5.png"]},
        {"results": ["jingong.png", "2.png"]},
        {"results": ["suoding.png"]},
        {"results": ["tansuo.png"]},
        {"results": ["cixinleyuan-tansuo.png"]},
        {"results": ["shibai.png"]},
        {"results": ["queren.png"]},
        {"results": ["jinru.png"]},
        {"results": ["jiangli.png", "1.png"]},
        {"results": ["100-tansuo.png"]},
    ])

    # ---- 活动爬塔 hdpt ----
    # rkjl 用例单独标注：重构前会 TypeError 崩溃，这是已知线上 bug
    cases += scene_cases("hdpt", 2401, [
        {"results": ["jujue.png"]},
        {"results": ["exit.png"]},
        {"results": ["suoding.png"]},
        {"results": ["suoding.png", "tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["tiaozhan.png"]},
        {"results": ["pt.png"]},
        {"results": ["hdrk.png"]},
        {"results": ["rukou4.png"]},
        {"results": ["buji.png"]},
        {"results": ["mrjiangli.png"]},
        {"results": ["rkbj.png"]},
        {"results": ["tishi.png"]},
        {"results": ["jiangli.png"]},
        {"results": ["shengli.png"]},
        {"results": ["jiangli3.png"]},
    ])
    cases.append({
        "kind": "scene", "scene": "hdpt", "name": "hdpt:rkjl_known_crash", "seed": 2402,
        "known_bug": "重构前 _click_random_xy 参数数量不匹配 -> TypeError",
        "iterations": [{"results": ["rkjl.png"]}],
    })

    # ---- 关闭加成 / 顶号 ----
    cases.append({
        "kind": "close_jiacheng", "name": "close_jiacheng:success", "seed": 2501,
        "script": [["guanbi.png"], ["jinru.png"], ["yxnjc.png"]],
        "jiacheng_folder": os.path.join(ROOT, "png", "jiacheng"),
        "initial_folder": None,
    })
    cases.append({
        "kind": "close_jiacheng", "name": "close_jiacheng:timeout", "seed": 2502,
        "script": [[] for _ in range(3)],
        "jiacheng_folder": os.path.join(ROOT, "png", "jiacheng"),
        "initial_folder": os.path.join(ROOT, "png", "k28"),
    })
    cases.append({
        "kind": "dinghao", "name": "dinghao:normal", "seed": 2503, "wait_seconds": 3,
    })

    return cases


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def record(scenes_dir):
    results = {}
    for case in build_fixtures():
        try:
            results[case["name"]] = run_case(case, scenes_dir)
        except Exception as exc:  # noqa: BLE001
            results[case["name"]] = {"case": case["name"],
                                     "harness_error": _sanitize(f"{type(exc).__name__}: {exc}")}
    return results


def diff_traces(expected, actual, verbose=False):
    """返回 ``[(用例名, [差异行...]), ...]``。"""
    problems = []
    for name in sorted(expected):
        if name not in actual:
            problems.append((name, ["缺少用例"]))
            continue
        exp, act = expected[name], actual[name]
        if exp == act:
            continue
        details = _explain(exp, act) if verbose else []
        problems.append((name, details or ["不一致"]))
    for name in sorted(set(actual) - set(expected)):
        problems.append((name, ["新增用例（基线里没有）"]))
    return problems


def _explain(exp, act, path="", out=None):
    """递归找出第一层差异，用于诊断。"""
    if out is None:
        out = []
    if len(out) >= 25:
        return out
    if type(exp) is not type(act):
        out.append(f"{path or '<root>'}: 类型 {type(exp).__name__} -> {type(act).__name__}")
        return out
    if isinstance(exp, dict):
        for key in sorted(set(exp) | set(act)):
            if key not in exp:
                out.append(f"{path}.{key}: 新增 {act[key]!r}")
            elif key not in act:
                out.append(f"{path}.{key}: 丢失 {exp[key]!r}")
            else:
                _explain(exp[key], act[key], f"{path}.{key}", out)
    elif isinstance(exp, list):
        if len(exp) != len(act):
            out.append(f"{path}: 长度 {len(exp)} -> {len(act)}")
        for i, (a, b) in enumerate(zip(exp, act)):
            _explain(a, b, f"{path}[{i}]", out)
    elif exp != act:
        out.append(f"{path}: {exp!r} -> {act!r}")
    return out


def main():
    parser = argparse.ArgumentParser(description="场景模块行为对比测试")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", action="store_true", help="录制基线 trace")
    group.add_argument("--check", action="store_true", help="与基线比对")
    group.add_argument("--summary", action="store_true", help="打印基线摘要")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印逐条差异")
    parser.add_argument("--allow-known-bug-fix", action="store_true",
                        help="允许 hdpt:rkjl_known_crash 用例出现差异（已修复该 bug）")
    args = parser.parse_args()

    if args.summary:
        with open(TRACE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        for name, trace in data.items():
            iterations = trace.get("iterations")
            if not iterations:
                print(f"{name:44s} clicks={len(trace['clicks']):3d} "
                      f"return={trace.get('return')} "
                      f"exc={trace.get('exception', '-')}")
                continue
            clicks = sum(len(it["clicks"]) for it in iterations)
            switches = [it["outputs"].get("switch_to") for it in iterations
                        if it.get("outputs", {}).get("switch_to")]
            stops = [i for i, it in enumerate(iterations)
                     if it.get("outputs", {}).get("stop")]
            exceptions = [it["exception"] for it in iterations if it.get("exception")]
            extra = ""
            if switches:
                extra += f" switch={switches}"
            if stops:
                extra += f" stop@{stops}"
            if exceptions:
                extra += f" exc={exceptions}"
            print(f"{name:44s} clicks={clicks:3d} logs={len(trace['logs']):3d} "
                  f"iters={len(iterations)}{extra}")
        return 0

    if args.check:
        with open(TRACE_FILE, encoding="utf-8") as handle:
            expected = json.load(handle)
        # 内存里的 trace 含 tuple，JSON 里是 list。统一走一次 JSON 往返，
        # 否则 random.choice 记录的坐标元组会造成假差异。
        actual = json.loads(json.dumps(record(LIVE_SCENES), ensure_ascii=False))
        problems = diff_traces(expected, actual, args.verbose)

        ignored = set()
        if args.allow_known_bug_fix:
            ignored.add("hdpt:rkjl_known_crash")
        problems = [(name, details) for name, details in problems if name not in ignored]

        if problems:
            print(f"FAIL: {len(problems)} 个用例行为不一致")
            for name, details in problems:
                print(f"  {name}:")
                for line in details:
                    print("      " + line)
            return 1
        print(f"PASS: {len(actual)} 个用例全部与基线一致")
        return 0

    if not os.path.isdir(BASELINE_SCENES):
        print(f"错误: 找不到重构前的场景源码目录 {BASELINE_SCENES}")
        print("录制基线需要它作为对照。请从你自己的备份里恢复 scenes/ 到该目录，")
        print("或者直接用已有的 tools/_baseline/trace.json 跑 --check。")
        return 2

    result = record(BASELINE_SCENES)
    os.makedirs(os.path.dirname(TRACE_FILE), exist_ok=True)
    with open(TRACE_FILE, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)
    crashes = [name for name, trace in result.items()
               if any(it.get("exception") for it in trace.get("iterations", []))
               or trace.get("exception")]
    print(f"已录制 {len(result)} 个用例 -> {TRACE_FILE}")
    print(f"用例中出现异常的场景: {', '.join(crashes) if crashes else '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
