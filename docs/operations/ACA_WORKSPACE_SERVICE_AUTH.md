# Reactor Workspace service authentication on Azure Container Apps

The Reactor private routes are disabled until a valid Workspace credential map is configured. The deployment workflow currently cannot promote auth configuration. It only performs image deployments while all four auth variables are unset; any auth configuration makes the run fail before it changes Azure resources. This keeps secret registration and revision updates closed until the ACA update path can prevent concurrent deployments from overwriting a newer revision.

## Provisioning prerequisites

1. Create separate random high-entropy secrets for the legacy ControlBearer and the Platform Workspace bearer. Use at least 32 characters for the ControlBearer and at least 32 bytes of entropy for the Workspace bearer. Do not reuse either token for the other purpose. The ControlBearer secret contains the raw bearer token; the Workspace map stores only its SHA-256 digest.
2. Store a version 1 Workspace credential map in a Key Vault secret. Each entry maps a lowercase SHA-256 digest to one fixed organization and Workspace. Generate the Platform bearer with at least 32 bytes of entropy, calculate its digest in the approved secret-management process, and verify the exact scope before storing the map:

   ```json
   {"version":1,"credentials":[{"tokenSha256":"<lowercase SHA-256 hex>","organizationId":"org-id","workspaceId":"workspace-id"}]}
   ```

   During rotation, distinct token digests may map to the same scope. Do not duplicate a digest or add a user, role, or scope supplied by an HTTP request.
3. Store a version 1 serving-binding grant map in a separate Key Vault secret. Grant only explicit `(servingBindingId, organizationId, workspaceId)` tuples approved by the Product owner:

   ```json
   {"version":1,"grants":[{"servingBindingId":"serving-id","organizationId":"org-id","workspaceId":"workspace-id"}]}
   ```

   Existing or historical bindings are not granted automatically. A private create is denied unless its binding and credential scope match one explicit tuple.
4. Assign the Reactor Container App a system-assigned or user-assigned managed identity. Grant that identity `Key Vault Secrets User` on each vault that contains one of the three secrets, or equivalent secret-read access.
5. Keep these resource references and the identity in the reviewed deployment change record:
   - `REACTOR_CONTROL_CREDENTIAL_SECRET_URI`: versionless Azure Key Vault URI for the raw legacy ControlBearer token.
   - `REACTOR_WORKSPACE_CREDENTIAL_MAP_SECRET_URI`: versionless URI for the digest-to-scope JSON map.
   - `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS_SECRET_URI`: versionless URI for the binding-grant JSON map.
   - `REACTOR_WORKSPACE_AUTH_IDENTITY`: `system` or the full resource ID of a user-assigned identity already attached to the app.

   Do not set these GitHub variables yet: any non-empty auth variable intentionally fails the deployment workflow before Azure changes. Never put secret values, raw service tokens, or map JSON in GitHub variables, source control, command output, or workflow logs. Keep the three secrets separate from Yield's credentials.

## Deployment behavior

The workflow deploys on pushes to `main`, `release`, and `develop`, and on manual dispatch. If all four auth variables are unset, it deploys the image and leaves existing ACA authentication settings unchanged. If any auth variable is set, the workflow stops before checkout or any Azure mutation. With no Workspace map configured, `/internal/workspace/v1/model-imports` returns `503`; a successful image deployment does not enable private access by itself.

The automated auth rollout is deliberately closed. Azure's documented [Container Apps Update API](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/container-apps/update) uses JSON Merge Patch and does not document an `If-Match`/ETag precondition. A show-then-update deployment can therefore race another revision update. Do not treat a preflight snapshot or a GitHub workflow lock as protection from portal, IaC, or other out-of-band writers.

Auth promotion is a manual deployment prerequisite until an atomic conditional update or a shared deployment lock for every writer is available. The operator must serialize all writes to the Container App, including Actions, portal, IaC, and other deployment systems; inspect the current app/revision and secret-reference names; apply only the reviewed auth and startup changes; then verify the resulting internal, healthy revision. If the reviewed snapshot changes before the update, stop and re-review. Do not submit a stale exported full app spec. Do not read or print Key Vault contents or ACA secret values.

