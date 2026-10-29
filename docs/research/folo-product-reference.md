# Folo 产品参考：展示分类、AI 复用与可选集成

调研日期：**2026-10-25（Asia/Shanghai）**。供 NoNews 需求讨论，不是产品决策或功能验收。

## 证据范围与版本

- 官方仓库：[RSSNext/Folo](https://github.com/RSSNext/Folo)。默认分支 `dev` 本次固定为 **68edee907003a90877f2ffa6bd9ed9bedababfd4**，提交日期 2026-10-24 UTC。以下 `[D…]` 均为此 SHA 的永久链接，统一于 2026-10-25 读取。
- GitHub latest release 为 [desktop/v1.16.0](https://github.com/RSSNext/Folo/releases/tag/desktop/v1.16.0)，发布于 **2026-10-16 07:10 UTC**；标签解析为 **b5596042964b9e0eb41d1e1b4947cbbdd471faf2**。以下 `[R…]` 为这个发布提交的永久链接。不是根据 `target_commitish: dev` 推断发布代码。
- **D：dev 实现**；**R：发布标签源码存在／抽样一致**；**文案：官方 README 或本地化说明的承诺**；**推论／建议：研究判断**。所有条目的共同限制是 **运行未验证**：未安装、构建、启动 Folo，未登录、调用模型、连接个人集成、播放媒体或测试 UI。
- 只读官方固定提交源码归档、官方包及公开 GitHub 元数据；归档解压到临时目录，未 clone 历史。没有把 Folo 前端调用的服务端 API 当作已审计的后端实现。
- 本项目依据：[IO 能力盘点](information-os-capability-inventory.md)、[NNW 功能基线](netnewswire-capability-baseline.md)、[术语](../../GLOSSARY.md)、[ADR 0001](../adr/0001-preserve-netnewswire-and-add-optional-capabilities.md)、[ADR 0002](../adr/0002-human-decisions-independent-of-ai.md)。保留 NNW 能力、macOS 优先、AI 可选、Integrations 可选；上游兼容不是设计约束；用户偏好提示词复用，尚未批准主题工作区。

## 先看结论

1. **Folo 的六类是订阅视图，不是六条后端加工流水线。** 用户设置存入 subscription 的 `view`，影响导航、条目查询、列表样式、阅读布局，甚至部分翻译字段；条目自身另有 `media`、`attachments`、正文等素材。把它直接映射成 IO 的 News／Paper／Newsletter／Podcast／Video 会丢失材料门槛和处理语义。[D1][D2][D3][D4]
2. **已有可复用提示词，但不等于完整处理 profile。** AI Shortcuts 是有名字、prompt、启用状态和展示位置的复用对象；Personalization 是全局偏好；Actions 是条件与动作规则；AI Tasks 是定时任务。已查类型中没有一个对象同时绑定 feed、材料策略、Curator／Editor、阈值、模型与收录目的地。[D12][D13][D14][D15][D16]
3. **可选连接和实际写入是分开的。** 配置 Obsidian／Zotero 后出现文章动作；内置 Zotero 写入 `webpage`，不代表论文识别或 PDF 归档；Obsidian 直接写本地 Markdown 文件，不是持续双向同步。[D18][D19][D20]
4. **播放、文字材料、AI 使用范围必须分别讨论。** 客户端存在字幕／转录读取路径，不保证每集有全文转录；播放器能播放也不证明 AI 使用了完整音视频材料。[D8][D9][D10][D11][D42]

## 1. “Media Format”究竟是什么

### 名称、enum 与可见类别

本次 dev 英文订阅表单键 `feed_form.view` 的文案是 **View**，中文是“视图”；公共类别名是 Articles、Social Media、Pictures、Videos、Audios、Notifications，另有 All。没有在已检索的本地化文件找到字面 “Media Format”。因此本报告沿用用户问题指称，但不声称当前正式 UI 的标题就是 Media Format，也未追溯旧版本改名历史。[D0][D46][D47][D1][D2]

`FeedViewType` 从 `@follow-app/client-sdk` 再导出。仓库锁定 SDK **0.3.98**；该官方包依赖 `@folo-services/constants` **0.1.58**，包内声明实际数值如下。数字核验来自读取发布包，不是猜测 enum 声明顺序；仓库永久证据是依赖锁和再导出位置。[D39][D22] 官方包：[client-sdk 0.3.98](https://registry.npmjs.org/@follow-app/client-sdk/0.3.98)、[constants 0.1.58](https://registry.npmjs.org/@folo-services/constants/0.1.58)（读取日期同上；未安装）。

| enum | 数值 | 可见名称／意义 |
| --- | ---: | --- |
| All | -1 | All，聚合；`switchable: false`，不能把 feed 订阅到 All |
| Articles | 0 | Articles，文章 |
| SocialMedia | 1 | Social Media，社交内容 |
| Pictures | 2 | Pictures，图片 |
| Videos | 3 | Videos，视频 |
| Audios | 4 | Audios，音频；不能把名字缩窄成仅 Podcast |
| Notifications | 5 | Notifications，通知类内容；不是系统通知权限开关 |

六个 subscription views 都声明 `switchable: true`。实际订阅表单候选还经过当前可见 timeline tabs 过滤，所以“定义了六类”不等于用户任何配置下都看到六个按钮。选择器用同一批 feed entries 预览选中样式，是展示分类的直接证据。[D1][D5]

### 设置入口和作用层级

**新增／编辑订阅表单 → View → 预览 → Follow／Update**。提交调用 subscription follow/edit 同步服务，body 包含 `feedId`、`userId`、`view`、category、title 等。这是“用户的订阅如何呈现”的设置，不是修改一个全局 feed 的媒体实质，也不是逐 entry 设置处理类型。设置中的 Feeds 管理还提供批量 Move to View；List 也有自己的 view 配置，不能把整个领域简化为只在 feed 对象上有一个属性。[D2][D3][D23][D48]

阅读正文时优先取 `subscription.view`，缺失才用 route view；列表查询也带 view。因此它不只是 CSS 切换，兼有组织与筛选含义。另一个维度是 `getView` 的 translation 字段：Articles 为 title/description，SocialMedia 为 content，Pictures/Videos/Audios/Notifications 为 title；这仍不构成材料获取或论文加工协议。[D1][D4][D24]

### 默认、自动推荐、手动覆盖

按 `FeedForm` 的实际顺序：[D2]

1. 初始值取显式 `defaultValues`，否则取当前路由视图；当前是 All 时转 Articles。
2. 编辑已有订阅时，载入已保存的 `subscription.view`；`keepDirtyValues: true` 保留已经改过的表单字段。
3. 尚未订阅、没有显式 `defaultValues.view`，且 API 返回数字 `analytics.view` 时，采用该推荐为起始值，同样保留用户已修改字段。
4. 用户选择视图并保存后写 subscription。没有证据表明每次收到新 entry 都重新自动改写用户视图。

**已知自动的是采用服务端推荐；未知的是推荐算法。** 本仓库的该调用链不能证明 `analytics.view` 根据 MIME、站点白名单、历史多数、模型判断中的哪一种计算，也不能保证混合源分类准确。

具体例子（依据代码推演，未实际点击）：从 All 添加一个 podcast feed，表单先以 Articles 起步；若返回 Audios 推荐且用户未改，显示 Audios。用户改回 Articles 并保存，后续该订阅正文走文章布局，但其音频附件仍可提供播放器。反之，把没有视频素材的 feed 改成 Videos，不会自动取得视频文件、字幕或生成 ASR。[D2][D7][D8]

### 三个应当分开的概念

- **订阅展示／组织偏好**：subscription.view。
- **条目实际素材及能力**：正文、图片/视频 media、MIME 标记的 attachments、可播放 URL、字幕。
- **NoNews 待讨论的处理方案**：先摘要还是全文、何时采集字幕、如何评分/写稿、用哪份提示词、何时允许外部写入。

前两者是 Folo 源码事实；第三者来自 IO 能力盘点的产品问题。它们可以关联，但不能由一个 view enum 代替。[D2][D7][D9] 对照 IO 盘点 A3、B1–B8、C2。

## 2. 列表与阅读体验：按真实 dispatch 看实现

以下为 D 源码行为；布局工厂与 R 文件相同。不是 UI 测试结论。[D6][D43][D7][R2]

| 类别 | 列表 | 阅读详情与边界 |
| --- | --- | --- |
| Articles | `ArticleItem → ListItem`，文章标题/摘要/来源等列表模板 | ArticleLayout：标题、正文、可选摘要、目录/附件；HTML 为普通条目正文路径 |
| Social Media | SocialMediaItem，作者/正文/媒体的社交内容卡片；wideMode | SocialMediaLayout；不是自动转成完整文章 |
| Pictures | PictureItem，GridItem、SwipeMedia；包含 masonry 相关实现；wide/grid | 先到 MediaLayout；实际有视频时走视频，有图片才图片布局，无媒体回文章 |
| Videos | VideoItem，网格、封面、时长，悬停预览路径 | 同样先到 MediaLayout；视频播放器＋标题＋描述/正文或字幕，不是“只播不读” |
| Audios | AudioItem 使用 ListItem | 共用 ArticleLayout，通过音频附件展示播放器，再读正文/转录 |
| Notifications | NotificationItem 使用 `ListItem simple`，精简列表 | 共用 ArticleLayout；通知类订阅与 Actions 的 newEntryNotification 是两回事 |
| All | AllItem，紧凑混合列表，可有音视频标识 | 工厂回退 ArticleLayout；正常已订阅条目的详情仍优先采用它的 subscription.view |

列表证据：[D6]；具体实现：[D25][D26][D27][D28][D29][D30]。详情选择：[D4][D43][D7][D44]。

**注意一个容易漏掉的分支：** Pictures 和 Videos 的详情均不是固定单一 renderer，而是 `MediaLayout` 再查看 entry 实际 media、URL 和 attachments。视频优先，图片次之，没有可识别媒体则文章回退。这是“view 选择＋entry 能力判断”，不是“entry 已被永久分类为 Video”。[D7]

### 音频：正文、播放、转录并存

ArticleLayout 无需 Audios 专属类型即可渲染 `ArticleAudioPlayer`。播放器找第一个有效 `audio/*` attachment；提供播放/暂停、进度及前后 10 秒等控制。打开附件链接的下载入口也不等于已实现离线缓存。无音频附件不会凭 Audios 标签制造播放器。[D8][D41]

`useTranscription` 优先读取 `text/srt` attachment URL；没有字幕但有音频 URL 时调用 `entries.transcription({url})` 并取 `srt`。该查询由阅读布局挂载，**不是只在点击 Transcript 标签之后才发起**。只有有返回转录数据时才显示相应切换；音频转录组件支持关联当前播放条目的进度和跳转。[D9][D10]

不能据接口名称断言“官方稿优先／ASR 兜底／所有音频实时转录”。服务端转录来源、缓存、成本、权限和失败语义没有在此调用端得到证明。对 NoNews 尤其不能用这条链替换 IO 现有的“show notes 筛选→合格完整稿→Editor”材料合同。

### 视频：内嵌播放和文字内容是两条能力

VideosLayout 上方 VideoPlayer，下方标题及 ContentBody／Transcript。视频 URL 根据来源 URL 和 attachments 转换，桌面可使用 webview，Web 使用 iframe；实际可播取决于站点、附件与外部条件。字幕沿用前述 `useTranscription`，不是“每个视频链接都自动生成字幕”。视频 transcript 使用 `type="subtitle"`，组件有别于音频转录的跳转／进度追踪模式。[D9][D10][D11][D42]

### Article、Newsletter、Paper 不应混同

- **Article 是阅读布局类别。** 可以承载普通新闻、博客、论文 RSS 摘要、newsletter 内容，不能由此推出来源材料完整。
- **Newsletter 在此更接近来源接入问题。** Discover 的 Inbox 能提供邮箱地址并有 email/webhook 文案；ArticleLayout 另用 `isInbox` 调整 HTML 样式注入。未见 Newsletter 作为 FeedViewType，不能推断“邮件一来自动拆分所引用的论文”。[D0][D8][D31]
- **Paper 不在这套 view enum 中。** 已读入口未见与 IO 对等的论文身份核验、摘要门槛、全文图表公式质量控制、Curator/Editor 分阶段管线。此为本次范围内未发现，并非断言 Folo 所有代码绝无科学内容支持。Zotero 动作也不能补上这一缺口，因为它明确创建网页记录。[D1][D19]

例子：同一封含三篇论文链接的 newsletter，在 Articles 中可作为一条正文阅读；是否提取三篇论文、按 DOI 归并、取摘要评分，是 NoNews 的另一项候选能力，不是换一个 View 即得到的行为。

## 3. 用户 prompt、AI presets、Actions 与 profile 边界

### 已有的复用单元

**A. Settings → AI → Personalization。** 一个 `personalizePrompt` 设置；编辑器有保存、清空和长度检查，文案定位是偏好驱动的个性化回答。它不是具名 profile 列表。客户端保存字段及同步链存在，但本次未证明服务端在摘要、聊天、定时任务等每个场景如何拼接它，不能声称“所有 AI 必定遵循同一优先级”。[D12][D13]

**B. Settings → AI → AI Shortcuts。** 可创建／编辑名字、图标、prompt、启用状态、list／entry 展示位置；类型还包括 id、hotkey、defaultPrompt。内置服务端 shortcut 与用户自定义 shortcut 合并；有效提示词是 `prompt || defaultPrompt || ""`，意味着有自定义值时替代该默认提示词，不是天然追加。编辑器要求名字、有效 prompt、至少一个目标位置。[D13][D14][D40][D45]

调用时可以直接发送或预填聊天输入；会构造当下的上下文 blocks（例如文章、feed、folder 等），带入聊天消息。**list/entry 是入口可见范围，不是把 prompt 永久绑定所有该类 feed。** 这是最接近用户所说“保存几个 prompt，在阅读不同材料时复用”的现成参考。[D15]

交互例子（产品使用推演）：创建“核对论证”，prompt 写“只依据当前材料，列出主张、证据、局限；没有全文时先说明材料不足”，勾选 entry；阅读一篇文章时从 shortcut 入口调用。再创建用于 list 的“本周进展”，针对当前上下文运行。两者无需建立新主题工作区，但也不自动具备 IO 的版本追溯、有效材料校验或采纳规则。

**C. Settings → AI → Tasks。** 有独立任务 prompt 和 schedule 配置，不能混称为 Actions 或 profile。另存在默认 timeline summary shortcut 的自动触发 hook，因此“所有 shortcuts 都只能手动”也不准确；自动行为应逐入口说明，不能由一个特例推断所有自定义 shortcut 会对每条新内容运行。[D16][D17]

**D. MCP presets。** AI 设置中的 MCP preset 是服务连接模板（configTemplate、quickSetup 等），不是 Curator/Editor prompt preset。它与常规 Settings → Integrations 中的 Obsidian／Zotero 保存命令也不是同一个授权面。[D32]

### Actions：条件规则，不是任意 AI 工作流编辑器

入口是 Actions 子页面／action-setting；包含条件和结果，规则可保存／同步，store 还有 JSON 导入导出。条件支持 subscription view、feed title、category、URL、entry title/content/author、媒体数量、附件时长、状态等；结果字典包含 summary、translation、readability、sourceContent、newEntryNotification、silence、block、star、rewriteRules、webhooks。[D33][D34][D35]

有三点不能扩大解释：

1. `rewriteRules` 编辑的是 `from`／`to` 对，不是用户自定义的“AI 改写文章 prompt”。此处不把其服务端具体替换算法推定为已审计。[D35]
2. 动作定义里没有命名为 “Run my AI Shortcut/profile”、`saveToObsidian` 或 `saveToZotero` 的内置结果。存在 webhook 扩展通道，不等于已有两种集成的自动保存规则。[D34]
3. README 文案描述 Actions 处理新条目；客户端上传规则并接收 entry settings。实际客户端的 readability/sourceContent 效果在打开条目时应用，所以不能把全部动作都描述成“抓取时已经完成”；后端匹配时机、重放旧条目、冲突顺序、webhook 重试等未核验。[D21][D33][D36]

例子：条件“Subscription View 等于 Articles，标题包含 climate”，Then 选择 summary/translation 或 star，是界面能力可表达的规则；这不是“用名叫 Climate 的完整 profile 按摘要/全文两阶段处理并自动收录 Zotero”。没有实际保存该规则或触发服务。

### 对“是否已有可复用 profile”的准确回答

**有命名 prompt 复用（Shortcuts）、规则复用（Actions）、定时任务和连接模板；未找到一个与 IO Kit 等价的完整 processing profile。** 这一区分基于上述对象类型及调用入口，不是对整个产品的绝对不存在证明。Folo 的 `profile` 账户页面也不应当因名称相同被当作处理方案。

NoNews 可以借鉴“轻量具名 prompt＋明确适用上下文”的交互，但候选处理方案是否进一步包含角色 prompt、阈值、材料策略、模型目标、来源绑定，应从 IO 盘点 C2 和新需求决定；不能以“Folo 有 presets”为由宣布已选定概念或新增工作区。

## 4. Integrations：配置、授权、动作与自动化

### Obsidian

**入口：Settings → Integrations → Obsidian。** 桌面可用，Web 对该集成有过滤。配置包含 enableObsidian、obsidianVaultPath；目录按钮调用系统目录选择，检查路径存在并可提示重新选择。命令注册要求 Electron、启用且有路径；填完配置本身不会导出文章。[D18][D19]

**动作：文章操作菜单 Save to Obsidian。** `useEntryActions` 接入命令；命令按 entryId 获取内容，调用 Markdown 转换，再 IPC 写文件。正文优先选已成功取得的 readabilityContent，否则 entry.content；不是默认导出 AI 聊天稿，转换失败还可能退回原 HTML 字符串。[D19][D37][D38]

写入 `${vaultPath}/${清理并截断至80字符的标题或发布日期}.md`；包含 frontmatter、`folo` 标签、标题和正文。已有同名文件返回 `File already exists`，并非更新原笔记。代码没有在这条链下载所有图片为本地附件，也没有双向同步、笔记修订合并或稳定 DOI 去重保证。[D20]

具体例子：选定 Vault 内某目录并启用 → 打开一篇文章 → Save to Obsidian → 写入 Markdown；再次以同名保存会撞名失败。**选择目录是文件目标配置，点击保存是本次动作意图**；该命令路径没有每次再次确认的对话框，不代表用户授予了后台持续写入授权。macOS 沙箱、文件权限及实际写入未验证。

### Zotero

**入口：Settings → Integrations → Zotero。** enableZotero、zoteroUserID、zoteroToken；设置页链接 Zotero keys 与创建 key 页面。命令启用条件仅检查开关和两个字段非空，不是令牌权限已经验证或外部写入成功。[D18][D19]

**动作：Save to Zotero。** 请求为 `POST https://api.zotero.org/users/{userID}/items`，携带 `Zotero-API-Key`。每次构造一个 `itemType: "webpage"`，带标题、作者、description → abstractNote、发布日期、URL、语言；collections/tags 均为空。虽然 API body 是数组，这个 UI 命令只构造当前 entry 一项。[D19][D38]

因此**不是** DOI／arXiv 元数据识别，不是 journalArticle 类型创建，不上传 PDF，不指定文献 collection，也不能声称已形成 IO 所需收录回执／幂等恢复机制。该实现读响应的 failed/success 并提示结果；这只是客户端处理路径，未获得任何真实 Zotero 回执。[D19]

具体例子：填自己的 user ID/key 并启用后，打开论文 RSS 摘要点 Save to Zotero，代码预期创建一个该 URL 的网页记录。若产品需求是“将论文及全文作为文献保存”，需要另定义动作能力，不能把此按钮直接当成已满足。

### 单次与自动触发的边界

本次追踪的两条内置命令均为**用户对当前文章发起保存**，未见配置后自动写入或与星标强制联动。Actions 结果字典没有它们；webhooks、自定义 Integration 请求和 MCP 是别的扩展面，需要独立配置及权限解释，不能等同于内置 Obsidian/Zotero 自动化。[D19][D34][D38]

NoNews 的候选需求应分别问：连接到哪里、允许哪种写入、由哪个用户动作触发、是否允许自动触发、写入什么版本、何时可宣称收录成功。依据已确认 ADR，人工决定、星标和外部收录保持独立；不能照抄 Folo 的“保存网页”去覆盖 IO 的文献收录合同。

## 5. 正式发布与 dev 的差异证据

2026-10-25 逐文件获取 R SHA 并与 D 比较，以下 **9 个文件字节一致**：tabs.tsx、settings/interface.ts、布局 factory.ts、useTranscription.ts、Integrations 设置页、integration commands、主进程 integration service、ShortcutModalContent.tsx、Actions constant.ts。[R1][R2][R3][R4][R5][R6][R7][R8][R9]

`FeedForm.tsx` 不完全一致：dev 增加抓取错误说明，并修复 follow 请求期间读取 isSubscribed 导致按钮/编辑状态混用的问题；本报告讨论的 view 初始值、analytics 推荐、keepDirtyValues 和保存 view 结构在 R 已存在。[D2][R10]

所以可以说“核心界面和调用形态在 v1.16.0 发布标签源码中存在”，**不能**说本次安装的发布二进制、线上服务、所有账户权限或每个端已实测一致。未对整个仓库作 release diff；上文未列入比对的细节只标作 D。README 的跨平台、AI Tasks、自动摘要等陈述仍是文案加部分实现证据，不提升为端到端可用证明。[D21]

## 6. 给 NoNews 的候选能力模块（建议，不决策）

1. **阅读与来源组织基线**：继续保留 NNW 订阅、账户同步、文件夹、搜索、已读/收藏、多窗口和阅读样式。借鉴 Folo 可见视图与内容预览，但无需照搬六个导航入口；先问哪种浏览任务确实受益。依据 NNW 基线及 Folo [D1][D5][D6]。
2. **呈现与媒体能力**：分别表示“用户希望怎么读”和“此条目实际有什么”。播放、原文、show notes、摘要、字幕、完整稿应有可辨身份；改变布局不启动采集或模型。参考 [D7]–[D11]，补足 IO B/D 族的材料可信度要求。
3. **来源设置与可复用处理方案**：在已存在 feed settings 上讨论绑定具名 prompt／Kit；先满足少量可理解的复用场景，不引入已被用户留待决定的主题工作区。Folo Shortcuts 值得借鉴入口和编辑体验，但缺少已证明的 IO 多阶段合同。[D13]–[D15]，IO A3/C2。
4. **可选 AI 理解与加工**：按单条、当前列表或来源未来新条目的范围显式启动；提示词复用与材料核验、版本追溯分离。是否需要聊天、自动列表摘要、定时简报分别讨论，不捆绑为首版前提。[D15]–[D17]，IO B/C/D1。
5. **人工判断与批次控制**：保留不依赖 AI 的 Human decision，独立已读/星标；可借鉴 Actions 的条件可见性，但任何自动规则都应说明影响对象和历史范围。不要默认让自动 star 代表人工保留。[D34]，ADR 0002、IO D/E 族。
6. **可选 Integrations 与收录结果**：Obsidian 用于明确导出的阅读/加工副本；Zotero 按网页收藏与正式文献收录分别讨论。连接配置、具体动作、写入版本、失败/重复、回执是候选职责，不要求用户连接才能阅读。[D18]–[D20]，IO 集成能力与 NNW 基线。
7. **自动化与运行反馈**：如果纳入，分开“来新内容时匹配规则”“打开时应用阅读选项”“定时生成”“外部写入”，不要统一成不可解释的后台智能。对照 [D16][D33][D36] 与 IO 的可重试、条件写入、版本和失败恢复能力。

下一轮最值得讨论的是：用户说“复用 prompt”是复用一段阅读指令，还是复用一整套可自动运行的处理方案；两者可以共存，但不该以 Folo 的名字先替用户作决定。

## 7. 未知与后续验证点

- analytics.view 的计算规则、混合源准确性、服务端是否还有覆盖规则：未得到后端实现证据。
- Personalization 的服务端拼接优先级、对各 AI 场景覆盖范围；实际模型、价格和配额：未核验，不作承诺。
- 转录接口是已有字幕、缓存还是生成、如何计费、缺稿/权限失败反馈：未知；可见 hook 不是运行证明。
- Actions 后端触发、执行顺序、历史重放、webhook 交付和权限：本次仅核对前端配置/保存/消费边界。
- 外部集成真实授权、Zotero key 最小权限、macOS 文件访问、重复点击后的外部状态：未连接，未验证。
- 不把“未发现 Paper 流水线／完整 profile”写成全仓绝无；本次围绕列出的入口、类型和调用链，不是穷尽审计。
- 未核验移动端等价性、无障碍、性能、布局视觉质量和生成质量。没有 UI 截图或“已测试”表述。

## 固定提交证据索引

所有条目采集日期均为 **2026-10-25**。D 为 dev SHA，R 为 desktop/v1.16.0 标签 SHA。每个链接直接指向源码，相关类型及函数名已在正文给出。

[D0]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/locales/app/en.json
- [D0] `locales/app/en.json`
[D1]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/constants/src/tabs.tsx
- [D1] `packages/internal/constants/src/tabs.tsx`
[D2]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/discover/FeedForm.tsx
- [D2] `apps/desktop/layer/renderer/src/modules/discover/FeedForm.tsx`
[D3]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/store/src/modules/subscription/types.ts
- [D3] `packages/internal/store/src/modules/subscription/types.ts`
[D4]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/EntryContent.tsx
- [D4] `apps/desktop/layer/renderer/src/modules/entry-content/EntryContent.tsx`
[D5]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/shared/ViewSelectorRadioGroup.tsx
- [D5] `apps/desktop/layer/renderer/src/modules/shared/ViewSelectorRadioGroup.tsx`
[D6]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/getItemComponentByView.ts
- [D6] `apps/desktop/layer/renderer/src/modules/entry-column/Items/getItemComponentByView.ts`
[D7]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/MediaLayout.tsx
- [D7] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/MediaLayout.tsx`
[D8]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/ArticleLayout.tsx
- [D8] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/ArticleLayout.tsx`
[D9]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/useTranscription.ts
- [D9] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/useTranscription.ts`
[D10]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/MediaTranscript.tsx
- [D10] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/MediaTranscript.tsx`
[D11]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/VideosLayout.tsx
- [D11] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/VideosLayout.tsx`
[D12]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/ai/PersonalizePromptSection.tsx
- [D12] `apps/desktop/layer/renderer/src/modules/settings/tabs/ai/PersonalizePromptSection.tsx`
[D13]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/shared/src/settings/interface.ts
- [D13] `packages/internal/shared/src/settings/interface.ts`
[D14]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/ai/shortcuts/ShortcutModalContent.tsx
- [D14] `apps/desktop/layer/renderer/src/modules/settings/tabs/ai/shortcuts/ShortcutModalContent.tsx`
[D15]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/ai-chat/hooks/useSendAIShortcut.ts
- [D15] `apps/desktop/layer/renderer/src/modules/ai-chat/hooks/useSendAIShortcut.ts`
[D16]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/ai-task/components/ai-task-modal.tsx
- [D16] `apps/desktop/layer/renderer/src/modules/ai-task/components/ai-task-modal.tsx`
[D17]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/ai-chat/hooks/useAutoTimelineSummaryShortcut.ts
- [D17] `apps/desktop/layer/renderer/src/modules/ai-chat/hooks/useAutoTimelineSummaryShortcut.ts`
[D18]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/integration/index.tsx
- [D18] `apps/desktop/layer/renderer/src/modules/settings/tabs/integration/index.tsx`
[D19]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/command/commands/integration.tsx
- [D19] `apps/desktop/layer/renderer/src/modules/command/commands/integration.tsx`
[D20]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/main/src/ipc/services/integration.ts
- [D20] `apps/desktop/layer/main/src/ipc/services/integration.ts`
[D21]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/README.md
- [D21] `README.md`
[D22]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/pnpm-lock.yaml
- [D22] `pnpm-lock.yaml`
[D23]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/feeds.tsx
- [D23] `apps/desktop/layer/renderer/src/modules/settings/tabs/feeds.tsx`
[D24]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/hooks/useEntriesByView.ts
- [D24] `apps/desktop/layer/renderer/src/modules/entry-column/hooks/useEntriesByView.ts`
[D25]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/article-item.tsx
- [D25] `apps/desktop/layer/renderer/src/modules/entry-column/Items/article-item.tsx`
[D26]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/social-media-item.tsx
- [D26] `apps/desktop/layer/renderer/src/modules/entry-column/Items/social-media-item.tsx`
[D27]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/picture-item.tsx
- [D27] `apps/desktop/layer/renderer/src/modules/entry-column/Items/picture-item.tsx`
[D28]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/video-item.tsx
- [D28] `apps/desktop/layer/renderer/src/modules/entry-column/Items/video-item.tsx`
[D29]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/audio-item.tsx
- [D29] `apps/desktop/layer/renderer/src/modules/entry-column/Items/audio-item.tsx`
[D30]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/notification-item.tsx
- [D30] `apps/desktop/layer/renderer/src/modules/entry-column/Items/notification-item.tsx`
[D31]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/discover/Inbox/InboxEmail.tsx
- [D31] `apps/desktop/layer/renderer/src/modules/discover/Inbox/InboxEmail.tsx`
[D32]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/ai/mcp/MCPServicesSection.tsx
- [D32] `apps/desktop/layer/renderer/src/modules/settings/tabs/ai/mcp/MCPServicesSection.tsx`
[D33]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/store/src/modules/action/store.ts
- [D33] `packages/internal/store/src/modules/action/store.ts`
[D34]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/store/src/modules/action/constant.ts
- [D34] `packages/internal/store/src/modules/action/constant.ts`
[D35]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/action/then-section.tsx
- [D35] `apps/desktop/layer/renderer/src/modules/action/then-section.tsx`
[D36]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/ApplyEntryActions.tsx
- [D36] `apps/desktop/layer/renderer/src/modules/entry-content/components/ApplyEntryActions.tsx`
[D37]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/integration/entry-content-markdown.ts
- [D37] `apps/desktop/layer/renderer/src/modules/integration/entry-content-markdown.ts`
[D38]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/hooks/biz/useEntryActions.tsx
- [D38] `apps/desktop/layer/renderer/src/hooks/biz/useEntryActions.tsx`
[D39]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/packages/internal/constants/src/enums.ts
- [D39] `packages/internal/constants/src/enums.ts`
[D40]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/atoms/settings/ai.ts
- [D40] `apps/desktop/layer/renderer/src/atoms/settings/ai.ts`
[D41]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/AudioPlayer.tsx
- [D41] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/AudioPlayer.tsx`
[D42]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/VideoPlayer.tsx
- [D42] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/VideoPlayer.tsx`
[D43]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/factory.ts
- [D43] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/factory.ts`
[D44]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/entry-column/Items/all-item.tsx
- [D44] `apps/desktop/layer/renderer/src/modules/entry-column/Items/all-item.tsx`
[D45]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/settings/tabs/ai.tsx
- [D45] `apps/desktop/layer/renderer/src/modules/settings/tabs/ai.tsx`
[D46]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/locales/common/en.json
- [D46] `locales/common/en.json`
[D47]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/locales/app/zh-CN.json
- [D47] `locales/app/zh-CN.json`
[D48]: https://github.com/RSSNext/Folo/blob/68edee907003a90877f2ffa6bd9ed9bedababfd4/apps/desktop/layer/renderer/src/modules/discover/ListForm.tsx
- [D48] `apps/desktop/layer/renderer/src/modules/discover/ListForm.tsx`
[R1]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/packages/internal/constants/src/tabs.tsx
- [R1] `packages/internal/constants/src/tabs.tsx`
[R2]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/factory.ts
- [R2] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/factory.ts`
[R3]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/useTranscription.ts
- [R3] `apps/desktop/layer/renderer/src/modules/entry-content/components/layouts/shared/useTranscription.ts`
[R4]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/settings/tabs/integration/index.tsx
- [R4] `apps/desktop/layer/renderer/src/modules/settings/tabs/integration/index.tsx`
[R5]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/command/commands/integration.tsx
- [R5] `apps/desktop/layer/renderer/src/modules/command/commands/integration.tsx`
[R6]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/main/src/ipc/services/integration.ts
- [R6] `apps/desktop/layer/main/src/ipc/services/integration.ts`
[R7]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/settings/tabs/ai/shortcuts/ShortcutModalContent.tsx
- [R7] `apps/desktop/layer/renderer/src/modules/settings/tabs/ai/shortcuts/ShortcutModalContent.tsx`
[R8]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/packages/internal/store/src/modules/action/constant.ts
- [R8] `packages/internal/store/src/modules/action/constant.ts`
[R9]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/packages/internal/shared/src/settings/interface.ts
- [R9] `packages/internal/shared/src/settings/interface.ts`
[R10]: https://github.com/RSSNext/Folo/blob/b5596042964b9e0eb41d1e1b4947cbbdd471faf2/apps/desktop/layer/renderer/src/modules/discover/FeedForm.tsx
- [R10] `apps/desktop/layer/renderer/src/modules/discover/FeedForm.tsx`
