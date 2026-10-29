# 短视频脚本运行报告

- 状态：completed
- 运行模式：live / deepseek-chat
- 说明：脚本通过当前素材、品牌规则与估算时长检查。
- 预计总时长：11.1 秒

## 可编辑脚本

本报告含受控测试：标注 test_fixture 的起始动作由测试程序执行，其后动作由 provider 决策。

标题：字幕助手

| 镜头 | 画面 | 旁白 / 字幕 | 起止秒 | 来源 | 规则 |
|---|---|---|---|---|---|
| 1 | 产品名称卡片 | 今天，聊聊字幕。你的视频，需要字幕吗？把注意力放在表达上。 | 0–7.8 | 创意白名单 | 通过 |
| 2 | 字幕功能文字卡片 | 支持字幕 | 7.8–9.3 | P01 | 通过 |
| 3 | 结尾文字卡片 | 一起看看。 | 9.3–11.1 | 创意白名单 | 通过 |

## 补充信息


## 风险

- 时长为文本启发式估算，未使用真实配音测量。
- 创意范围受已批准文案和画面白名单限制；任意语义改写需另行人工审核。
- 尚未进行真实平台政策、法律合规或最终视频审核。

## 动作记录

| 步骤 | 动作来源 | 动作 | 简要依据 | 结果 |
|---|---|---|---|---|
| 1 | test_fixture | search_materials | 受控测试夹具执行，非模型选择 | {"ok": true, "count": 1} |
| 2 | test_fixture | write_script | 受控测试夹具执行，非模型选择 | {"ok": true} |
| 3 | test_fixture | estimate_duration | 受控测试夹具执行，非模型选择 | {"ok": true, "total_seconds": 31.0, "within_limit": false} |
| 4 | model | write_script | 原草稿31秒超限且旁白重复，删减为3镜并保留唯一事实引用 | {"ok": true} |
| 5 | model | estimate_duration | 删减后需重新估算时长，确认是否在30秒上限内 | {"ok": true, "total_seconds": 11.1, "within_limit": true} |
| 6 | model | check_rules | 时长已符合上限，需核验事实引用与品牌规则后才能完成 | {"ok": true, "passed": true, "issues": []} |
| 7 | model | finish | 最新草稿时长11.1秒未超30秒上限，规则核验通过，可完成 | {"ok": true, "status": "completed"} |
