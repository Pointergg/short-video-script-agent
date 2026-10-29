# 评估与证据

## 当前验证状态

2026-10-29 本机实际执行 **DeepSeek `deepseek-chat` 真实模型评估**与离线评估。最终真实模型 10 个场景均满足各自的状态与行为断言；独立反馈探针 5/5。`examples/live/summary.json`、`feedback-probes.json` 和各场景 Trace 均为程序保存的实际结果。自然调用与受控测试清楚区分，不把夹具动作称为模型动作。

离线模式的 8 个输入/环境组合全部得到预期状态；单元测试实际结果见 `examples/test-results.txt`。这些比例只代表本轮有限测试的通过情况，不是模型准确率、长期成功率或真实创作者满意度。

## 真实模型实际结果

| 场景 | 起始方式 | 实际结果 | 证据 |
|---|---|---|---|
| 正常生成 | 模型从第一步决策 | 14.0 秒，逐镜规则通过，completed | [分镜与动作](../examples/live/normal/report.md) |
| 30 秒生成 | 模型从第一步决策 | 首稿 20.0 秒，未超限，无须改稿 | [Trace](../examples/live/over_duration/result.json) |
| 缺受众 | 模型从第一步决策 | request_info，无业务工具调用 | [Trace](../examples/live/missing_info/result.json) |
| 无素材 | 模型从第一步决策 | 两次空检索后请求补充 | [Trace](../examples/live/no_materials/result.json) |
| 工具失败 | 模型决策，工具注入真实错误返回 | 观察 SEARCH_UNAVAILABLE 后明确 fail | [Trace](../examples/live/tool_failure/result.json) |
| 1 秒不可满足 | 模型从第一步决策 | 9.1 → 1.5 秒仍超限，明确说明失败 | [分镜与动作](../examples/live/impossible_duration/report.md) |
| 检索改写恢复 | 先执行无命中查询夹具 | 模型改写后命中 P01，生成 15.0 秒脚本 | [Trace](../examples/live/query_rewrite/result.json) |
| 2 步上限 | 模型从第一步决策 | 返回 incomplete，不交付未检查草稿 | [Trace](../examples/live/step_limit/result.json) |
| 超时长修正 | 工具实际计算夹具首稿 31.0 秒 | 模型改成 11.1 秒，再估时、检查、finish | [分镜与动作](../examples/live/controlled_over_duration/report.md) |
| 无依据事实修正 | 工具实际拒绝夹具中的 80% | 模型删除虚构事实，重写、复查，11.6 秒 | [分镜与动作](../examples/live/controlled_rule_repair/report.md) |

同一份 31.0 秒草稿的单步探针：60 秒预算下模型选择 `check_rules`，30 秒预算下选择 `write_script`；空检索选择改写、不可恢复失败选择 fail、无依据事实选择重写。详见 [feedback-probes.json](../examples/live/feedback-probes.json)。探针只检验下一动作，完整修正能力由上表的完整运行另行验证。

受控场景中的首稿/首个查询是测试夹具，工具结果全部真实执行；后续动作由真实模型生成。自然路径中的首稿未超时，不能把该条记录包装成“模型主动修正了超时长”。

## 保留的失败与改进

- [第一轮](../examples/live/attempt-01/summary.json)：两条路径出现 MODEL_INVALID_RESPONSE；原始结果保留。初版只核对 status，使一次 API 失败也满足了“预期 failed”，属于评估缺陷。现已要求不可满足/工具失败场景必须由模型显式 fail，不能拿调用错误充数。
- [第二轮](../examples/live/attempt-02/summary.json)：9/10 行为断言通过。模糊主题下模型第一次选了有效检索词，因此没有触发预期的“先空再改写”；这不等于模型不会改写。最终将该用例改为已标注来源的无结果夹具，确定性触发实际反馈后再观察模型。
- 有限恢复：模型空响应、格式错误等连续重试最多一次，仍计入步数；失败记录不删除。业务动作调整仍由模型决定，传输重试不算 ReAct 证据。
- 当前结果仅为单次最终运行与五个探针，无统计显著性保证；额外成功运行不抵消历史失败。

## 离线实际输出

| 用例 | 预期与实际状态 | 观察到的关键行为 | 完整证据 |
|---|---|---|---|
| normal | completed | 60 秒上限，首稿 31.0 秒，直接进入规则检查 | [Trace](../examples/mock/normal/result.json) / [分镜](../examples/mock/normal/report.md) |
| over_duration | completed | 30 秒上限，31.0 → 25.3 秒；修改后重新估时和检查 | [Trace](../examples/mock/over_duration/result.json) / [分镜](../examples/mock/over_duration/report.md) |
| missing_info | needs_input | 缺受众，要求补充，无业务工具调用 | [Trace](../examples/mock/missing_info/result.json) |
| no_materials | needs_input | 两次实际检索均为 0，改写后要求资料 | [Trace](../examples/mock/no_materials/result.json) |
| tool_failure | failed | 故障注入返回 SEARCH_UNAVAILABLE，明确停止 | [Trace](../examples/mock/tool_failure/result.json) |
| impossible_duration | failed | 1 秒上限，修订到最小事实仍需 1.5 秒，说明无法满足 | [Trace](../examples/mock/impossible_duration/result.json) |
| query_rewrite | completed | 初次无结果，改用“产品”后命中 P01，继续生成 | [Trace](../examples/mock/query_rewrite/result.json) |
| step_limit | incomplete | 2 步耗尽，草稿不能当成交付 | [Trace](../examples/mock/step_limit/result.json) |

每个目录同时保存输入、材料快照和故障/上限参数。`result.json.trace` 包含实际步骤、工具参数、返回结果、简短动作依据；`checks.duration.scenes` 与 `checks.rules.scenes` 按镜头序号对应。事实片段含 `source_id`，文案白名单片段不伪挂来源。

## 反向验证

`tests/test_agent.py` 覆盖：虚构“效率提升80%”、P99 假来源、未检索的真实来源、借 neutral 注入功能、标题和画面夹带事实、草稿修改后检查失效、模型跳过检查结束、非法工具参数修正、规则失败后重新写稿复查、模型响应格式错误、非法时长和重复素材 ID。

反馈差异测试只改变目标时长：相同首稿在 60 秒预算后下一动作是 `check_rules`，30 秒预算后是 `write_script`。改变检索结果为空时，下一动作从生成变成改写查询/补充资料。这证明离线模拟器与主循环会处理不同观察；**不能据此推断真实模型也一定如此**。

## 真实模型验收步骤

1. 按 README 设置服务和密钥，运行 `python scripts/evaluate.py --provider live`，输出到独立 `examples/live/`，不要覆盖 mock。
2. 审查至少两条实际路径，核对模型是否观察实际工具结果、是否请求相应工具、是否重新检查最新草稿。
3. live 正常首稿可能本来就短，不能为凑修正证据伪造估时。使用 `scripts/probe_model.py` 的受控反馈实验，向模型提供**实际工具计算**的 31 秒草稿记录，比较 60 秒与 30 秒预算下的下一步动作。
4. 汇总真实通过/失败，不删除不利结果，不把 `status=completed` 单独当成所有创作要求均已人工确认。以 `provider=live`、实际动作链和工具结果共同作为证据。

## 限制与未完成

已实际验证本次 DeepSeek 接口与上述有限场景；未验证其他供应商、中文旁白真实语速、平台适配质量、创作吸引力、开放域事实蕴含及材料真实性。Mock 使用重复铺垫以稳定制造超时输入，不能用于评价文案质量。CI 执行 Python 3.11–3.13 离线检查，最新结果以 GitHub Actions 为准。
