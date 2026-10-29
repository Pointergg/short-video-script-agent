# 短视频脚本运行报告

- 状态：failed
- 运行模式：mock / offline-simulator-v1
- 说明：工具失败：SEARCH_UNAVAILABLE
- 预计总时长：None 秒

## 可编辑脚本

无可交付脚本。未通过草稿可在 JSON 的 draft 字段查看。

## 补充信息


## 风险

- 本次为离线 Mock：仅证明工程流程，不证明真实模型决策或创作质量。
- 时长为文本启发式估算，未使用真实配音测量。
- 创意范围受已批准文案和画面白名单限制；任意语义改写需另行人工审核。
- 尚未进行真实平台政策、法律合规或最终视频审核。
- 任务未完成；draft 仅供排查，不能当作已验收脚本发布。

## 动作记录

| 步骤 | 动作来源 | 动作 | 简要依据 | 结果 |
|---|---|---|---|---|
| 1 | offline_simulator | search_materials | 先检索主题对应的可引用事实。 | {"ok": false, "error": "SEARCH_UNAVAILABLE"} |
| 2 | offline_simulator | fail | 工具失败且本次没有可靠替代事实来源。 | {"ok": true, "status": "failed"} |
