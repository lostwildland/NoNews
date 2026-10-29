# AI 服务、模型与可复用提示词：交互方案调研

调研日期：**2026-10-25（Asia/Shanghai）**。用于设计讨论，**不构成 ADR 决定**。只读公开官方文档、公开源码和本仓库研究／ADR；没有安装或启动应用、登录账号、读取凭据、执行推理或修改应用代码。没有使用浏览器自动化，因此没有启动 preview。

## 结论先行

**建议首版把具名提示词与模型完全分开：两份角色模型设置（Curator、Editor），提示词不保存模型，也不提供模型覆盖。** Feed 仍独立组合两份提示词、自动开关和阈值。选择提示词时直接显示“本次将使用 Curator 模型 …”，让用户看清组合，无需再维护一层例外。

这与先前“角色默认＋提示词可选覆盖”不同。覆盖能照顾例外，但每份共享提示词会变成潜在路由规则；换服务时用户必须找出哪些仍继承、哪些已固定。当前已确认需求证明了“多份可复用指令”和“两种角色”，**尚未证明每份指令必须独立选模型**。先不要把未证明的例外做成永久配置层。

这只是当前约束下最小且可解释的选择，不是认定所有 prompt 都可跨模型等质工作。如果后续确有“同一角色的两份 prompt 必须长期使用不同模型”，应重新比较独立的执行方案（见方案 C），而不是立即堆叠全局／角色／prompt／feed 多级覆盖。

产品事实也没有支持唯一行业标准：Raycast 接近“命令固定模型”，LM Studio 的推理预设与模型加载默认分离，Open WebUI 同时提供独立 prompts 和模型包装，LibreChat Agents 又支持引用独立版本化 prompt。**功能存在不是 UX 优秀的证明**；本次没有可用性测试、转化数据或安装体验，不能据这些产品声称某案已被验证最好。

## 已确定的产品边界

依据 [ADR 0004](../adr/0004-reusable-prompts-and-feed-processing-policy.md)、[ADR 0005](../adr/0005-user-connected-ai-services-including-magpie.md)：Curator／Editor 提示词分别具名、跨来源复用、复制修改；Feed 保存组合和自动处理策略，支持批量；不强制 Kit。首版自定义 prompt，不做自然语言 onboarding 或 prompt 试运行。改配置不自动重跑历史，显式重跑须预览且保留旧结果。系统维护输出结构与校验。BYO 服务，支持 Magpie，不要求所有用户安装 Magpie，不由产品代付推理。上游兼容不约束本次 UX 选择。

## 证据与版本边界

| 产品 | 本次证据 | 可确认的状态 |
| --- | --- | --- |
| Raycast | 当前官方 Manual；闭源客户端没有取得源码 SHA | **官方文档描述**，未固定客户端版本、未运行验收 |
| LM Studio | 当前官方 Docs；preset 文档注明导入／分享从 0.3.15 提供 | **官方文档描述**，0.3.15 是该功能历史门槛，不是本次最新版本声明；未取得闭源应用 SHA |
| Open WebUI | GitHub release `v0.12.4`，SHA `33c1978d5bad52a31df75ea55143025dfad18d16`；当前官方 Docs | **发布标签源码**核验对象关系；滚动文档的其他功能不能全归到此 release |
| LibreChat | `main` SHA `a378657583567310c841d652b0f6b00c83e2bd6b`；官网标 `Latest (dev)` | **开发源码／开发文档**；`releases/latest` 返回 404，未建立 release 对应关系，不称已发布 |
| Folo | release `desktop/v1.16.0`，SHA `b5596042964b9e0eb41d1e1b4947cbbdd471faf2`，2026-10-16 发布；复核 shortcut 类型和编辑器 | **发布标签源码**；其余既有结论引用本仓库前次报告，未重复全量审计 |