During the manual update, the Reactor ControlBearer reference must reach the startup bootstrap as an ACA secret reference. The bootstrap must run as container uid `10001`, create `CYRENE_DATA_DIR` (default `/data`) and its `credentials` directory with mode `0700`, write `credentials/control.token` with mode `0600`, unset the temporary environment variable, and then start the existing entrypoint. The API continues reading its configured `credential_file`; never place a credential value in an app command, app spec, workflow log, or deployment record.

The Workspace map and serving-binding grants must be injected through `REACTOR_WORKSPACE_CREDENTIAL_MAP` and `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS`. The Workspace bearer authenticates the Platform service and maps it to a fixed scope; it does not establish a user, Workspace member, or role. Keep the app on single revision mode when enabling auth. Verify internal ingress, all three secret reference names, the bootstrap command, and the resulting healthy revision without exposing secret values.

Removing an active reference or resetting the startup command also requires a separately reviewed, serialized revision update. Key Vault secret rotation should be followed by a Reactor deployment so a fresh revision consumes the current references; verify that the Platform and Reactor ControlBearer callers have rotated in the intended order.

## Failure recovery and cleanup

- An auth-configured Actions run is expected to fail before checkout or Azure changes. Keep the variables unset for image-only deployments; use the reviewed manual process for auth promotion.
- Before manual promotion, validate token digests, fixed scope assignments, and binding-grant tuples. A syntactically valid map can still assign the wrong Workspace or grant a wrong serving binding.
- If an operator's update fails or times out, inspect revision health, image, internal ingress, and environment **secret reference names** only. Do not call `az containerapp secret list --show-values` or `listSecrets`.
- Remove an ACA secret only after confirming no active revision references it. Use name-only secret listing and the normal revision deactivation process; never print secret values.

## 中文说明

Reactor 私有路由在有效 Workspace 凭据映射配置前保持禁用。当前部署工作流只在四个认证变量全部为空时执行镜像更新；只要任一认证变量非空，工作流便会在检出代码或修改 Azure 资源前失败。这样可避免缺少并发条件更新保护时，密钥注册和新 revision 更新覆盖其他部署产生的较新 revision。

ControlBearer 与 Platform Workspace bearer 必须使用不同的高熵随机 token，Workspace token 至少有 32 字节熵。Workspace 凭据映射只保存 token 的小写 SHA-256 摘要及固定组织/Workspace 范围；serving-binding grant 映射只允许经 Product owner 批准的 `(servingBindingId, organizationId, workspaceId)` 元组。旧 binding 不会自动授权。为 Reactor 分配托管身份，并仅授予该身份读取对应 Key Vault secrets 的权限。

认证配置必须由人工按变更流程部署。在整个变更期间，必须使用覆盖 Actions、Azure 门户、IaC 及其他发布系统的统一部署锁，检查当前应用、revision 和密钥引用名称，只提交审查过的认证与启动配置，并验证更新后的内部入口和健康 revision。如果快照已变化，应停止并重新审查。当前官方 Container Apps Update API 文档没有说明 `If-Match`/ETag 条件更新；预检快照或只锁 GitHub workflow 都不能防止门户或其他外部写入者造成竞态。不要提交过期的完整导出 app spec。

所有 token 与 JSON 映射只保存在经批准的密钥管理系统中；工作流、应用命令、变更记录和日志中不得出现密钥值。ControlBearer 启动过程必须以 uid `10001` 运行，目录权限为 `0700`、凭据文件权限为 `0600`，写入后立即 `unset` 临时环境变量，再启动原有 entrypoint。Workspace 映射和 serving-binding grants 必须固定组织与 Workspace 范围；bearer 只代表 Platform 服务身份，不代表最终用户、成员或角色。

认证变量未配置时，镜像发布不改变现有 ACA 认证配置，私有 `/internal/workspace/v1/model-imports` 仍返回 `503`。移除引用、重置启动命令或轮换密钥也需要单独审查并在统一部署锁下更新。检查和清理时只查看密钥引用名称，不读取或打印 Key Vault/ACA 密钥值。
