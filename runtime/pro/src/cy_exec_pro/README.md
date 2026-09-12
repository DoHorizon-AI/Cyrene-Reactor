# runtime/pro/src/cy_exec_pro / runtime/pro/src/cy_exec_pro

Pro serving extension package.

Pro 服务扩展包。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/pro/src/cy_exec_pro/core/` | Product-side alert coordination. / Product 侧告警协调。 |
| `runtime/pro/src/cy_exec_pro/engines/` | Reserved namespace with no implementation. / 不含实现的保留命名空间。 |
| `runtime/pro/src/cy_exec_pro/utils/` | Pro logging and shared utility modules. / Pro 日志与共享工具模块。 |
| `runtime/pro/src/cy_exec_pro/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |

## Suggested reading order / 推荐阅读顺序

Start with `runtime/pro/src/cy_exec_pro/core/` and then follow the module imports or package entry point.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `runtime/pro/src/cy_exec_pro/core/` 开始，再按模块导入关系或包入口继续阅读。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
