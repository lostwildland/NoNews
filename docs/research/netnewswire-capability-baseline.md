# NetNewsWire 保留基线与接入问题

日期：2026-10-25。调查对象是本地 NoNews checkout，HEAD `d9ec7df6f92c53dcd4bc0d9a26d14d9c0716bf8b`，不是对上游最新版本的声明。工作区含先前的技能配置修改。以下为菜单、控制器、共享模块和技术文档的静态盘点，未构建、登录账号或运行设备测试。

## 本轮已由用户确认的方向

- 面向持续追踪主题、需要将阅读转化成判断或产出、受到信息过载困扰的人；不要求用户懂 RSS、部署服务或维护知识库。
- 第一承诺：帮助判断什么值得投入注意力、理解选中的内容、安心结束一次阅读。阅读数量、清空未读和收藏数量不直接作为成功。
- macOS 为首个完整体验验证平台，iPhone 接续阅读纳入设计，不要求三端同时交付。
- 保留 NetNewsWire 现有功能作为基线，先盘点 Information OS 功能并抽象为候选模块，再讨论接入和改善。这不等于已决定保留所有原界面、数据结构或实现。
- Information OS 功能逐项盘点并明确去向，不预先承诺全部原样进入首版。
- 本轮终点为可指导设计开发的产品与架构决策；奖项作为体验品质标杆，科学相关设计需要证据与验证。

### 后续确认（2026-10-25）

- Zotero 和 Obsidian 作为可选 Integrations 配置项；连接方式、触发动作和写入规则尚未决定。
- 用户倾向通过自定义提示词表达兴趣与处理偏好。可复用配置的具体形态待结合 Folo 调研讨论；尚未决定新增“主题工作区”或独立阅读目标对象。

- 保留基线和可选增强的正式决定见 [ADR 0001](../adr/0001-preserve-netnewswire-and-add-optional-capabilities.md)。
- 人工决定与 AI、阅读状态的独立性见 [ADR 0002](../adr/0002-human-decisions-independent-of-ai.md)。
- 新订阅默认正常收取和阅读；用户通过来源设置开启 AI 处理并明确方案与范围，可批量应用；导入订阅不自动启动历史全文采集和生成。用户指出已有 feed settings，应以此能力为讨论起点；具体继承、覆盖及配置项尚未决定。

## 已找到实现入口的功能族

1. **订阅与组织**：新建订阅、文件夹、刷新、OPML 导入导出；账户协议还定义改名、移动、删除、恢复等操作。证据：[菜单](../../Mac/MainMenu/Base.lproj/MainMenu.xib)、[AccountDelegate](../../Modules/Account/Sources/Account/AccountDelegate.swift)、[OPML 导出](../../Shared/Exporters/OPMLExporter.swift)、[导入界面](../../Mac/MainWindow/OPML/ImportOPMLWindowController.swift)。
2. **多账户与同步**：本地、iCloud、Feedly、Feedbin、NewsBlur、FreshRSS、Inoreader、BazQux、The Old Reader 均在账户类型定义中；实际凭据与服务兼容性未验证。证据：[Account.swift 第 40 行](../../Modules/Account/Sources/Account/Account.swift)、[账户说明](../../Technotes/Accounts.markdown)。
3. **浏览、筛选与搜索**：Today、All Unread、Starred；文章搜索、排序、隐藏已读文章/源、下一条未读。证据：[SmartFeedsController](../../Shared/SmartFeeds/SmartFeedsController.swift)、[MainWindowController](../../Mac/MainWindow/MainWindowController.swift)、[菜单](../../Mac/MainMenu/Base.lproj/MainMenu.xib)。
4. **阅读状态与收藏**：已读切换、星标切换、全部/上方/下方标记已读，状态同步。证据：[MainWindowController 第 462 行](../../Mac/MainWindow/MainWindowController.swift)、[AccountDelegate 第 35 行](../../Modules/Account/Sources/Account/AccountDelegate.swift)、[文章与状态分离说明](../../Technotes/ArticlesAndStatuses.markdown)。
5. **正文阅读与呈现**：HTML 渲染、主题、字号、Reader View、浏览器打开、文章内查找。证据：[ArticleRenderer 第 139 行](../../Shared/Article%20Rendering/ArticleRenderer.swift)、[主题管理](../../Shared/ArticleStyles/ArticleThemesManager.swift)、[通用偏好](../../Mac/Preferences/General/GeneralPrefencesViewController.swift)、[ArticleExtractor 第 35 行](../../Shared/Article%20Extractor/ArticleExtractor.swift)。
6. **桌面操作与外部交互**：多窗口、布局与工具栏、快捷键、复制链接、系统分享、AppleScript，以及 NSUserActivity / Spotlight 相关实现。证据：[菜单](../../Mac/MainMenu/Base.lproj/MainMenu.xib)、[分享入口第 588 行](../../Mac/MainWindow/MainWindowController.swift)、[ScriptableArticle](../../Mac/Scripting/Article+Scriptability.swift)、[ActivityManager](../../Shared/Activity/ActivityManager.swift)。没有据此声称跨设备接续已验证。
7. **配置与运行反馈**：账户管理、主题/字号/未读计数呈现、浏览器选择、更新设置、Current Activity、Activity Log、Error Log、账户统计。证据：[Preferences](../../Mac/Preferences/)、[菜单](../../Mac/MainMenu/Base.lproj/MainMenu.xib)。
8. **文章生命周期**：每账户文章库、状态保存与清理策略。证据：[ArticlesDatabase 第 420 行](../../Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesDatabase.swift)、[ArticlesTable 第 253 行及第 578 行](../../Modules/ArticlesDatabase/Sources/ArticlesDatabase/ArticlesTable.swift)。这属于用户数据保留行为，后续不能只检查界面是否还在。

## 接入前必须澄清的边界

- **阅读、AI 加工、采纳、持久保存分别是什么状态？** 账户协议同步的是阅读/星标等既有状态；不能未经决策便把 AI 加工或采纳映射成已读、星标。
- **阅读缓存和长期资料如何共存？** 当前实现会清理部分文章。技术文档对本地账户的描述较粗，代码还含“超过 30 天”的条件；应以代码和后续验证确定迁移行为，不能只抄文档。
- **哪些能力依赖外部服务授权？** `AccountType.isDeveloperRestricted` 标记部分账号类型；Reader View 使用 `extract.feedbin.com/parser` 和 `SecretKey` 引用。这里只读取引用，未读取密钥。复用源码不等于取得上游服务凭据或已能交付。
- **哪些接缝可复用？** AccountDelegate 可作为账户/同步职责的候选接缝，PseudoFeed 可作为聚合视图候选接缝，ArticleRenderer 可作为阅读呈现候选接缝；这些都不是已核准的插件接口或最终模块设计。

## 覆盖与未知

覆盖了 macOS 主要菜单、关键动作实现、账户协议、阅读渲染、主题、状态及文章清理。未逐个审计每个服务适配器、所有快捷键/无障碍行为、iOS 全部入口，也未检查上游差异。后续应把保留基线细化为验收场景，而不是以此清单宣称功能已全部可用。
