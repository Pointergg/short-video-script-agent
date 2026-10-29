# 评估与证据

## 当前验证状态

2026-10-29 本机实际执行离线评估。`examples/mock/summary.json` 是一键脚本生成的结果，不是手写日志。当前**未提交真实模型运行结果**：尚未配置可用 API Key。因此不能声称已完成真实模型 ReAct 决策验收。标准库 HTTP provider 的存在不等于模型调用验证通过。

离线模式的 8 个输入/环境组合全部得到预期状态；测试结果见 `examples/test-results.txt`。这些比例只代表固定测试的通过情况，不是模型准确率或真实创作者满意度。

## 实际输出

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

尚未验证真实模型输出、API 供应商兼容性、中文旁白真实语速、平台适配质量、创作吸引力、开放域事实蕴含及材料真实性。Mock 使用重复铺垫以稳定制造超时输入，不能用于评价文案质量。CI 配置已提供，远端是否成功以 GitHub Actions 实际结果为准。
