# Product tests / 产品测试

`test_product_mvp.py` covers persisted Product/reference-port behavior.
`test_cuda_contract.py` covers model completeness, Platform byte verification,
binding denial and preserving recovery identity across uncertain launch results.
`test_exchange_handoff.py` checks explicit Send to, receiver permission and
monotonic Endpoint versions across restart; its engine and receiver are unit fixtures.
Structural fixtures are not runnable models. Real CUDA, streaming, cancellation
and release evidence must be recorded separately for the selected host.

结构测试与 reference-port 测试不等于真实模型推理。指定执行节点的 CUDA、流式、
取消、资源回收证据必须单独验收。
---
<!-- Chinese Translation / 中文翻译 -->

# Product 测试

`test_product_mvp.py` 覆盖持久化 Product 行为和参考端口行为。`test_cuda_contract.py` 覆盖模型完整性、Platform 字节验证、绑定拒绝，以及在启动结果不确定时保留恢复标识。`test_exchange_handoff.py` 检查显式的 Send to、接收方权限和重启前后单调递增的 Endpoint 版本；其中引擎和接收方均为单元测试夹具。

结构夹具不是可运行模型。真实 CUDA、流式处理、取消和资源释放证据必须针对所选主机单独记录。

结构测试和 reference-port 测试不等同于真实模型推理。指定执行节点的 CUDA、流式、取消和资源回收证据必须单独验收。
