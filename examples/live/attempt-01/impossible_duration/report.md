# 短视频脚本运行报告

- 状态：failed
- 运行模式：live / deepseek-chat
- 说明：模型调用或动作解析失败。
- 预计总时长：4.0 秒

## 可编辑脚本

无可交付脚本。未通过草稿可在 JSON 的 draft 字段查看。

## 补充信息


## 风险

- 时长为文本启发式估算，未使用真实配音测量。
- 创意范围受已批准文案和画面白名单限制；任意语义改写需另行人工审核。
- 尚未进行真实平台政策、法律合规或最终视频审核。
- 任务未完成；draft 仅供排查，不能当作已验收脚本发布。

## 动作记录

| 步骤 | 动作 | 简要依据 | 结果 |
|---|---|---|---|
| 1 | search_materials | 先检索产品素材以获取可引用的事实与标题 | {"ok": true, "count": 1} |
| 2 | write_script | 已检索到产品事实，用一条fact与一条neutral_copy组成1秒内简洁脚本 | {"ok": true} |
| 3 | estimate_duration | 先估算当前两镜草稿是否超过1秒上限 | {"ok": true, "total_seconds": 4.0, "within_limit": false} |
| 4 | model_error | 模型调用或动作解析失败。 | {"ok": false, "error": "MODEL_INVALID_RESPONSE"} |
