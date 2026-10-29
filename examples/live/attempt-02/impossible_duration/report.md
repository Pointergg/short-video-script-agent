# 短视频脚本运行报告

- 状态：failed
- 运行模式：live / deepseek-chat
- 说明：唯一可用事实“支持字幕”单镜最短约1.5秒，无法压到1秒上限内，目标时长不可满足
- 预计总时长：1.5 秒

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
| 1 | search_materials | 先检索本地素材以获取产品事实与标题 | {"ok": true, "count": 1} |
| 2 | write_script | 已检索到产品事实，按简洁风格选取批准短句与画面 | {"ok": true} |
| 3 | estimate_duration | 先估算草稿时长是否超过1秒上限 | {"ok": true, "total_seconds": 9.1, "within_limit": false} |
| 4 | write_script | 总时长9.1秒超1秒上限，删减至仅保留事实镜头并压缩画面时长 | {"ok": true} |
| 5 | estimate_duration | 删减后需重新估算是否满足1秒上限 | {"ok": true, "total_seconds": 1.5, "within_limit": false} |
| 6 | fail | 删减后仍超限且无更短合规素材，无法满足1秒上限 | {"ok": true, "status": "failed"} |
