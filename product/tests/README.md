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
