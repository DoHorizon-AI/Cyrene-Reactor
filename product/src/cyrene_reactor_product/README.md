# Reactor Product package / Reactor 产品包

- `domain`, `store`, `service`, `api`: the existing Product resource authority.
- `domain`: Product deployment identity consumes Platform-owned `ArtifactRef` values opaquely.
- `remote_engine`: controller-side serving port; both network paths are probed.
- `exchange_handoff`: explicit versioned resource transfer to Exchange drafts.
- `cli`: explicit Product controller setup; reference execution remains test-only.

具体引擎只存在于 `Cyrene-Plugins-Official`。产品侧保持 Deployment、Endpoint 权威；
私有地址、凭据和模型路径不会导出到公共资源接口。
