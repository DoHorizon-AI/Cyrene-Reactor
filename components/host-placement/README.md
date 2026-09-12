# Host placement / 主机放置接入

This thin executable calls Platform `plan_execution_placement` with a freshly
read canonical KernelCapabilities protobuf, an explicitly confirmed NodeRef,
and a model Artifact already verified by Platform staging. It does not allocate
or launch. Kernel AcquireLease is the subsequent exclusive allocation authority.

该工具只调用 Platform 的现有 Placement 算法，不分配或启动。输入是刚读取的
KernelCapabilities 原协议、用户确认的 NodeRef 与已校验落盘的模型 Artifact。
实际排他分配仍由后续 Kernel AcquireLease 完成。

Build: `cargo build --locked -p cyrene-reactor-host-placement`.
Private JSON on stdin: `capabilities` (protobuf bytes), `node_id`, `node_epoch`,
`minimum_memory_bytes`, `artifact`, `scope`. Output contains selection/rejection
evidence. It is an internal adapter, not a public Product schema.

构建命令同上。标准输入/输出只用于执行端内部适配；路径和授权资料不进入公共接口。
