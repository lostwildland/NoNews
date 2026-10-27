# Information OS 用户能力盘点（迁入 NetNewsWire fork 的讨论底稿）

盘点日期：2026-10-25（Asia/Shanghai）。源仓库：`/Users/extension/design-dev/information-os`。源 HEAD：`e3bb6d1447955f1b43c79ca56fdabbb1fecd0033`。

本报告依据**当前工作树**，不是该提交的纯净快照。盘点末次 `git status --porcelain` 为 70 个修改、4 个删除、26 个未跟踪条目（目录条目不等于文件数）；包括后端、Reader、文档、测试和迁移资料的并发改动。已删除的旧 provider 文件不能据 HEAD 或旧文档算作当前能力。行号对应本次读取，后续工作树变化可能使其移动；没有冻结、提交或更改源仓库。

任务边界：作为被委派研究者直接执行 research 技能，未再委派。只读源代码、仓库文档、配置定义和测试源码；不读取 `.env`、凭据、私人正文、生产数据库、runtime 报告或私人迁移清单，不访问外部服务，不运行服务或测试。唯一产物是本文件。既有记忆仅提示“重新核对注册入口及迁移契约”，结论均以本次源码为依据，不复用历史生产数量或成功记录。

用户目标是：帮助持续跟踪主题、把阅读变成判断或产出的人选择注意力、理解材料，并安心结束阅读。macOS 优先，保留 NNW 现有能力；旧 IO 每项能力都应被看见，但不意味着原样进入首版。这里先盘点能力，最后才给候选模块，**不决定首版范围或重构结构**。NNW 基线另有报告，本报告不重新审计 NNW。

## 证据口径与关键结论

- **实现**：找到当前入口及实现路径；不代表该安装已启用或实际成功。
- **维护实现**：脚本／兼容／迁移路径存在，不属于普通阅读主流程。
- **遗留／退出**：有明确拒绝、移除或替代证据；保留清理／兼容代码不等于功能仍开放。
- **设计／待定**：仅有目标、ADR 或延期说明，未找到足够当前调用链。
- **未发现／未知**：本次抽样未证明；不推断整仓绝对没有。
- **运行未验证**是以上所有条目的共同第二维度：未查部署、配置值、数据库、真实网页／设备和外部回执；测试仅证明仓库写了哪些断言，本次未执行。

IO 不只是“AI 摘要”。当前可见能力覆盖：多来源身份归并、来源级处理策略、不同媒体的材料门槛、评分与人工决定分离、版本与证据、阅读分层、批次及撤销、资料收录、期号采用、个人精读副本、失败恢复和历史迁移。其用户价值同时来自处理和“不误处理”：无材料不冒充低分、无回执不冒充采用、人工 Reject 阻止迟到任务写回。

迁移讨论最容易误认的现状：

1. 当前处理权威是 **feed 设置**，不是 Folder；Folder 主要供导航及批量筛选。
2. Podcast／Video 当前先按 show notes／Reader 描述筛选，正文才是文字稿／字幕；不是默认下载媒体或做 ASR。
3. Paper 新评分达标可持久化自动入选并继续全文／Editor；Important 可在有有效低分时继续加工，但不制造人工入选。人工 Reject 优先。
4. **自动加工资格不等于 Zotero 收录资格**：当前 Zotero 候选需要已提交的人工 Select／Publish／兼容 Star 意图；接受 AI 决定和自动高分本身都不是收录命令。独立 IO Star 按钮已从 Reader 移除，Select 成为保留并收录的入口，宿主收藏另行保留。
5. 正文及 AI 稿默认以数据库版本为权威，已有文件权威逐项兼容；Obsidian 精读是用户显式导出的工作副本。
6. Publish 实际是“采用到已有期号并核验”，不是已公开发布。
7. Reader 手动改稿已无当前 UI／revision API；Quick views 则已有后端持久化。文档对这两点仍有过时描述。

以下引用均相对于源仓库根目录，`路径:行号` 指该文件的证据入口（必要时正文写明范围）。所有链接均为本地一手资料。

## 入口核对

| 入口 | 实际职责与证据 |
| --- | --- |
| 项目契约 | [AGENTS.md](/Users/extension/design-dev/information-os/AGENTS.md:5) 规定正文单一权威、失败显式和条件写入；[README.md](/Users/extension/design-dev/information-os/README.md:14) 明确 FreshRSS 自带订阅、搜索不计为 IO 能力；[PRODUCT.md](/Users/extension/design-dev/information-os/PRODUCT.md:3) 以代码定义现状。 |
| FreshRSS 页面挂载 | `extensions/InformationOS/extension.php:79` 注册控制器、views、Feed／收藏／自动已读信号；`:110` 起挂载 Reader、内容、来源统计、Activity、批次、响应式布局脚本；`:150` 设置导航。不是独立 SPA。 |
| Web API 代理 | `extensions/InformationOS/Controllers/informationosController.php:79` 路由白名单、同源和 CSRF；`:122` 从 FreshRSS 原生搜索解析完整结果范围，不仅取屏幕已加载行。 |
| 后端 | `backend/server.py:356` 为 Application 路由分派；`:879` Reader／版本读取；`:1021` 后台工作；`:1065` AI Job；`:1185` 对账；`:1259` Newsletter、`:1274` Zotero、`:1298` FreshRSS 投影。 |
| 设置入口 | `backend/server.py:666` Quick views，`:673` Feed settings，`:708` Processing，`:719` Kits；`:394` 明确拒绝旧 Provider 管理。 |
| 部署入口 | `scripts/production-bridge.sh:74` 起组装真实目标与写 gate，`:91` worker 数、`:92` full scope；只读了脚本定义，没有启动。 |