公开元数据入口：[Open WebUI release](https://github.com/open-webui/open-webui/releases/tag/v0.12.4)、[LibreChat 固定提交](https://github.com/LibreChat-AI/LibreChat/commit/a378657583567310c841d652b0f6b00c83e2bd6b)、[Folo release](https://github.com/RSSNext/Folo/releases/tag/desktop/v1.16.0)。源码读取使用 raw.githubusercontent.com，引用用同 SHA 永久链接。以下产品入口均由文档／代码还原，**不是本次实际点击记录**。

## 五个产品：什么与什么绑定

### 1. Raycast AI Commands：以执行命令为中心

**路径**：Root Search → Create AI Command；编辑已有命令从 Search AI Commands → Edit。命名、prompt、model、creativity 属于同一命令；可复制、分享链接、JSON 导入。AI Commands 模型设置独立于 Quick AI／AI Chat。官方说明：Custom AI Commands 默认不会更新已有显式模型；每个命令保存自己的模型，目前没有单命令“use default”入口。它实际更像创建／编辑时确定的绑定，不能只看到“default”一词就推定持续继承。[AI Commands 官方手册](https://manual.raycast.com/ai/ai-commands)

**连接归属**：Settings → AI → Models & Providers → Custom Providers → Reveal Providers Config，配置 provider 的 URL、key、模型列表及能力。模型按 provider 分组进入选择器；非法 YAML 会显示错误并保持此前已加载模型。能力声明包括 system message、vision、tools 等；官方明确兼容 API 不等于保证所有 provider 可用。该文件包含用户密钥，分享命令不应被等同于迁移服务凭据。[Custom Providers 官方手册](https://manual.raycast.com/ai/custom-providers)

**对本项目的启发（推论）**：固定命令有直接、稳定的运行配方，但已有 20 个命令时改默认不会统一迁移。对于每天自动处理很多来源，重复配置和遗忘旧服务的代价比一次快捷操作更大。离线本地模型也不等于全部工具离线：Raycast 文档把某些云工具步骤另外计费；应明确每个阶段实际走哪个服务。[Local Models 官方手册](https://manual.raycast.com/ai/local-models)

**未核验**：导入命令的模型在接收方不存在时的精确 UI；云服务离线时命令是否自动回退。不能把配置解析错误的保留策略扩大为推理失败策略。

### 2. LM Studio：模型选择与指令／推理 preset 可分开

**路径**：聊天 Advanced Configuration → Preset 管理；保存具名 system prompt＋推理参数，可无 system prompt。Preset JSON 可从文件／URL 导入、分享并发布到 Hub；新版格式不包括加载参数。它证明“复用指令与生成设置”并不必须等同于“固定某个模型”；没有据此声称预设能在任意模型上产生相同质量。[Config Presets](https://lmstudio.ai/docs/app/presets)

**另一个默认**：My Models → 齿轮 → 模型默认加载参数，影响下一次加载，包括通过 `lms load`。这是 GPU／上下文等加载设置，不是“默认聊天模型”，也不是当前所有会话会即时变更。[Per-model Defaults](https://lmstudio.ai/docs/app/advanced/per-model)

**连接归属**：已下载本地模型可离线聊天和运行本地推理服务器，不依赖云端 API key；模型／runtime 下载另需网络。不能把本地 preset 文件和模型权重当作同一迁移包。[Offline Operation](https://lmstudio.ai/docs/app/offline)

**对本项目的启发（推论）**：指令复用与执行环境有不同生命周期，分开对象合理；但 LM Studio 的主动聊天会在运行前面对模型选择器，NoNews 后台任务不具备这个纠错时机。

**未核验**：切换 preset 后未保存变更的处理、跨模型不支持参数的精确错误行为、云端凭据迁移；不把文档中的 local 能力推断为整个产品仅支持 local。

### 3. Open WebUI：两条复用路径同时存在

**A. Workspace → Prompts → Create**：具名内容与 slash command，在聊天中调用；当前文档提供版本历史及分享权限。**B. Workspace → Models → Create**：选择 Base Model，配 system prompt、参数及可选工具／知识，成为模型选择器中的包装。两者不是同一对象；发布源码 `PromptForm` 的内容字段与 `ModelForm.base_model_id`、params、meta 分立。[Prompts 文档](https://docs.openwebui.com/features/workspace/prompts/)、[Models 文档](https://docs.openwebui.com/features/workspace/models/)、[固定 Prompt 源码](https://github.com/open-webui/open-webui/blob/33c1978d5bad52a31df75ea55143025dfad18d16/backend/open_webui/models/prompts.py#L83)、[固定 Model 源码](https://github.com/open-webui/open-webui/blob/33c1978d5bad52a31df75ea55143025dfad18d16/backend/open_webui/models/models.py#L242)

**连接与默认**：管理连接从 Settings → Admin → Connections；个人 Direct Connections 另由管理员启用，key 留浏览器 local storage，推理直达 provider。该个人路径仍不保证后台步骤走同一连接。模型包装迁移需重新指向 base model，分享包装不是给接收者授权底层模型；当前文档明确检查双方访问权限。[连接文档](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/)、[Direct Connections（实验性）](https://docs.openwebui.com/features/chat-conversations/direct-connections/)、[Models 文档](https://docs.openwebui.com/features/workspace/models/)

**故障证据**：官方排错文档说明不可达连接会拖延模型列表，并举出 DNS 问题可表现为 model not found。这说明“模型无效”提示未必能正确定位到模型设置，需区分连接失败与标识不存在。[Connection Errors](https://docs.openwebui.com/troubleshooting/connection-error/)

**对本项目的启发（推论）**：可以分离指令复用与运行配方，但 Open WebUI 的双体系、全局／个人／模型多层参数并非本项目必须复制的成熟度标志。NoNews 首版不需要把“模型”同时拿来称真实模型、角色包装、工具集合。

### 4. LibreChat：旧 Presets 已弃用，Agent 可引用独立 prompt

**不要把旧教程当当前方向**：Presets 页明确 deprecated，指向 Agents。旧 preset 的确绑定 endpoint、model、instructions、参数，支持 JSON 导入导出，默认应用于新会话；它只能作为历史方案，不能当当前首推设计。[Presets 官方文档](https://www.librechat.ai/docs/user_guides/presets)

**当前开发文档路径**：endpoint 选 Agents → Side Panel → Agent Builder。Agent 有 name、instructions、provider/model；Instructions source 可在 Inline 与 Prompt 间切换，后者引用独立 prompt 并选择 Production 或固定版本。Agent 自身也有配置历史；识别到 model-not-found／rate-limit 会给本地化引导。固定开发源码有 provider、model、instructionsPrompt，支持上述概念关系，但没有建立客户端 release 验收。[Agents 开发文档](https://www.librechat.ai/docs/features/agents)、[固定 Agent schema](https://github.com/LibreChat-AI/LibreChat/blob/a378657583567310c841d652b0f6b00c83e2bd6b/packages/data-schemas/src/schema/agent.ts#L11)

**凭据与后台**：用户可在 endpoint 齿轮或 Settings → Data & Privacy → API keys 输入 key；部署也能配置服务器共享 key。因此“分享 Agent”不应当等于分享 key。Scheduled Chats 选已保存 Agent＋任务 prompt＋schedule，官方标实验性、默认关闭，并提供失败状态与重复失败停用；这是把自动运行做成独立执行语义的参考，不是生产可靠性证明。[Your First Chat](https://www.librechat.ai/docs/quick_start/first_chat)、[Scheduled Chats](https://www.librechat.ai/docs/features/scheduled_chats)

**对本项目的启发（推论）**：第三个可复用对象“运行方案”可引用 prompt，而不用把 model 塞进 prompt 文本对象。但它比两份角色默认多一个必须命名／维护的概念，不能仅因 Agent 产品流行就要求 RSS 用户创建 Agent。

**未核验**：Agent 导出是否包含关联 prompt 版本、导入缺服务／缺权限的准确恢复 UI、每次运行具体采用哪个保存时刻的 Agent 配置。

### 5. Folo：轻量 Shortcut 独立于模型绑定

本次复核 release 的 `AIShortcut`：id、name、prompt、defaultPrompt、enabled、icon、hotkey、displayTargets；类型中没有 model/provider。编辑器保存相同字段。**路径**：Settings → AI → Shortcuts → 新建／编辑；阅读或列表中调用。它是轻量具名指令对象的直接参考，但**类型无模型字段只证明此对象不持有绑定，不能证明整个请求链没有默认模型或其他模型选择**。[固定接口](https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/packages/internal/shared/src/settings/interface.ts#L181)、[固定编辑器](https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/settings/tabs/ai/shortcuts/ShortcutModalContent.tsx#L103)

已有 [Folo 产品参考](folo-product-reference.md) 区分了 Personalization、Shortcuts、Tasks、Actions 与 MCP 连接模板；本次不重做该盘点。不把 MCP key 误认成 BYO LLM key，也没有证明 Folo 的模型供应、离线失败、prompt 分享迁移及自动任务采用哪种完整路由。Folo 对本题的价值是展示 prompt 可以保持轻量，而不是证明它已解决 NoNews 的自动处理配置。

## 跨产品比较：可借鉴与未知

| 问题 | 已有一手证据 | 对 NoNews 的含义（设计推论） |
| --- | --- | --- |
| 凭据放哪里 | Raycast provider 配置；Open WebUI 服务器连接／个人浏览器连接；LibreChat 用户 key／部署 key；LM Studio 本地模型无需云 key | 连接对象持有凭据引用，prompt 及 Feed 不重复保存 key；导出 prompt 不带密钥 |
| 选模型的层级 | Raycast 命令；LM Studio 聊天选择与 preset 分离；Open WebUI base-model wrapper；LibreChat Agent | “行业都有 preset”不足以决定绑定；先选最适合后台自动运行的最小层级 |
| 改默认影响什么 | Raycast 明确不改已有命令；LM Studio load defaults 影响下次加载；LibreChat 旧默认 preset 只影响新会话 | 必须把影响写成具体对象与生效时点，不能只写“已保存默认” |
| 不存在／离线 | LibreChat model-not-found 引导；Open WebUI 不可达可能伪装为模型不存在 | 分开显示连接不可达、凭据失效、target 不存在、输出不合格；不要把失败变成低分 |
| 能力不兼容 | Raycast 能力声明；Open WebUI 基础模型和权限依赖；其他产品路径未验 | 选择器只能提示已知能力，不保证输出符合合同；运行仍要校验 |
| 分享迁移 | Raycast command 分享；LM Studio preset JSON；Open WebUI 对象访问控制；LibreChat 旧 preset JSON | 分享指令、分享执行方案和迁移连接应分开；缺模型需映射，不默认换成云模型 |
| 聊天与后台 | 聊天可随时改模型；LibreChat scheduled 有独立状态／失败停用，且属实验 | 后台不能等人回来看选择器；配置需在执行前解析并留记录，故障有明确恢复入口 |

没有声称任何产品的默认改动会自动重跑历史；也没有证据证明它们的会话／preset 更新合同适合 RSS 队列。

## 三个真正不同的方案

以下是本项目候选设计，不是上述产品功能声明。共同底座都是“连接 = URL／认证／能力目录；执行目标 = 该连接上的模型或网关 target；提示词 = 具名、角色化、版本化指令”。

### A. 完全分离：角色选择执行目标，提示词只写指令（推荐首版）

Settings → AI Services 添加连接；Settings → Processing 分别选 Curator 和 Editor 的执行目标。Prompt 编辑器不出现模型选项。Feed → Processing 仍选两份提示词、阈值和自动开关，并在每行旁只读显示实际角色目标。

例：“论文价值”与“产业跟踪”都是 Curator prompt，均使用 `Magpie / curate`；“论文深读”和“新闻短稿”均使用 Editor 的 `Magpie / edit`。改 Editor 目标只改一处，所有后续 Editor 任务都变；不影响 Curator、不重跑历史。换到直连服务也无需编辑四份 prompt。

**优势**：模型设置只有两处；不存在隐藏覆盖；复制 prompt 不意外复制旧供应商。**限制**：某篇长文与新闻短稿无法分别固定便宜／长上下文模型；如果必须靠不同模型才能满足同一角色，A 不足。

### B. 绑定配方：每份具名提示词必须选择执行目标

Prompt 编辑器同时选择连接／模型，Feed 继续只选 prompt。“论文深读”绑定模型 X，“新闻短稿”绑定模型 Y。服务模型在 prompt 中始终显式固定，创建默认最多是表单初始值；**没有持续继承，也不叫可选覆盖**。

例：四份 Editor prompt 都固定旧服务，改全局创建默认不会改变它们；换服务必须提供“替换所有引用该目标的提示词”及影响预览，否则会留下旧路由。分享 prompt 时携带逻辑目标说明但不带凭据，接收方需映射。

**优势**：指令作者直接控制其运行配方，容易说明“这一份就是这样跑”。**限制**：把语义复用和供应商生命周期耦合；同样指令换模型时可能需要复制，prompt 库出现“深读-X／深读-Y”。该重复不能靠把模型字段藏进高级设置消除。

### C. 独立执行方案：prompt 与目标都可复用，另存组合

Prompt 不带模型；另建“处理方案”，各角色独立引用一份 prompt＋一个执行目标；Feed 各选 Curator／Editor 方案。两个角色方案仍可自由组合，**不恢复强制 Kit**。

例：同一“论文深读”prompt 被“深读·本地”和“深读·云端长文”两个 Editor 方案引用，Feed 决定用哪一个。更新 prompt 可影响两者；换服务只需改方案，prompt 不动。

**优势**：清楚区分指令、执行环境与来源策略；模型异质性确实存在时无需复制 prompt；可固定版本并追溯。**限制**：新增方案命名、列表与引用管理，Feed 不再直接选 prompt，用户要理解一层间接关系。这是能力扩展方案，不是首版免费午餐。

### 评估矩阵

评估对象为“2 个角色、10 份 prompt、30 个 Feed、需批量换一次服务”的假定任务；属于设计判断，未经用户实验。低／高不是产品实测分数。

| 维度 | A 完全分离 | B prompt 固定绑定 | C 独立执行方案 |
| --- | --- | --- | --- |
| 概念负担 | 最低：连接、两角色、prompt | 中：prompt 同时是配方 | 最高：另有运行方案 |
| 重复配置 | 最少，模型两处 | 多份 prompt 重复模型 | 同组合可复用，需维护方案 |
| 透明性 | 角色目标可见即清楚 | 每份 prompt 显式模型，清楚 | 展开组合可清楚，入口更深 |
| 可预测性 | 后续同角色统一变动；影响面大但单一 | 每份固定；默认不会暗改 | 方案引用与版本需说明 |
| 批量换服务 | 改两处，最简单 | 需批量替换引用，否则遗漏 | 改相关方案，复杂度居中 |
| 可追溯性 | 留执行快照后足够 | 留 prompt＋target 快照后足够 | 方案版本更完整，但仍需快照 |
| 同角色多模型 | 不支持 | 支持 | 支持且不复制指令 |

**为什么不把“角色默认＋prompt 可选覆盖”列为第四个首选？** 它属于 A/B 混合：没有固定模型的 prompt 跟着角色变，固定模型的保持不动。用户看见相同 prompt 列表，却要记住两种生效规则；换服务还得清点例外。它并非错误：当只有少数稳定例外、使用点始终显示“继承／固定”、且用户实测理解时可以成立；目前没有证据证明这笔复杂度值得首版承担。

## Magpie：目标不是实际模型

本仓库 [IO 能力盘点 C6](information-os-capability-inventory.md) 已记录：请求 Magpie target，与实际 provider/model、reported model 分开；供应商凭据与 fallback 在外部网关。本次未读取 Magpie 私人配置、未查询实际目录或调用服务，因此不新增协议细节或宣称 live 兼容。

建议选择器采用“连接名 / 目标名”，例如 `我的 Magpie / curate`。**`curate` 是逻辑目标，不应当伪装成真实模型名称**。直连示例 `我的服务 / model-id` 则是 provider 模型标识。可以统一显示为“执行目标”，用一行说明区分“网关决定实际模型”与“直连指定模型”，无需用户学内部路由术语。

记录至少分别保存：请求连接与目标、配置／prompt 版本、请求开始时刻；响应如可提供，另存实际 provider/model 和 reported model。缺信息显示“网关未提供”，不得从 target 名推断。Magpie 在 NoNews 之外改了映射，即使 NoNews 配置未变，实际模型也可能变；三种方案都无法仅靠 prompt 绑定消除这一点。

连接目录刷新成功只证明目录可读，不证明付费推理可用或模型满足输出格式。首版已排除 prompt 试运行，不应偷加自动收费“健康检查”；允许只读目录验证，首次正式处理仍可能失败。

## 推荐首版的具体可见行为

这是建议验收合同，未获确认，不改 ADR。

1. **设置只维护两个角色目标。** 如只接一项服务，两角色可以选同一目标。Feed 和 prompt 都不提供模型覆盖。Feed 预览同时列出“Curator：论文价值 → 我的 Magpie / curate；Editor：论文深读 → 我的 Magpie / edit”。
2. **保存改动前显示影响。** 例如“Editor 将从 A 换到 B，影响 23 个已启用来源之后创建的 Editor 任务；历史结果不变”。数量来自真实引用关系，不能把所有 Feed 都计成自动运行。Curator 失败不记为 0 分、不自动进入 Editor。
3. **运行配置在任务创建时快照。** 建议排队任务继续用创建时快照；运行中不改。Curator 达标后才创建的 Editor 子任务采用当时的 Editor 配置并记录。修改设置时明示现有排队任务不变；如需替换，使用明确取消／重排入口。此项填补 ADR 已注明的未决队列边界，不声称已有决定。
4. **错误不静默换服务。** 无效 target、401、离线、能力不足或非法输出分别可见；受影响角色任务暂停／失败可重试，普通阅读仍可用。不得因一个服务离线就换到另一付费服务或降低评分合同。网关自身 fallback 另按其返回信息记录。
5. **删除连接前列出引用并提供替换。** 不清空 prompt 内容，不把失效连接 silently 改为全局第一个模型；分享 prompt 只携带指令与角色／版本，接收方使用自己的角色目标。若日后导出完整处理设置，另做目标映射。

## 可观察的验证标准与升级触发

先用静态原型和任务访谈验证，不需要安装参考产品、收费推理或 prompt 试运行。下面的次数／比例是**建议门槛**，不是现有研究结果。

| 任务 | 观察指标／拟定通过标准 |
| --- | --- |
| 给 3 个 Feed 配两份已有 prompt | 用户无需复制 prompt 或理解 Agent／Kit；能指认每个角色用哪个目标 |
| 把所有 Editor 换服务 | 只修改 1 个角色设置；保存前能正确说明受影响来源、历史和排队任务范围 |
| 复制“论文深读”并改写作风格 | 模型不随复制产生隐藏副本；用户能正确预测两份指令使用相同角色目标 |
| Magpie target 仍叫 edit，但上游模型已变 | 用户能从处理详情分清请求 target、实际模型与未知信息，不把名称当稳定模型承诺 |
| 服务失效／能力不兼容 | 原型显示可定位原因和修复入口；用户不会把失败理解为内容不值得读；无自动换服务 |
| 需要“新闻省钱、论文长上下文” | 记录是否真为同角色、长期重复、无法靠统一可用目标解决；不得引导用户复制 prompt 伪装路由 |

建议招募 5–8 名有多来源 RSS／BYO AI 经验的用户；关键预测任务至少 80% 首次答对、不得出现误认为改默认会重跑历史或悄悄上云的严重误解。小样本只找可用性问题，不可证明市场普适性。若多位用户反复必须让同一角色用不同模型，并能稳定解释这种区别，再对比 B 与 C；偏向 C 作为可扩展方向，但需证明新增方案概念比重复 prompt 更易用。

## 没有验证的事

没有实机 UI、键盘操作或无障碍验收；没有端到端错误注入、跨账号导入／分享、模型质量／费用比较。Raycast／LM Studio 的闭源实现未核验；LibreChat 是开发边界；Open WebUI 滚动文档不能全部推定随 v0.12.4 发布。Magpie 当前协议与真实路由未重新检查，仍需单独制定兼容性合同。本文只提出交互方案，未实施、未改 ADR、未证明推荐已通过用户测试。
