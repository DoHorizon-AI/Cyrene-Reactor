# Platform SDK typing / 平台 SDK 类型

`cy_artifacts.pyi` supplies types for the existing public methods consumed from
Platform commit `6a561793b476e295e7f70bdeb04a692c6393cf3e`. That Python SDK currently
has no `py.typed` marker. These are method signatures only; all Artifact wire
validation, hashing, publishing and staging execute in the pinned Platform SDK.

该文件仅为尚无 `py.typed` 的平台 SDK 提供已使用方法的签名，不实现另一套 Artifact
数据结构或校验器。实际执行全部由固定版本的平台 SDK 完成。
---
<!-- Chinese Translation / 中文翻译 -->

# Platform SDK 类型声明

`cy_artifacts.pyi` 为 Reactor 所使用的 Platform commit `6a561793b476e295e7f70bdeb04a692c6393cf3e` 中现有公开方法提供类型声明。该 Python SDK 目前没有 `py.typed` 标记。这些内容只有方法签名；所有 Artifact wire 验证、哈希计算、发布和暂存操作仍由固定版本的 Platform SDK 执行。

该文件只为尚无 `py.typed` 标记的平台 SDK 提供已使用方法的签名，不会再实现一套 Artifact 数据结构或验证器。实际操作全部由固定版本的平台 SDK 负责。
