# runtime/pro/src/cy_exec_pro/core / runtime/pro/src/cy_exec_pro/core

Product-side alert coordination.

Product 侧告警协调。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/pro/src/cy_exec_pro/core/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |
| `runtime/pro/src/cy_exec_pro/core/alert_manager.py` | Python runtime or test module: alert_manager.py. / Python 运行时或测试模块：alert_manager.py。 |

Concrete engines and selection live in `Cyrene-Plugins-Official`; hardware
facts remain Platform-owned.

## Suggested reading order / 推荐阅读顺序

Start with `runtime/pro/src/cy_exec_pro/core/__init__.py` and then follow the module imports or package entry point.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `runtime/pro/src/cy_exec_pro/core/__init__.py` 开始，再按模块导入关系或包入口继续阅读。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