## 功能族级清单

### A. 获取和组织信息：先知道什么进入系统

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| A1 接入持续更新的订阅 | **实现**。FreshRSS 提供订阅、条目、分页与原生状态；IO 接收轻量信号后对账，再摄入 observation。不是自带完整 RSS 订阅器。桥接不可用时宿主阅读能力与 IO 处理能力应分开理解。 | `README.md:14`；`docs/integrations.md:7`；`backend/reconciliation.py:14`、`:121`、`:253`；`backend/ingestion.py:46`；`backend/server.py:908`。 |
| A2 同一内容不重复判断 | **实现**。canonical item 与多个 feed observation 分离，身份按媒体作用域及规范 URL／DOI／arXiv／视频 ID 等归并；同篇的人工／AI 状态共享。arXiv 版本可归同 item，但 DOI 发表版并不自动和预印本合并。正常 ingest 并未显式把 Podcast GUID 传给 `identity_for`，不能把文档所列 GUID 能力扩大为所有 Feed 都有稳定 GUID 归并。 | `docs/product-implementation-spec.md:21`；`backend/core.py:147`、`:535`；`backend/ingestion.py:60`；`tests/test_core.py:28`、`:41`；`docs/adr/0009-target-literature-duplicates-use-existing-source-item.md:3`。 |
| A3 按来源选择投入多少处理 | **实现**。每 feed 固定媒体类型、兼容 Kit、材料策略和 disabled／normal／important；新源默认 disabled。Important 允许有效低分后继续正文／Editor，不改 AI 评分、不生成 Human Select、不绕过材料缺失或人工 Reject。它与 FreshRSS“高优先级来源”星标不是一回事。 | `docs/settings.md:7`；`backend/feed_settings.py:38`、`:497`；`backend/pipeline.py:550`；`tests/test_run_contract.py:411`、`:448`；`docs/reader.md:33`。 |
| A4 整理来源而不误改历史处理 | **实现**。来源列表汇总当前订阅、历史身份及宿主仍保存的来源；区分 subscribed／missing／unverified。Folder 可批量筛选处理模式，不能偷偷替混合来源猜媒体／Kit。入库固定合同，单次运行固定 prompt／目标／阈值，防止设置半途混用；显式重跑另有规则。 | `docs/settings.md:9`、`:13`；`backend/feed_settings.py:231`、`:445`、`:527`；`backend/pipeline.py:1845`、`:1915`；`tests/test_run_contract.py:250`、`:307`。 |
| A5 历史目录补齐与范围管理 | **维护实现＋覆盖未知**。期刊 Crossref 目录、arXiv／会议发现、导入、日期修正、去重、范围退出都有维护入口；来源＋时间范围与专题集合关系分离。未证明所有来源自动持续追新、无漏项；历史文档本身记录会议及出版社覆盖缺口。 | `docs/adr/0010-literature-scope-is-target-source-and-time-window.md:3`；`docs/literature-history.md:27`、`:37`；`backend/journal_catalog.py:19`、`:46`；`backend/conference_scope.py:30`、`:71`；`scripts/discover_arxiv_catalog.py`、`scripts/import_scoped_catalog.py`（仅入口盘点）。 |

