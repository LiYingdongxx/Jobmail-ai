# JobMail AI V2 - Agent + RAG 升级方案

文档类型：Roadmap / 面试复习材料  
状态：规划中，尚未作为已完成能力写入简历  

## 1. 当前 V1 是什么

JobMail AI V1 是一个面向实习和校招场景的求职邮件处理原型，当前采用规则版 workflow 实现：

```text
招聘邮件输入
-> 邮件分类
-> 关键信息提取
-> 岗位标准化
-> deadline 结构化
-> 行动建议
-> 回复草稿
-> 用户人工确认
```

V1 已实现的核心能力包括：

- 邮件分类：`interview`、`materials`、`follow_up`、`offer`、`rejection`、`spam`
- 信息提取：日期、时间、联系方式、待办事项、岗位、deadline
- deadline 结构化：`deadline_raw`、`deadline_iso`、`deadline_status`、`deadline_hours_left`
- 行动建议：基于邮件类型和 deadline 紧急度生成下一步建议
- 回复草稿：基于模板生成面试确认、材料补交、Offer 沟通等回复
- 评估机制：使用 strict / loose 指标评估分类、岗位和 deadline 提取效果

V1 的核心价值是先验证求职邮件处理流程是否成立，而不是一开始追求复杂模型能力。

## 2. 为什么要升级到 V2

V1 的优点是可解释、可运行、便于评估，但也存在局限：

- 固定流程较强，每封邮件基本走同一套处理链路
- 规则和正则对非常规表达的泛化能力有限
- 回复草稿主要依赖固定模板，个性化和上下文适配不足
- 没有接入外部知识，例如岗位 JD、学校实习规则、求职沟通规范
- 只能处理单封邮件，缺少对用户求职进度的持续跟踪

V2 的目标是引入 Agent、RAG 和 Memory，把 JobMail AI 从“规则演示工具”升级为“可扩展的 AI 求职邮件助手架构”。

## 3. V2 总体架构

V2 采用以下架构：

```text
用户输入招聘邮件
-> Agent 判断任务目标
-> 调用邮件分类工具
-> 调用信息抽取工具
-> 调用 deadline 解析工具
-> RAG 检索相关知识
-> 调用回复生成工具
-> Memory 更新求职进度
-> 输出结构化结果
-> 用户人工确认
```

核心思想是：

- Agent 负责调度流程
- Tool 负责稳定执行具体任务
- RAG 负责补充外部知识
- Memory 负责记录用户历史和求职进度
- Human-in-the-loop 负责最终确认和风险控制

## 4. Agent 负责什么

V2 中的 Agent 不直接完成所有任务，而是作为调度器，根据邮件内容和上下文选择合适工具。

可拆分的工具包括：

```text
classify_email_tool
extract_info_tool
deadline_parser_tool
action_suggestion_tool
reply_generator_tool
evaluation_tool
```

示例 ReAct 流程：

```text
用户输入邮件
-> Thought: 这是一封招聘邮件，需要先判断类型
-> Action: classify_email_tool[email]
-> Observation: interview
-> Thought: 面试邮件需要提取面试时间、方式、deadline 和待办
-> Action: extract_info_tool[email]
-> Observation: position、date、time、deadline、todos
-> Thought: 需要结合面试邮件模板生成回复草稿
-> Action: rag_search_tool["interview confirmation email template"]
-> Observation: 相关模板和沟通规范
-> Action: reply_generator_tool[email + extracted_info + retrieved_context]
-> Observation: 回复草稿
-> Action: Finish[分类结果 + 关键信息 + 行动建议 + 回复草稿]
```

Agent 的价值在于：

- 可以根据邮件类型动态决定下一步，而不是所有邮件固定走同一条路径
- 可以在缺少信息时继续调用工具或提示人工确认
- 可以把复杂任务拆解成多个可解释步骤

## 5. RAG 负责什么

RAG 的作用是让系统在生成建议和回复前先检索相关资料，而不是只依赖模型自身知识或固定模板。

可接入的知识库包括：

- 求职邮件回复模板
- 面试确认邮件模板
- 材料补交回复模板
- Offer 沟通模板
- 学校实习 / STEM 项目申请规则
- 公司岗位 JD
- 常见 HR 沟通话术
- 用户自己的简历项目材料

RAG 流程：

```text
文档
-> 清洗 / 解析
-> 切分成 chunks
-> embedding 向量化
-> 存入知识库
-> 用户邮件触发查询
-> 检索相关 chunks
-> 把 chunks 作为 context 给 LLM
-> LLM 基于 context 生成回复和建议
```

在 JobMail AI 中，RAG 可以用于：

- 让回复草稿更贴近真实求职沟通规范
- 根据岗位 JD 生成更有针对性的回复
- 根据学校实习规则提醒用户注意事项
- 在输出中保留参考来源，提升可解释性

## 6. Memory 负责什么

Memory 用于记录用户自身和任务历史，而不是存储通用知识。

JobMail AI 中适合存入 Memory 的内容包括：

- 用户目标岗位方向，例如 AI Product / Data Analytics / Applied AI
- 用户不偏好的方向，例如硬核算法岗
- 已投递公司和岗位
- 每家公司当前进度
- 已处理过的邮件
- 已确认的 deadline
- 已提交的材料

