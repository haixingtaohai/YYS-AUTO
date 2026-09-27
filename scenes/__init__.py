"""游戏场景处理模块包。

每个场景模块对外暴露：

- ``handle_scene(ctx) -> SceneResult``：处理一轮识别结果
- ``handle_no_recognition(ctx)``：可选，未识别到任何图片时调用（只有困28单人、
  困28队长、结界突破三个场景需要）

场景名到模块的映射见 :mod:`scenes.registry`。
"""