### B. 获得足够材料：五种媒体不能套同一流程

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| B1 读完整新闻、据正文评估 | **实现**。HTTP／浏览器采集与后备路由、标题／正文／来源图抽取；获取核验后的正文版本才评分，Editor 绑定相同材料。失败保留可重试或人工处理原因；不是凭 Feed 摘要冒充全文。可投影回 FreshRSS，但投影失败不取消数据库正文。 | `docs/content-pipeline.md:27`；`backend/adapters.py:110`；`backend/acquisition/news/scrape.py:378`；`backend/pipeline.py:626`、`:2314`、`:2620`；`tests/test_news_body_scoring.py:110`、`:137`、`:301`。 |
| B2 区分新闻访问障碍 | **实现／外部条件未知**。有 browser runtime 检查、超时监控、archive 后备与人工挑战出口。登录、机构访问、验证码、第三方扩展是否可用不由代码存在证明。不是保证任意新闻站全文可取。 | `docs/content-pipeline.md:31`、`:33`；`docs/production.md:40`、`:46`；`backend/acquisition/news/scrape.py:198`、`:267`；`tests/test_archive_fallback.py`（测试文件盘点）。 |
| B3 用可信摘要筛论文 | **实现**。核对摘要身份、归属、完整性、缓存版本及来源；出版社／arXiv／Crossref／OpenAlex／Semantic Scholar 路线；候选摘要、无摘要、获取失败分开。无可用摘要只译题，Correction 有文种规则排除，不拿已有全文兜底成摘要评分。 | `GLOSSARY.md:19`、`:43`；`docs/content-pipeline.md:35`；`backend/paper_abstract.py:70`、`:152`、`:245`、`:511`、`:777`；`backend/pipeline.py:2389`、`:2397`；`tests/test_paper_abstract.py:117`、`:162`。 |
| B4 选择后深入论文全文 | **实现**。人工入选／新达标评分的持久化事实，或 Important 的有材料低分例外，允许继续取全文及 Editor；Reject 优先，旧高分／已有稿不自动激活历史。摘要回退不算全文，未核验正文阻止自动写稿。另有持久化显式 manual-ReEdit 意图例外，仍核对材料和人工授权，不是普遍绕过核验。 | `docs/content-pipeline.md:17`、`:47`；`backend/core.py:660`、`:687`；`backend/pipeline.py:823`、`:2608`、`:2650`、`:2819`；`tests/test_paper_acquisition_selection_gate.py:139`、`:188`。 |
| B5 保留论文图表公式与来源材料 | **实现／来源适配抽样**。HTML 转 Markdown，MathML／LaTeX、表格、图像和引用结构处理；arXiv、出版社、已有 PDF、MinerU 等路由；PDF 页数／OCR 覆盖核验。来源 HTML／PDF 与正文不同，下载成功不等于可用正文。未逐一核验所有出版社转换质量。 | `docs/adr/0003-html-primary-with-pdf-source-exceptions.md:3`；`docs/content-pipeline.md:51`；`backend/acquisition/paper/fulltext_routes.py:150`、`:455`、`:3134`、`:3430`、`:3551`；`backend/acquisition/paper/mathml_latex.py`；`tests/test_conversion_fidelity.py`、`tests/test_mineru_input_guards.py`（测试族盘点）。 |
| B6 阅读整期 Newsletter | **实现**。足够完整的 Feed issue 优先，较短输入转网页；保留外链顺序和采集元数据。过薄内容保留快照／失败，阻止后续 AI。整期作为一个 item，不自动把外链拆成独立新闻队列。这里是“输入媒体 Newsletter”，与输出期刊采用不同。 | `docs/content-pipeline.md:53`；`backend/adapters.py:236`、`:265`；`backend/acquisition/newsletter/scrape.py`；`backend/pipeline.py:399`。 |
| B7 先判断 Podcast 值不值得深入 | **实现**。先官方单集页 show notes、后备 RSS 内容做评分材料；入选或 Important 才取完整 transcript，再 Editor。区分页面不可读、无稿、过短、需人工；不下载音频、不自动 ASR。show notes 不是完整转录。 | `backend/materials.py:77`；`backend/pipeline.py:373`；`backend/adapters.py:332`；`backend/feed_settings.py:57`；`tests/test_media_material_pipeline.py:122`、`:137`、`:218`。`docs/content-pipeline.md:14` 的旧流程表与当前实现有差异。 |
| B8 先判断 Video 值不值得深入 | **实现**。用 FreshRSS Reader 描述评分；后续仅接受显式 transcript／字幕 URL 或受检 PeerTube API 字幕。YouTube 页面字幕路线未自动开放，缺路由为 manual-required；不调用 yt-dlp，不下载视频，不对音轨 ASR。 | `backend/materials.py:137`；`backend/adapters.py:465`、`:499`（特别是 `:542`）；`backend/pipeline.py:373`；`tests/test_media_material_pipeline.py:309`、`:352`、`:361`。`docs/content-pipeline.md:15` 流程表过时。 |
| B9 配图可读、可追溯和修复 | **实现／可选 gate**。Reader 可按 item 获取本地解析配图；图像引用、上传、校验、staging、receipt、失败重试有独立实现。启用媒体上传可在 Editor 阶段准备图床链接，不能把“News 仅保留远程 URL”的旧描述泛化到所有配置。图床公开 URL 与私有 HTML／PDF 边界要保留。 | `docs/adr/0006-information-os-owns-raw-and-literature-image-namespace.md:3`；`docs/integrations.md:22`；`backend/media_pipeline.py:427`、`:569`、`:597`；`backend/pipeline.py:2714`；`backend/service.py:1953`；`tests/test_media_recovery.py`（测试族盘点）。 |

### C. 选择注意力并形成理解：AI 是角色而非整个产品

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| C1 看评分、理由和局限 | **实现**。Curator 0–10 分、理由、中文标题及媒体特定结果；AI Selected／Rejected、Human 决定、处理阶段分别保存。无有效材料不是零分。当前输出校验要求分数／标题／理由；具体提示词内容在数据库，未读取，因此“长文风格／概念提炼质量”只能记为文档目标及可配置角色，不能证明当前生产提示词确实如此。 | `docs/content-pipeline.md:17`、`:19`；`backend/pipeline.py:2102`、`:2478`、`:2571`；`backend/ai_client.py:67`；`backend/core.py:606`。 |
| C2 按兴趣处理不同来源 | **实现**。Kit 可复用／复制／改名／删除，支持媒体声明、阈值、每角色 prompt 和 Magpie target；不等于已存在独立“主题项目／研究问题”对象。删除受 feed 绑定保护。 | `docs/settings.md:23`；`backend/folders.py:125`、`:178`、`:187`；`backend/feed_settings.py:159`；`backend/server.py:719`。 |
| C3 分类和回看主题 | **实现**。Paper 受控标签词表、最多两个主题及层级／非法组合校验；News 六类编辑分类；投影宿主标签并保留个人标签，历史 Paper 有单独 tags 补分类阶段。受控 AI 领域标签不是通用主题知识图谱。 | `docs/content-pipeline.md:21`、`:81`；`docs/integrations.md:16`；`backend/paper_tags.py`、`prompts/paper/tag.schema.json`；`backend/pipeline.py:1738`；`backend/projection.py`。后两类资产已做文件／入口盘点，未逐项审计 126 个标签语义。 |
| C4 从材料得到可阅读的加工稿 | **实现**。Editor 针对媒体出稿：News JSON 转成标题／图／来源导语／正文；其他媒体走文本输出。输入正文版本、输入哈希、prompt 版本及目标／实际模型来源可追溯。输出不应冒充原文；当前 prompt 是否符合个人编辑风格未知。 | `docs/content-pipeline.md:9`；`backend/pipeline.py:2650`、`:2701`、`:2714`；`backend/ai_client.py:112`；`backend/content_store.py:417`。 |
| C5 明确重评或重写、比较多稿 | **实现**。Run AI／ReCurate／ReEdit；后台阶段重试不抹掉已有成功结果；Draft 版本列表、按需取文本、并排比较与删除受保护版本的限制。不是边读边聊天或跨文档问答。 | `docs/reader.md:43`、`:62`；`backend/pipeline.py:276`；`backend/server.py:639`、`:902`；`backend/service.py:3919`；`extensions/InformationOS/static/native-content.js:748`、`:823`、`:891`。 |
| C6 配置与追溯 AI，而非盲信“成功” | **实现**。每角色单一 Magpie target，网关目录刷新不执行推理；区分 requested target、actual provider／model、reported model；输出截断／非法 JSON／无有效分数显式失败。供应商凭据、fallback、thinking 在外部网关；不能推断 IO 自带多模型共识或自动学习。 | `docs/settings.md:15`；`backend/ai_client.py:84`；`backend/service.py:4558`；`backend/magpie.py:46`；`tests/test_magpie.py:12`、`:23`、`:56`。 |

