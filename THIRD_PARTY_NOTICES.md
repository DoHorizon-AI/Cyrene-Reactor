# Third-party notices / 第三方声明

Reactor's first-party source, documentation, schemas, and generated Product
contract files are licensed under the Apache License 2.0; see
[`LICENSE`](LICENSE). No upstream source is copied into this repository.
Runtime, Product, and Rust dependencies retain their own licenses.

Reactor 自有源码、文档、schema 与生成的产品契约文件依据 Apache License 2.0 提供，
详见 [`LICENSE`](LICENSE)。本仓库没有复制上游源码。运行时、产品层与 Rust 依赖仍适用
各自许可证。

The authoritative direct-dependency, upstream-revision, license, and SBOM
inventory is [`docs/DEPENDENCY-LICENSES.md`](docs/DEPENDENCY-LICENSES.md). The
Python lockfiles and [`Cargo.lock`](Cargo.lock) are the reproducible records
for the complete resolved graphs. Do not infer a dependency's license from
Reactor's Apache metadata.

权威的直接依赖、上游 revision、许可证与 SBOM 清单位于
[`docs/DEPENDENCY-LICENSES.md`](docs/DEPENDENCY-LICENSES.md)。Python 锁文件与
[`Cargo.lock`](Cargo.lock) 是完整解析图的可复现记录。不要根据 Reactor 的 Apache 元数据
推断依赖的许可证。

One release gate is currently explicit:

当前有一个明确的发布门禁：

1. The pinned Plugins runtime has no license field in its upstream package
   metadata. It must receive explicit license metadata and remain cloneable at
   the pinned immutable revision before the public dependency closure is
   complete.

1. 锁定的 Plugins runtime 上游包元数据没有 license 字段。在公开依赖闭包完成前，必须
   补充明确许可证元数据，并确保锁定的不可变 revision 可被克隆。

The host-placement binary no longer links `cy-adapter-client`; CI rejects any
attempt to reintroduce that dependency. Its remaining Platform contract and
placement dependencies declare Apache-2.0.

host-placement 二进制已不再链接 `cy-adapter-client`；CI 会拒绝重新引入该依赖。其余
Platform contract 与 placement 依赖均声明为 Apache-2.0。

The repository does not bundle vLLM, KServe, model weights, datasets, or
deployment credentials. Those are replaceable/future integration targets and
must be reviewed separately if a future distribution includes them.

本仓库不捆绑 vLLM、KServe、模型权重、数据集或部署凭据。它们是可替换或未来集成目标；
如果未来发行版包含这些内容，必须单独完成许可证审查。
