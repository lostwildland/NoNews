# IO capability parity and acceptance matrix

2026-10-27. Baseline: existing 41-entry inventory; current source must be rechecked and new active capabilities added. No row below is accepted merely because a ticket exists. A retired capability is tracked but cannot be presented as active implementation.

The [command-to-ticket audit](../research/io-command-ticket-coverage.md) classifies all 54 current `Application.handle` route fragments into implemented operations, aliases, guards and refused legacy surfaces. Use it with this matrix during implementation and T30 acceptance; it is source traceability, not runtime proof or a requirement to expose legacy HTTP routes.

The [maintenance/helper follow-up](../research/io-maintenance-port-surfaces.md) expands E2/E3/F7 into the six evidence families below. It samples source entry points beyond HTTP; it does not claim exhaustive script or live-installation coverage. Source implementation and NoNews acceptance remain separate.

The [script entry-point coverage](../research/io-script-ticket-coverage.md) adds a complete 106-entry filename/hash inventory under the observed `scripts/` tree, including aliases and untracked source helpers. Its ticket assignments are audit obligations, not proof that every file is active or ported. Owning tickets and final T30 must record each retained behavior or justified compatibility/supporting disposition; the 41-family baseline is not a cap on capability coverage.

| ID | Existing capability | Owning tickets | Status | Evidence |
| --- | --- | --- | --- | --- |
| A1 | 接入持续更新的订阅 | [T02](https://github.com/lostwildland/NoNews/issues/4), [T04](https://github.com/lostwildland/NoNews/issues/6) | not implemented in NoNews | source inventory only; native verification pending |
| A2 | 同一内容不重复判断 | [T01](https://github.com/lostwildland/NoNews/issues/3), [T04](https://github.com/lostwildland/NoNews/issues/6) | not implemented in NoNews | source inventory only; native verification pending |
| A3 | 按来源选择投入多少处理 | [T04](https://github.com/lostwildland/NoNews/issues/6) | not implemented in NoNews | source inventory only; native verification pending |
| A4 | 整理来源而不误改历史处理 | [T04](https://github.com/lostwildland/NoNews/issues/6) | not implemented in NoNews | source inventory only; native verification pending |
| A5 | 历史目录补齐与范围管理 | [T22](https://github.com/lostwildland/NoNews/issues/24) | not implemented in NoNews | source inventory only; native verification pending |
| B1 | 读完整新闻、据正文评估 | [T05](https://github.com/lostwildland/NoNews/issues/7) | not implemented in NoNews | source inventory only; native verification pending |
| B2 | 区分新闻访问障碍 | [T05](https://github.com/lostwildland/NoNews/issues/7) | not implemented in NoNews | source inventory only; native verification pending |
| B3 | 用可信摘要筛论文 | [T06](https://github.com/lostwildland/NoNews/issues/8) | not implemented in NoNews | source inventory only; native verification pending |
| B4 | 选择后深入论文全文 | [T07](https://github.com/lostwildland/NoNews/issues/9) | not implemented in NoNews | source inventory only; native verification pending |
| B5 | 保留论文图表公式与来源材料 | [T07](https://github.com/lostwildland/NoNews/issues/9) | not implemented in NoNews | source inventory only; native verification pending |
| B6 | 阅读整期 Newsletter | [T08](https://github.com/lostwildland/NoNews/issues/10) | not implemented in NoNews | source inventory only; native verification pending |
| B7 | 先判断 Podcast 值不值得深入 | [T09](https://github.com/lostwildland/NoNews/issues/11) | not implemented in NoNews | source inventory only; native verification pending |
| B8 | 先判断 Video 值不值得深入 | [T10](https://github.com/lostwildland/NoNews/issues/12) | not implemented in NoNews | source inventory only; native verification pending |
| B9 | 配图可读、可追溯和修复 | [T19](https://github.com/lostwildland/NoNews/issues/21) | not implemented in NoNews | source inventory only; native verification pending |
| C1 | 看评分、理由和局限 | [T05](https://github.com/lostwildland/NoNews/issues/7), [T06](https://github.com/lostwildland/NoNews/issues/8) | not implemented in NoNews | source inventory only; native verification pending |
| C2 | 按兴趣处理不同来源 | [T03](https://github.com/lostwildland/NoNews/issues/5) | configuration and bounded native browsing implemented in source; acceptance pending | [current candidate and evidence limits](t03-current-candidate.md); [editor-intent/HIG source audit](t03-native-interaction-source-audit.md); responsiveness, strict/native UI and runner binding verification pending |
| C3 | 分类和回看主题 | [T23](https://github.com/lostwildland/NoNews/issues/25) | not implemented in NoNews | source inventory only; native verification pending |
| C4 | 从材料得到可阅读的加工稿 | [T11](https://github.com/lostwildland/NoNews/issues/13) | not implemented in NoNews | source inventory only; native verification pending |
| C5 | 明确重评或重写、比较多稿 | [T11](https://github.com/lostwildland/NoNews/issues/13) | not implemented in NoNews | source inventory only; native verification pending |
| C6 | 配置与追溯 AI，而非盲信“成功” | [T03](https://github.com/lostwildland/NoNews/issues/5) | durable configuration source in progress; acceptance pending | [R3 findings and evidence limits](t03-preview-binding-review-r3.md); Keychain/package/UI verification pending |
| OUTPUT-PREFERENCES | 保留中文标题／排版工作流，并让新用户选择输出语言与格式 | T03/T06/T11/T12/T16/T17/T27 | not implemented in NoNews | [source-derived output preference contract](../specs/native-output-preferences.md); original history immutable; no runtime evidence |
| D1 | 分层阅读而不混淆证据 | [T12](https://github.com/lostwildland/NoNews/issues/14) | not implemented in NoNews | source inventory only; native verification pending |
| D2 | 阅读论文复杂排版 | [T12](https://github.com/lostwildland/NoNews/issues/14) | not implemented in NoNews | source inventory only; native verification pending |
| D3 | 按状态缩小注意力范围 | [T14](https://github.com/lostwildland/NoNews/issues/16) | not implemented in NoNews | source inventory only; native verification pending |
| D4 | 使用熟悉的阅读工作区 | [T12](https://github.com/lostwildland/NoNews/issues/14) | not implemented in NoNews | source inventory only; native verification pending |
| D5 | 独立表达自己的选择 | [T13](https://github.com/lostwildland/NoNews/issues/15) | not implemented in NoNews | source inventory only; native verification pending |
| D6 | 批量完成审阅与处理 | [T15](https://github.com/lostwildland/NoNews/issues/17) | not implemented in NoNews | source inventory only; native verification pending |
| D7 | 安心放弃而不损害已用成果 | [T13](https://github.com/lostwildland/NoNews/issues/15), [T21](https://github.com/lostwildland/NoNews/issues/23) | not implemented in NoNews | source inventory only; native verification pending |
| D8 | 自己修改 AI 稿 | source compatibility audit | retired source UI — not counted as active | source inventory only; native verification pending |
| E1 | 保存到 Zotero 资料库 | [T16](https://github.com/lostwildland/NoNews/issues/18) | not implemented in NoNews | source inventory only; native verification pending |
| E2 | 保留既有 Zotero 劳动 | [T16](https://github.com/lostwildland/NoNews/issues/18) | not implemented in NoNews | source inventory only; native verification pending |
| E3 | 在 Obsidian 精读和积累自己的理解 | [T17](https://github.com/lostwildland/NoNews/issues/19) | not implemented in NoNews | source inventory only; native verification pending |
| E4 | 采用 News／Paper 到已有期号 | [T18](https://github.com/lostwildland/NoNews/issues/20) | not implemented in NoNews | source inventory only; native verification pending |
| E5 | 知道哪版已采用、防重复、防覆盖 | [T18](https://github.com/lostwildland/NoNews/issues/20) | not implemented in NoNews | source inventory only; native verification pending |
| E6 | 从 Obsidian 带回采用事实 | [T18](https://github.com/lostwildland/NoNews/issues/20) | not implemented in NoNews | source inventory only; native verification pending |
| F1 | 看来源是否值得继续投入 | [T23](https://github.com/lostwildland/NoNews/issues/25) | not implemented in NoNews | source inventory only; native verification pending |
| F2 | 追溯自己的判断及 AI 历史 | [T11](https://github.com/lostwildland/NoNews/issues/13), [T13](https://github.com/lostwildland/NoNews/issues/15) | not implemented in NoNews | source inventory only; native verification pending |
| F3 | 不丢正文、不把后来版本当旧证据 | [T01](https://github.com/lostwildland/NoNews/issues/3), [T11](https://github.com/lostwildland/NoNews/issues/13), [T21](https://github.com/lostwildland/NoNews/issues/23) | not implemented in NoNews | source inventory only; native verification pending |
| F4 | 知道任务做到哪里、出了什么问题 | [T20](https://github.com/lostwildland/NoNews/issues/22) | not implemented in NoNews | source inventory only; native verification pending |
| F5 | 控制开销与处理失败 | [T20](https://github.com/lostwildland/NoNews/issues/22) | not implemented in NoNews | source inventory only; native verification pending |
| F6 | 安全连接外部系统 | [T02](https://github.com/lostwildland/NoNews/issues/4), [T20](https://github.com/lostwildland/NoNews/issues/22) | not implemented in NoNews | source inventory only; native verification pending |
| F7 | 历史资产归并、迁移、恢复证据 | [T01](https://github.com/lostwildland/NoNews/issues/3), [T21](https://github.com/lostwildland/NoNews/issues/23), [T22](https://github.com/lostwildland/NoNews/issues/24), [T27](https://github.com/lostwildland/NoNews/issues/29) | not implemented in NoNews | source inventory only; native verification pending |
| MAINT-ASSET-PROOF | 精确资产／回执只读核验 | T21/T22/T27 | not implemented in NoNews | [source evidence and port cases](../research/io-maintenance-port-surfaces.md); proof is not a write permit |
| MAINT-RECONCILE | 中断迁移分组核对与有据释放 | T20/T21/T22/T27 | not implemented in NoNews | same source follow-up; contradictory bytes remain held |
| MAINT-POST-HOC | 保留事后回执的有限证明范围 | T21/T22/T27 | not implemented in NoNews | same source follow-up; never relabelled write-time/complete |
| MAINT-PRIVATE-RAW | 私有 Raw 归档登记和精确回退 | T21/T22/T27 | not implemented in NoNews | same source follow-up; source tests read, not rerun |
| MAINT-NOTE-RECONCILE | Zotero 子笔记版本与书目信息修复 | T16/T17/T22/T27 | not implemented in NoNews | same source follow-up; authored current draft/ownership preserved |
| MAINT-VERIFIED-CLEANUP | 经核验的清理计划／备份／逐项回执 | T16/T21/T22/T27 | not implemented in NoNews | same source follow-up; cloud result differs from desktop/local readback |
| ENGINE | Bundled private IO startup/settings/jobs and native lifecycle foundation | [T02](https://github.com/lostwildland/NoNews/issues/4) | accepted developer foundation; later business journeys pending | [source/current-bundle/native-control acceptance](t02-accepted-engine.md); Python62pass/1optionalSkip, localCI747, installedharness11, Ready→Stopped→Ready; known fixture diagnostics stay T30 |
| NNW-BASE | Preserve native NNW accounts/read/Star/search and build | [T00](https://github.com/lostwildland/NoNews/issues/2), [T26](https://github.com/lostwildland/NoNews/issues/28), [T30](https://github.com/lostwildland/NoNews/issues/32) | build/launch baseline accepted; full journeys pending | T00 native build, 753 tests, focused regressions and two-axis review: [evidence](t00-review-r3.md); T26/T30 pending |
| SYNC | New IO data cross-device sync, assets and offline merge | [T24](https://github.com/lostwildland/NoNews/issues/26), [T25](https://github.com/lostwildland/NoNews/issues/27), [T26](https://github.com/lostwildland/NoNews/issues/28), [T30](https://github.com/lostwildland/NoNews/issues/32) | pending | no acceptance evidence yet |
| SNAPSHOT | Current-schema lossless snapshot/verify/restore developer interface | [T01](https://github.com/lostwildland/NoNews/issues/3) | accepted; personal cutover pending | Prior [full acceptance](t01-review-r7.md), conflict-policy follow-up and [shared-schema reacceptance](t01-schema-review-r28.md); 53 public tests; no personal migration claim |
| MIGRATION | Complete owner database/assets/config cutover and independent restore | [T01](https://github.com/lostwildland/NoNews/issues/3), [T27](https://github.com/lostwildland/NoNews/issues/29), [T30](https://github.com/lostwildland/NoNews/issues/32) | pending | no acceptance evidence yet |
| ONBOARDING | Independent new-user setup and configurable personal preferences | [T28](https://github.com/lostwildland/NoNews/issues/30), [T30](https://github.com/lostwildland/NoNews/issues/32) | pending | no acceptance evidence yet |
| UX | Native NNW/Apple Liquid Glass/accessibility evidence | [T29](https://github.com/lostwildland/NoNews/issues/31), [T30](https://github.com/lostwildland/NoNews/issues/32) | pending | no acceptance evidence yet |
