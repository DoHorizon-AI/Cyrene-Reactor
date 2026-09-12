# Platform SDK typing / 平台 SDK 类型

`cy_artifacts.pyi` supplies types for the existing public methods consumed from
Platform commit `6a561793b476e295e7f70bdeb04a692c6393cf3e`. That Python SDK currently
has no `py.typed` marker. These are method signatures only; all Artifact wire
validation, hashing, publishing and staging execute in the pinned Platform SDK.

该文件仅为尚无 `py.typed` 的平台 SDK 提供已使用方法的签名，不实现另一套 Artifact
数据结构或校验器。实际执行全部由固定版本的平台 SDK 完成。