### D. 阅读、判断、结束：保留用户控制感

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| D1 分层阅读而不混淆证据 | **实现**。Score／Paper Abstract／Draft／Fulltext／Original 分开；摘要候选、摘要缺失、全文失败等各自显示；数据库正文与旧文件权威通过同一 Reader 路径解析。不能因有文字就显示为完整全文。 | `docs/reader.md:39`、`:86`；`backend/service.py:1086`、`:1341`、`:1430`；`extensions/InformationOS/static/native-content.js:315`、`:351`、`:1122`。 |
| D2 阅读论文复杂排版 | **实现／视觉未验证**。Markdown、安全清理 HTML 表格、公式、脚注、图片和内部链接；宽内容滚动，公式失败保留来源，缺图可见。当前实现使用 web 渲染器，不能直接推断 macOS 原生 NNW 渲染已兼容。 | `docs/reader.md:47`；`extensions/InformationOS/static/native-content.js:57`、`:557`、`:577`、`:678`；`tests/fulltext_rendering.test.cjs`、`tests/native_content.test.cjs`（测试族盘点）。 |
| D3 按状态缩小注意力范围 | **实现**。AI／Human／阅读／收藏／Publication 筛选、日期工具、保存／套用／删除 Quick views。Quick views 当前写 `app_settings`，共用 bridge 的客户端可读取同一列表，并有旧 localStorage 迁移／降级；不是文档所说的“仅本机浏览器”。高级搜索保留宿主解释权。 | `docs/reader.md:17`；`extensions/InformationOS/static/native-toolbar.js:160`、`:386`、`:470`、`:560`；`backend/filter_views.py:81`、`:99`；`backend/server.py:666`；`tests/test_filter_views.py:59`、`:77`。 |
| D4 使用熟悉的阅读工作区 | **实现／交互未验证**。响应式一／二／三栏，列宽与主题保存在浏览器；来源／文章导航、方向键／手势、触控长按及桌面多选；编辑控件内不抢键的约束有文档与测试族。布局是 FreshRSS 增强，不宜原样作为 NNW 必须替换的 UI。 | `DESIGN.md:3`；`docs/reader.md:5`、`:96`、`:109`；`extensions/InformationOS/static/normal-view.js`；`extensions/InformationOS/static/native-toolbar.js:46`、`:1025`；`tests/normal_view.test.cjs`（入口及测试族抽样）。 |
| D5 独立表达自己的选择 | **实现，需区分 UI 与兼容 API**。当前 Reader 主要是 Select／Reject／Publish，独立 IO Star 按钮已移除但后端兼容 Star／Unstar；宿主收藏仍在。决定与 AI 分开，约 10 秒命令撤销，重复观察共享结果并暂时收起。Reader 当前要求有 AI 结果才启用 Select／Reject；后端直接人工决定路径不等于 UI 可无评分操作。Select 关联收录意图，不能等同 NNW“已读”。 | `docs/product-implementation-spec.md:27`；`docs/reader.md:58`、`:72`；`backend/core.py:741`、`:784`、`:872`、`:947`；`extensions/InformationOS/static/native-ai.js:396`、`:404`、`:786`。 |
| D6 批量完成审阅与处理 | **实现**。Accept AI decisions 先固定成功 AI 决定与预览；Process current results 固定完整宿主查询范围／选中范围、Kit 分布与模型阶段估计；跳过已审阅／重复／不可处理项。批次路由变化需重新预览；预览不创建任务，提交才写。 | `docs/reader.md:96`；`backend/service.py:790`、`:4210`、`:4264`、`:4314`；`extensions/InformationOS/static/native-batch.js:169`、`:291`；`extensions/InformationOS/Controllers/informationosController.php:122`。 |
| D7 安心放弃而不损害已用成果 | **实现**。人工 Reject 取消待运行工作、使迟到结果失去写授权；数据库文本进入七天恢复期，Select 可取消清理；到期检查采用／投递／精读等引用与备份读回，删除文本但留版本墓碑、身份、评分与审计。不是“已读即删”，也不是所有外部材料都删除。清理后的普通用户恢复 UI 未证明存在。 | `docs/adr/0014-reject-cleanup-seven-day-window.md:23`、`:35`、`:44`；`backend/core.py:996`、`:1023`、`:1092`；`backend/reject_cleanup.py:1`、`:751`、`:840`；`tests/test_reject_cleanup.py:180`、`:281`、`:423`。 |
| D8 自己修改 AI 稿 | **遗留／退出，不能列为当前已实现 UI**。`docs/reader.md:78` 仍描述 Markdown 编辑器，但当前 `buildPane` 明确不创建编辑控件；后端仅有读取与删除稿件路由，没有 revisions API。旧文件稿可以去 Obsidian 改，数据库稿的通用人工编辑闭环本次未找到。DTO 的 database 编辑描述也不能代替真实写入口。 | `extensions/InformationOS/static/native-content.js:868`；`backend/server.py:902`；`backend/service.py:1613`；`tests/test_manual_drafts.py:16`、`:50`。 |

