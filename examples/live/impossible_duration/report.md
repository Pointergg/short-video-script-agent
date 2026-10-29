# 短视频脚本运行报告

- 状态：failed
- 运行模式：live / deepseek-chat
- 说明：目标时长1秒低于单镜头最低估算时长1.5秒（含0.5秒镜头基础时长），无法在保留任何事实或旁白的情况下满足时长上限。
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

| 步骤 | 动作来源 | 动作 | 简要依据 | 结果 |
|---|---|---|---|---|
| 1 | model | search_materials | 先检索产品素材以获取可引用事实 | {"ok": true, "count": 1} |
| 2 | model | write_script | 已检索到产品事实，按简洁风格用批准短句与画面组稿 | {"ok": true} |
| 3 | model | estimate_duration | 先估算草稿时长是否超过1秒上限 | {"ok": true, "total_seconds": 9.1, "within_limit": false} |
| 4 | model | write_script | 总时长9.1秒超1秒上限，删减至仅保留事实镜头并重新估算 | {"ok": true} |
| 5 | model | estimate_duration | 删减为单镜头后重新估算时长是否在1秒上限内 | {"ok": true, "total_seconds": 1.5, "within_limit": false} |
| 6 | model | fail | 单镜头最短估算1.5秒已超1秒上限，删减无法解决，属不可满足约束。 | {"ok": true, "status": "failed"} |
