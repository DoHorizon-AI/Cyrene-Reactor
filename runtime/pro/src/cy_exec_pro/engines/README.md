# runtime/pro/src/cy_exec_pro/engines / runtime/pro/src/cy_exec_pro/engines

Reserved Product-side namespace. It contains no engine or cache implementation.

保留的 Product 侧命名空间；不包含引擎或缓存实现。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/pro/src/cy_exec_pro/engines/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |

Concrete engines, provider relays, and LoRA execution live in
`Cyrene-Plugins-Official`.

## Suggested reading order / 推荐阅读顺序

There is no runtime path below this namespace. Concrete engines and caches are
resolved as Plugins-owned capabilities.

此命名空间下没有运行路径；具体引擎与缓存通过 Plugins 所有的能力解析。