### E. 把阅读转成收藏、个人理解或产出

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| E1 保存到 Zotero 资料库 | **实现，文档有漂移**。当前候选要求 Human selected 加最新已提交 Select／Publish／兼容 Star 收录命令；自动高分、Accept AI、被动历史导入不单独触发收录。维护不同媒体父项；Paper 编辑版本留 IO，非 Paper 可写子笔记。归属不明需显式认领／核验，不能标题近似就接管。 | `backend/zotero.py:1036`、`:1238`、`:1318`；`backend/core.py:1149`；`docs/integrations.md:55` 与源码不完全一致。`tests/test_unified_zotero_collection.py`、`tests/test_zotero.py`（测试族盘点）。 |
| E2 保留既有 Zotero 劳动 | **实现／维护实现**。历史父项关联只读、原子笔记和人工批注不因迁入被覆盖；身份核验、父项元数据、Extra／tags／中文 aliases 同步各有路径。旧 Unstar 非 Paper 清理与 Paper Reject 清理分开。普通新收录不保证全库扫描，现代码仅在旧键／显式认领时做 existing resolution。 | `docs/adr/0007-native-history-and-information-os-editor-ownership.md:3`；`backend/zotero.py:515`、`:565`、`:696`、`:964`、`:1263`；`docs/integrations.md:59` 的“首次完整清单匹配”不能无条件照搬。 |
| E3 在 Obsidian 精读和积累自己的理解 | **实现／插件安装未知**。Zotero 手动动作调用 helper→bridge，按当前正文导出个人笔记；重复执行不覆盖用户改动，缺正文不造空壳，缺文件需显式重建，回写 Zotero fulltext 链接并读回。Reader 胶囊只导航，不自动创建。不是后台每项都向 vault 灌文件。 | `docs/adr/0013-on-demand-reading-notes-are-user-copies.md:3`；`docs/integrations.md:65`；`backend/reading_notes.py:199`、`:302`、`:530`；`scripts/zotero/create-obsidian-note.action.js`（入口盘点）；`tests/test_reading_notes.py:230`、`:271`、`:586`。 |
| E4 采用 News／Paper 到已有期号 | **实现**。Publish 只支持 News、Paper；选择不晚于当天且 todo／doing 的最近已有期号，固定目标与稿件版本，无期号不新建；News 要来源图片。Reader 当前还要求已有可投递稿才启用 Publish；后端保留等待草稿的投递分支，不代表当前 UI 可无稿提交。writer 经过 Linter 和条件写入；没有“把输入 Newsletter 一键发布”的泛化链路。 | `docs/integrations.md:24`；`backend/newsletter.py:408`、`:419`、`:450`；`backend/delivery.py:131`、`:212`、`:341`；`tests/test_publish_adoption.py:113`、`:164`。 |
| E5 知道哪版已采用、防重复、防覆盖 | **实现**。Reader Publish 与 Obsidian Paper Digest 共用 intent／receipt／usage：固定 item、稿件与期号身份；同版定位已有块，换稿要明确确认和当前块哈希。采用不是正式公开发布；旧 deliveries 不自动升级为 verified adoption。后台新稿不静默覆盖期号。 | `GLOSSARY.md:55`；`docs/adr/0016-one-issue-adoption-ledger.md:11`；`backend/delivery.py:275`、`:321`；`backend/literature_receipts.py:58`；`tests/test_publish_adoption.py:189`、`:258`、`:306`。 |
| E6 从 Obsidian 带回采用事实 | **实现／部署未知**。QuickAdd 采用入口、回执刷新宏、spool producer／consumer 及 catch-up 新鲜度；回执只含身份／完整性信息，不带正文。空 spool 不证明“未采用”，需完整扫描证据。必须另验 Obsidian 宏及 bridge 使用同一目录。 | `docs/integrations.md:47`；`scripts/obsidian/receipt-sync.quickadd.js:3`、`:41`；`backend/literature_receipts.py:69`、`:76`；`backend/server.py:945`、`:983`；`tests/obsidian_receipt_sync.test.cjs`（测试族盘点）。 |

### F. 反馈、可信保存与运行可见性