示例：

```text
用户已投递：Ricoh Project Assistant
当前状态：等待回复
用户偏好：AI 产品 / AI 项目 / 数据分析
风险偏好：不希望系统自动发送邮件
```

Memory 的价值在于：

- 支持跨邮件、跨公司跟踪求职进度
- 减少用户重复输入背景信息
- 让行动建议更个性化
- 支持后续生成求职进度看板

Memory 和 RAG 的区别：

| 能力 | 主要记录对象 | 示例 |
|---|---|---|
| Memory | 用户历史和偏好 | 用户想找 AI 产品实习，不喜欢硬核算法 |
| RAG | 外部资料和知识库 | 岗位 JD、邮件模板、学校规则 |

## 7. 用户如何确认

求职邮件属于高风险沟通场景，因此 V2 仍然坚持：

```text
AI suggestion + human confirmation
```

系统不自动发送邮件，只生成：

- 邮件分类结果
- 关键信息提取结果
- deadline 状态
- 行动建议
- 回复草稿
- 需要人工确认的风险提示

用户需要确认：

- 邮件类型是否正确
- deadline 是否准确
- 回复草稿是否符合真实情况
- 是否需要补充附件或修改措辞
- 是否执行发送或归档动作

对于以下情况，系统应强制提示人工复核：

- `deadline_status = unknown`
- `position = 未知岗位`
- 回复涉及 Offer、薪资、入职时间
- 邮件类型置信度较低
- RAG 检索不到可靠参考资料

## 8. 风险与边界

V2 的主要风险包括：

- Agent 可能选择错误工具或过早 Finish
- RAG 可能检索到不相关或过期内容
- LLM 可能生成不符合事实的回复草稿
- Memory 可能记录错误或过期的求职状态
- 求职邮件中包含隐私信息，长期存储有风险
- 自动化程度过高可能影响正式求职沟通

产品边界：

- 不自动发信
- 不自动承诺面试时间、入职时间或薪资条件
- 不保存敏感信息，除非用户明确确认
- 对低置信度结果进行提示
- 允许用户查看、修改和删除 Memory

## 9. V2 评估指标

V2 除了保留 V1 指标，还需要增加 Agent、RAG 和回复质量相关指标。

V1 保留指标：

- `classification_acc_strict`
- `position_acc_strict / loose`
- `deadline_acc_strict / loose`
- `full_match_acc_strict / loose`

Agent 相关指标：

- `tool_selection_acc`：工具选择是否正确
- `task_completion_rate`：是否在限定步数内完成任务
- `invalid_action_rate`：模型输出无法解析 Action 的比例
- `early_finish_rate`：过早 Finish 的比例

RAG 相关指标：

- `retrieval_relevance`：检索结果是否和邮件场景相关
- `context_precision`：提供给 LLM 的 context 是否有效
- `source_coverage`：回复是否覆盖必要参考信息

回复质量指标：

- `reply_usefulness`：回复是否可直接编辑使用
- `reply_safety`：是否避免过度承诺和事实错误
- `human_edit_rate`：用户需要修改回复的比例

产品指标：

- 邮件处理时间节省
- deadline 遗漏率降低
- 用户确认率
- 用户手动修改率

## 10. 最小可行 V2 Demo

不建议一开始做完整 V2。更合理的最小 Demo 是：

```text
1. 把 classify_email、extract_info、generate_reply 包装成工具
2. 写一个简单 Agent 按固定 Action Map 调用工具
3. 准备一个小型 RAG 知识库，只包含 3 类邮件模板
4. 对 5-10 封邮件跑通 Agent + RAG 流程
5. 输出结构化结果和回复草稿
```

最小知识库：

```text
interview_reply_template.md
materials_reply_template.md
offer_reply_template.md
```

最小验收标准：

- 能根据邮件类型选择正确工具
- 能检索到对应邮件模板
- 能生成比 V1 更贴合场景的回复草稿
- 不自动发送邮件
- 用户可以看到检索来源和原始字段

## 11. 面试表达版本

如果面试官问“这个项目后续怎么优化”，可以这样回答：

```text
当前 JobMail AI V1 是规则版 workflow，重点验证求职邮件处理流程，包括分类、信息抽取、deadline 结构化、行动建议和回复草稿。后续我会考虑升级为 Agent + RAG 架构。

Agent 负责根据邮件类型动态调用不同工具，例如邮件分类、信息抽取、deadline 解析和回复生成。RAG 负责从求职邮件模板、岗位 JD 和学校实习规则中检索相关资料，让回复草稿更贴近真实场景。Memory 可以记录用户投递过的公司、岗位偏好和邮件处理状态，从单封邮件处理升级到整个求职流程管理。

但求职邮件属于高风险沟通场景，所以系统不会自动发送邮件，所有建议和回复草稿都需要用户人工确认。
```

## 12. 当前状态说明

本方案是 V2 Roadmap，不代表当前仓库已经实现 Agent + RAG。

当前已实现版本仍为 V1：

- 规则版邮件分类
- 规则/正则信息抽取
- deadline 结构化
- 模板回复草稿
- strict / loose 评估脚本

V2 适合作为后续学习方向、面试讨论材料和下一阶段开发计划。
