# Reactor Product package / Reactor 产品包

- `domain`, `store`, `service`, `api`: the existing Product resource authority.
- `domain`: Product deployment identity consumes Platform-owned `ArtifactRef` values opaquely.
- `remote_engine`: controller-side serving port; both network paths are probed.
- `exchange_handoff`: explicit versioned resource transfer to Exchange drafts.
- `cli`: explicit Product controller setup; reference execution remains test-only.

具体引擎只存在于 `Cyrene-Plugins-Official`。产品侧保持 Deployment、Endpoint 权威；
私有地址、凭据和模型路径不会导出到公共资源接口。
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor Product 软件包

- `domain`、`store`、`service`、`api`：现有 Product 资源权威所在位置。
- `domain`：Product 部署标识以不透明方式使用 Platform 所有的 `ArtifactRef` 值。
- `remote_engine`：controller 侧服务端口；会探测两条网络路径。
- `exchange_handoff`：向 Exchange 草稿显式传输有版本的资源。
- `cli`：显式配置 Product controller；参考执行只用于测试。

具体引擎仅存在于 `Cyrene-Plugins-Official`。Product 侧持有 Deployment 和 Endpoint 权威；私有地址、凭据和模型路径不会导出到公开资源接口。