| ID／用户能力 | 当前行为、边界、状态 | 文档与代码证据 |
| --- | --- | --- |
| F1 看来源是否值得继续投入 | **实现**。30／90 天及全历史的人工审阅数、选择率、曾收藏率和 value density；后者为两率平均值。按 distinct feed-item 计，不自动排序／停订／调模型。可为人提供反馈，但不是已实现推荐学习。 | `docs/reader.md:31`；`backend/core.py:1235`；`backend/service.py:4439`；`extensions/InformationOS/static/native-feeds.js:98`；`tests/test_core.py:136`。 |
| F2 追溯自己的判断及 AI 历史 | **实现**。记录人工动作所见 AI run、AI 决策和材料证据、命令与事件；新摘要不替换旧评分依据。文档／代码未证明根据这些反馈自动训练模型、更新 prompt 或个性化排序。 | `GLOSSARY.md:43`；`backend/core.py:606`、`:741`、`:947`；`backend/service.py:1798`；`tests/test_core.py:58`、`:69`；`tests/test_news_body_scoring.py:385`。 |
| F3 不丢正文、不把后来版本当旧证据 | **实现**。正文／AI 稿不可原地改写，来源身份、可用性、哈希和版本记录；条件替换、事务读回、读取验哈希；列表只回元数据，按需读文本。已有 imported／文件权威有单独兼容，不可把 active mapping 数量当成未迁移正文数量。 | `docs/adr/0012-database-owns-body-and-draft-versions.md:16`、`:52`；`docs/adr/0018-per-file-database-authority-cutover.md:18`；`backend/content_store.py:186`、`:395`、`:417`；`backend/service.py:2799`；`tests/test_database_default.py:30`、`:83`。 |
| F4 知道任务做到哪里、出了什么问题 | **实现**。Activity 的 Jobs／Needs attention／History，队列进度、worker 状态、失败分组、同因重试、Dismiss、已解决历史失败；最近 400 Jobs 不代表全局失败总数。取消队列不杀已运行 Job。健康接口显示 live worker／scope，不等于端到端采集投递成功。 | `docs/activity.md:7`、`:17`、`:31`；`backend/server.py:245`、`:357`、`:540`；`backend/service.py:3971`；`extensions/InformationOS/static/native-activity.js:238`、`:506`、`:885`、`:1122`。 |
| F5 控制开销与处理失败 | **实现**。持久化 Job、幂等、分阶段重试、批次展开、worker 1–8 动态池；disabled／人工 Reject 可停止自动耗费。没有证据证明已做完整 token／货币预算面板或费用上限控制。Magpie 单次调用失败与显式重试区别于旧 provider 自动 fallback。 | `docs/settings.md:39`；`backend/jobs.py`（队列入口盘点）；`backend/server.py:1046`、`:1065`、`:1317`；`backend/settings.py:32`；`backend/ai_client.py:88`；`tests/test_processing_pool.py`、`tests/test_jobs.py`（测试族盘点）。 |
| F6 安全连接外部系统 | **实现／安全审计未做**。loopback bridge token、write scope、PHP 同源／CSRF／白名单、目标 gate；外部 HTTP 有地址和重定向策略，文件写入有路径／身份／哈希边界。集成检查不等于真实推理或实际投递测试。 | `docs/production.md:3`、`:44`；`extensions/InformationOS/Controllers/informationosController.php:79`；`backend/server.py:1413`；`backend/network_policy.py`、`backend/runtime_config.py`（策略入口盘点）；`tests/test_network_policy.py`、`tests/test_runtime_config.py`（测试族盘点）。 |
| F7 历史资产归并、迁移、恢复证据 | **维护实现**。旧稿／摘要候选／原始来源关联，数据库导入、逐文件 cutover、manifest、漂移核验和归档／恢复入口；不触发历史模型或外部投递。个人确认过的历史漂移放行策略不应作为新产品普遍信任规则。当前实际迁完多少未知。 | `docs/adr/0004-link-and-classify-legacy-artifacts-before-cleanup.md:3`；`docs/adr/0015-database-cutover-and-legacy-archive.md:3`；`docs/adr/0017-historical-index-drift-policy.md:3`；`docs/adr/0019-historical-frozen-raw-draft-scaffold-and-empty-placeholder-archive.md:9`；`backend/legacy_content_migration.py:270`、`:314`；`backend/production_cutover.py:291`、`:353`。 |

## 文档与代码差异、退出能力、仅设计边界

| 项目 | 本次结论 | 证据及后续讨论影响 |
| --- | --- | --- |
| Folder 决定 Kit | **遗留配置迁移路径**，日常权威已移到 feed。 | `PRODUCT.md:5` 的 Folder routing 描述落后于 `docs/settings.md:7` 和 `backend/feed_settings.py:403`。不因 `FolderProfiles` 类仍在就判断 Folder 仍控制流程。 |
| Podcast／Video 先全文再评分 | **旧概览**；当前先筛选材料、后正文。 | `docs/content-pipeline.md:14` 对照 `backend/pipeline.py:373`、`backend/materials.py:77`、`:137`。 |
| Paper 必须人工选择才取全文 | ADR 0002 的**旧规则**被当前自动入选与 Important 例外扩展；不是只有设计。 | `docs/adr/0002-paper-fulltext-after-human-selection.md:3` 对照 `backend/core.py:660`、`backend/pipeline.py:343`、`:550`。缺摘要也不再先全文补评分。 |
| Star／自动高分与 Zotero | **概览不足以定义收录触发**。当前按已提交人工收录命令，非只看 Star 位，也非自动阈值。 | `docs/integrations.md:57` 对照 `backend/zotero.py:1036`。首版需区分“值得加工”“人工选择”“纳入资料库”。 |
| 独立 Star 按钮、无评分审阅／无稿 Publish | **旧 UI 说明**；当前 Star 不渲染，Select／Reject 需 AI 结果，Publish 需草稿。后端兼容命令不代表可见操作。方向键／手势仍查找 Star 按钮，但不能据残留映射宣称向下收藏有效。 | `docs/reader.md:64`、`:65`、`:118` 对照 `extensions/InformationOS/static/native-ai.js:396`、`:404`、`:413` 及 `extensions/InformationOS/static/normal-view.js:506`、`:532`。 |
| 首次 Zotero 总是全库扫描 | **旧描述**；普通创建不依赖全库扫描，旧键／显式认领才走 resolve。 | `docs/integrations.md:59` 对照 `backend/zotero.py:1263`。不承诺泛用全库去重。 |
| 手动改稿及自动同步修订 | **当前 Reader 功能退出**，文档、DTO 和部分编辑状态变量残留不构成可用入口。 | `docs/reader.md:78`、`docs/product-implementation-spec.md:42` 对照 `native-content.js:868`、`backend/server.py:902`、`tests/test_manual_drafts.py:50`。未来是否重建由产品决定。 |
| Quick views 仅本地 | **已扩大到后端共享**，本地仅旧值迁移／降级。 | `docs/reader.md:29` 对照 `backend/filter_views.py:1`、`native-toolbar.js:470`。共享 bridge 不等于独立多租户／云同步服务。 |
| Provider 管理、直连密钥／fallback | **已退出 IO 的角色**，改由 Magpie。 | `docs/settings.md:19`、`backend/server.py:394`、`backend/ai_client.py:88`；`docs/production.md:26`、`:34` 和 `docs/integrations.md:83` 仍有旧 Provider 说明。 |
| FreshRSS 为唯一新闻全文库、自动向 vault 写 Raw | **旧权威模式／仍有兼容**。默认数据库，旧文件不静默迁移。 | ADR 0011 `:28`、`:37` 与 ADR 0012 `:52`；`backend/service.py:2799`。`AGENTS.md:10`“评分用 entry.content”也已落后于 News 当前正文绑定。 |
| 独立 Obsidian News 笔记自动生成 | **明确退出**，只保留旧登记文件清理及 News 格式辅助。 | `backend/news_notes.py:244`、`:263`；`tests/test_news_notes.py:108`。文件存在不等于仍提供生成能力。 |
| 通用主题研究工作台、跨篇综合／问答、主张证据图谱 | **本次未发现当前入口或完整实现**；不能因有标签、Kit、长文稿就声称已有。 | 已检索范围包括顶层文档、当前 API、Reader、Pipeline 和测试名称；不是穷尽整个私有项目群的否定。用户目标可以要求这些，但不能计为 IO 既有能力。 |
| 自动 ASR、视频理解、通用知识批注 | **未见现行实现**。音视频路径明确停在可读 transcript／caption；Codex annotation 文件是开发注释覆盖层 CSP 兼容。 | `backend/adapters.py:355`、`:542`；`extensions/InformationOS/static/codex-annotations.js:1`；扩展 `:87`。不能把它算为用户论文高亮／批注系统。 |
| 自动公开发布、通用 CMS／邮件分发 | **未证明**。当前期号采用是已实现，公开发布状态未核验；未发现本仓主链有通用 Ghost／邮件发送闭环。 | `GLOSSARY.md:55`、ADR 0016 `:13`、`backend/literature_receipts.py:17`。 |
| 完整会议追新、预印本与发表版自动合并 | **文档明确延期／有缺口**，有目录工具不等于完成。 | `docs/literature-history.md:37`、`:39`；ADR 0009 `:3`。未访问线上或生产资料刷新这些历史状态。 |

部分 ADR 的补记标题写着“2026-11”，晚于本次环境日期；本报告不据这种标题推导发布时点，而以现场源码与调用链判断实现状态。`AGENTS.md:19` 提到的 `docs/architecture/modules.md` 本次路径不存在，不能引用为已读架构事实。

## 个人耦合和移入 macOS fork 必须重新决定的约束

这些是能力迁移的边界，不是要求照搬的实现方案。

1. **宿主耦合**：FreshRSS 的 DOM、搜索语法、标签、entry ID、GReader API、PHP 控制器和 News 内容直写投影。目前 UI 不能当作可直接嵌入 NNW 的完整模块。NNW 的订阅／账号／同步／阅读状态应继续以其现有语义为基线；IO Human decision 不要偷换成已读。证据：`README.md:14`、控制器 `:128`、`backend/ingestion.py:146`。
2. **个人文件与期刊工作流**：`nothing-new-*`／`paper-digest-*`、todo／doing、Neuritis vault、Linter、QuickAdd、Zotero Actions and Tags、citekey／BBT 和 Extra.fulltext 组成具体个人链路。保留“显式导出／采用回执／防覆盖”能力不等于必须沿用这些命名。证据：`backend/newsletter.py:408`、`docs/integrations.md:67`、`scripts/production-bridge.sh:82`。
3. **研究范围和编辑立场**：2023 起、28 期刊、指定会议／arXiv 类别、News 六分类、Paper AI 主题词表、中文标题与排版都是现有用途的选择。代码甚至含目标 feed ID／前缀识别；不能误当通用信息系统的不变量。证据：ADR 0010 `:5`、`docs/literature-history.md:37`、`backend/ingestion.py:112`、`backend/ai/note_lint.py:23`。
4. **服务与运行依赖**：Python bridge、SQLite、Magpie、采集浏览器及其隔离 runtime、可选 OCR／图床、FreshRSS 容器、Obsidian CLI／插件和 Zotero 服务。脚本含个人 HOME／vault／OrbStack 默认路径及 full scope；仓库能跑测试不能证明用户机器依赖已安装。证据：`scripts/production-bridge.sh:40`、`:74`、`:80`、`:92`；`docs/production.md:40`、`:46`。
5. **不可弱化的资料保护**：身份核验、摘要和全文可用性分开、版本来源、条件写入、采用回读、人工修改保护、Reject 的迟到任务授权与恢复窗口。这些保障“安心结束阅读”，不宜当成只为旧迁移存在的杂务。证据：`GLOSSARY.md:23`、`:27`、`:104`；ADR 0012 `:16`；ADR 0014 `:35`。
6. **不应普遍化的历史授权**：ADR 0017 的漂移放行依赖该用户对一批历史文件“近期未修改”的确认；不能在新 NNW 用户资料上默认采用。旧映射、备份、retired 状态和一次性迁移脚本可以独立于首版日常体验，但是否保留迁移入口需另定。

## 测试与覆盖检查

实际采用“根文档／ADR → 挂载与 API → 关键分支 → 测试断言”的抽样。完整阅读根 README／PRODUCT／DESIGN／GLOSSARY 和项目指引；阅读 ADR 0001–0019 的决策或相关契约段，其中较长迁移 ADR 以关键门槛为主；核对当前 UI 注册、控制器、后端路由、处理分支、配置定义。没有逐行阅读整个仓库，没有遍历私人样本或执行任何测试。

抽样中直接读到的断言包括：`tests/test_core.py:28` 身份去重及 `:41` arXiv／DOI 分离；`tests/test_run_contract.py:411` Important 低分继续但不记选择、`:448` Paper 有摘要才继续；`tests/test_manual_drafts.py:50` revision API 拒绝；其他表中给出的测试名称／行号用于定位覆盖意图，并未统一审阅 fixture 真实性或运行结果。外部服务 mock 测试不能证明线上采集、模型质量、Zotero 写入、Obsidian 插件安装或真实回执成功。

| 用户要求的覆盖项 | 对应清单 | 覆盖深度及未知 |
| --- | --- | --- |
| 内容获取、来源分类 | A1–A5、B1–B2、C3 | 已核主入口、feed 合同与目录工具；未核真实订阅全集及站点可达性。 |
| 多模态／论文 | B3–B9 | 已核评分材料与正文差异、gate、主要适配入口；出版社／OCR 保真及字幕可得率为抽样未知。 |
| AI 角色、加工、筛选评分 | C1–C6 | 已核两角色、阈值、Magpie、版本；未读数据库 prompt，实际生成质量未知。 |
| 阅读呈现与结束 | D1–D8 | 已核挂载、状态层、批次、撤销、清理及编辑退出；未做浏览器／macOS 可访问性或手势实测。 |
| 采纳／发布及三类外部工具 | E1–E6 | 已核收录命令、精读副本、issue writer、receipt；未做真实连接与回读。 |
| 反馈、配置、运行可见性 | A3–A4、C2／C6、F1–F6 | 已核统计公式、配置来源、队列与失败入口；未证明自动学习、预算上限或生产运行健康。 |
| 个人耦合、历史与约束 | F7、差异表、个人耦合节 | 已核维护路径及文档陈旧点；不审私人迁移资料，历史完成度不作现状结论。 |

## 候选能力模块：供下一轮讨论，不是最终结构

以下分组源自上面的用户能力，不按当前 Python 文件名机械搬运，也不承诺首版全做。

| 候选边界 | 承担的用户问题／覆盖能力 | 必须先讨论的取舍 |
| --- | --- | --- |
| 来源与关注范围 | 我跟踪什么、哪些来源值得投入；A、F1 | 复用 NNW 来源／文件夹到什么程度；Kit 与用户“主题”是否应分开；目录回填是否只作为维护工具。 |
| 内容材料与证据 | 我现在看的是什么、能信到哪层；B、F3 | 原文／摘要／转录／附件／AI 稿的身份及存储边界；哪些媒体首版只读现成文本。 |
| 判断与加工 | 为什么值得读、如何更好理解；C | 阈值、Important、人工选择之间的关系；保留双角色还是更少入口；数据库稿人工编辑缺口是否优先。 |
| 阅读与完成 | 怎么快速判断，并安心停下；D、F2 | NNW 原生阅读 UI／快捷键保留；IO Select／Reject／收藏与 NNW 已读不混同；七天清理是否适合新用户。 |
| 资料保存与产出 | 怎么变成自己的资料、笔记或一期成果；E | Zotero／Obsidian 是否为可选连接；“采用”通用化到何种产出；首版是否仅显式导出而不建回执系统。 |
| 运行与恢复 | 失败是否可见、如何安全恢复；F4–F7、C6 | 本地常驻 bridge 还是其他承载；后台生命周期、成本可见性、凭据与目标授权；历史迁移独立于日常功能。 |

下一轮应先明确“用户完成一次阅读后留下什么”：仅已读、明确决定、资料库收录、个人理解笔记或可用产出。现有 IO 已区分其中多种状态，但部分 UI 文案与文档仍混用；模块切分应建立在这些能力和边界的取舍之后。
