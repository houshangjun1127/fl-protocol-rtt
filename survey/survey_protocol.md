# 文献调查协议 —— 联邦学习中"轮次达标（Rounds-to-Target）"报告实践的系统调查

**协议版本**：v1.0（待审）
**日期**：2026-10-12
**对应任务**：工作流 B-1（`execution_plan_20261011.md` §3 B-1）
**状态**：**仅协议设计。尚未执行检索与抽取。** 等待主 agent 审核关卡 **G1** 通过后才启动 B-2。
**产出文件**：`results/survey_protocol.md`（本文件）
**下游产出**：`results/survey_screening_log.md`（B-2）、`results/survey_extraction.csv`（B-3）

---

# G1 审核裁定（主 agent，2026-10-12）

**裁定结果：通过（conditional approve）—— 附三条强制修订，B-2 执行时以下方裁定为准；裁定与正文冲突时，以本章为准。**

协议主体（概念分解、I1–I5/E1–E6 纳排、N0→N3 四级计数闭环、去重键、预注册补充策略、
全文字段与 5 条 checklist 的对齐）审核通过，可据以启动 B-2。
B-1 自陈的三个缺陷经复核均成立，裁定如下：

### 裁定 1 —— 万级 `total` 的检索式（Q3、Q7）不得直接进入主流程，先过精度闸门

实测 Q3 `"communication rounds" "target accuracy" federated learning` = 10,730、
Q7 `"rounds to achieve" accuracy federated learning` = 10,367，作为筛查式已失效
（S2 对未加引号词做近似 OR 处理）。

**强制**：B-2 对**每一条**检索式（含 Q1、Q2、Q4 等量级正常的）先取回**前 100 条**做人工判精度，
记录 `hits_100 / relevant_100`。
- 精度 ≥ 30% → 直接进入主流程；
- 10% ≤ 精度 < 30% → **收紧后重测**（加引号、加邻近限定、限定 venue_type），重测仍 <30% 则弃用；
- 精度 < 10% → **弃用**，不得进入主流程，但在日志中保留弃用理由与实测数字。

Q3b（B-1 提出的收紧版）**未实测**，按同一闸门处理，不得因为"看起来更严"就直接采信。
**禁止把 `total` 当作召回量的证据写进任何交付物**——只报实际取回数与人工判定的相关数。

### 裁定 2 —— Google Scholar 退出检索环节，仅保留全文获取用途

GS 的 `total` 不可信、结果随账号与地区漂移、无法被第三方复现，不满足本调查"可复现"的底线。

**强制**：
- GS **不得作为检索来源**，不计入 `N0`（取消 `N0_gs` 计数口径）。
- 检索来源只剩 **Semantic Scholar Graph API + arXiv API** 两个。
- GS 仅允许出现在 §4.5 全文获取的**第 4 梯队**（找 PDF 链接），且**只记录"由此获取到 PDF"**，
  不得记录或引用其命中数。
- 若 S2+arXiv 走完补充策略后 `N3 < 50`，**如实报 N<50 并在论文中写明**，
  **严禁**为凑数启用 GS 或放宽纳排标准。

### 裁定 3 —— checklist 打勾压成两档，取消 `partial`

B-1 自陈 `partial` 是论文 §5 原文没有的中间档，属于协议扩权；且 `no` 与 `unspecified`
的区分依赖抽取者主观判断，会直接影响 B-4 的缺失率数字。

**强制**：
- 5 条 checklist 的打勾字段（`chk1`–`chk5`）取值**只保留两档**：
  `disclosed` / `not_disclosed`。
- **取消** `partial`、`no` 与 `unspecified` 的分野——凡未达到"明确披露"者一律记 `not_disclosed`。
- 主分析**只报二元缺失率**及其 Wilson CI。B-1 原计划的"双口径敏感性分析"**不再需要**，
  因为不再存在需要靠敏感性分析来兜底的主观档。
- 抽取者仍须在 `notes` 字段自由记录判断依据，供抽复核时溯源，但 `notes` 不参与统计。

### 裁定 4（补充，非 B-1 自陈）—— 抽复核失败的处置要连坐

§4.8 已规定"每批随机抽 2 篇开原文复核，1 错返工整批"。**追加**：
若同一抽取者**累计两批**返工，该抽取者的**全部已交付批次**一律重抽，
不得只返工被抽中的那两批。理由：复核是抽样检验，两批连续出错说明问题在系统而非偶然。

---

# G1 补充裁定 #1（主 agent，2026-10-12 19:30）—— 数据源变更

**背景**：B-2 执行中 S2 匿名端点持续返回 429，Q4–Q7 的**分页**无法继续。
**这不构成"检索失败"**：单页 100 条已全部取回并落盘（共 1091 条），卡住的只是后续分页。
真正的欠账是——去重后 188 个唯一研究，全文筛只完成了 **3 条**。

## 裁定 5 —— 纳入 OpenAlex 为第三个检索源，并作为补充检索的首选

放宽裁定 2 中"来源仅 S2 + arXiv"的限制。新增 OpenAlex（`https://api.openalex.org/works`）。

**判据沿用当初砍掉 Google Scholar 的同一套标准**，逐条对照：

| 标准 | Google Scholar（禁止） | OpenAlex（允许） |
|---|---|---|
| 可复现 | 否，结果随账号/地区漂移 | 是，官方 API，任何人可得同一结果 |
| 命中数可信 | 否，`total` 无意义 | 是，`meta.count` 可复现 |
| 免费无限额 | — | 是 |
| 覆盖面 | — | 2.4 亿+ 文献，已含 S2 与 arXiv 记录 |
| 稳定标识符 | — | 有，DOI / arXiv ID |

**与裁定 2 不冲突**：裁定 2 禁的是**不可复现**的来源，OpenAlex 恰恰相反。

## 强制要求

1. **走同一套精度闸门**（裁定 1）：每个 OpenAlex 检索式先取前 100 条人工判
   `hits_100 / relevant_100`；≥30% 采用、10–30% 收紧重测、<10% 弃用。
   **`meta.count` 同样只作留痕，不得当召回量证据。**
2. 逐请求落盘 `results/survey/raw/oa_{ID}_page{PAGE}.json`，不覆盖。
3. 台账追加进 `results/survey/raw/_fetch_log.tsv`。
4. 去重键沿用 §4.3 优先级；跨源重复**必须合并为一行**，来源字段记录全部来源。
5. **论文必须披露**：Methods 段写明检索使用 OpenAlex（及 Semantic Scholar、arXiv）
   并给出检索日期。**数据源变更不披露即是方法学隐瞒。**

## 执行顺序（不可颠倒）

1. **先榨干现有 188 条候选池** —— 零 API 依赖，今晚即可推进
2. 不足 50 → **OpenAlex 补充检索**（无限额）
3. 仍不足 → **如实报 N<50**，写进 Limitations

**严禁**为凑数放宽 I1–I5/E1–E6，或启用 Google Scholar。

---

## 0. 目标与对齐对象

### 0.1 调查目标

量化联邦学习（FL）文献中"达到某精度阈值所需通信轮数"（下称 **RTT**，rounds-to-target）这一报告的**协议披露缺失率**，为本文主张"协议选择而非算法决定 RTT 排名"提供外部证据。本协议严格界定：调查对象是**报告实践**，不是算法性能，不做任何方法排名。

### 0.2 抽取字段必须对齐的 5 条 checklist（原文抄录）

出处：`the manuscript`，**§5 Minimum disclosure checklist**（文件第 307–329 行；逐条位于 L315–316、L317–319、L320–322、L323–325、L326–329）。原文如下，一字未改：

> 1. **Target value and its justification.** Report $t$, and state why that value.
>    *(§3.1 — the winner depends on $t$.)*
> 2. **Reachable ceiling.** Report the best accuracy any participating method
>    attains in the given setup, so a reader can see how much headroom $t$ leaves.
>    *(§3.1 — 80% means four different things; §4 — HEM's 4-point margin.)*
> 3. **Global training schedule.** Report the learning-rate schedule and whether it
>    was tuned per method or fixed globally. *(§3.2 — a 6–11× effect on the gap on
>    CIFAR-10, and a 19–28× swing ratio on MNIST.)*
> 4. **Statistic definition.** State explicitly whether "reached" means first
>    passage, a sustained level, or a window average, and give the window size.
>    *(§3.3 — first passage rewards oscillation.)*
> 5. **Stability and dispersion.** Report per-seed results, or at minimum the
>    dispersion of the ranking across seeds, together with a stability measure such
>    as the final-window spread and post-peak regression. *(§3.1 — the averaged
>    ranking at 0.80 looks decisive while the seeds split 2/1/1.)*

本协议的 §5 抽取字段表中，`chk1`–`chk5` 五个字段与上述五条**一一对应**，并逐条给出可判定打勾规则（见 §5.3）。

### 0.3 本协议的纪律红线（继承 `execution_plan_20261011.md` §8）

1. **每篇入选论文必须打开原文核对**（出版社页面 / arXiv PDF / 本地 PDF），禁止凭摘要、凭引文、凭记忆填表。每行抽取必须有 `check_method` 与 `rtt_report_location` 证据。
2. **禁止凭记忆列举文献作为示例**。本协议中出现的任何文献标识，只来自 `the manuscript` 自身参考文献表（用于滚雪球种子），不新增任何"我记得有某篇"的条目。
3. 本阶段**不执行检索**，**不执行抽取**，**不运行任何训练进程或分析脚本**。

---

## 1. 检索式

### 1.1 概念分解

| 概念 | 作用 | 代表词面 |
|---|---|---|
| **C1 领域限定** | 必须是联邦学习（含去中心化/分层 FL） | `federated learning`, `federated`, `FedAvg` |
| **C2 计数单位** | 必须以"通信轮"为计时单位 | `communication rounds`, `communication round`, `rounds`, `global rounds` |
| **C3 达标事件** | 必须是"达到某个预先声明的水平" | `rounds to reach`, `rounds to target`, `rounds to achieve`, `rounds required to reach`, `convergence rounds`, `until accuracy reaches` |
| **C4 阈值量** | 阈值必须是精度类量 | `accuracy`, `target accuracy`, `test accuracy`, `% accuracy` |

检索式 = C1 ∧ C2 ∧ C3 ∧ C4 的组合。C2 与 C3 在文献中常常合并出现（"rounds to reach"），因此实际检索式以 **C3 的短语为中心**，用 C1 限定领域。

### 1.2 主数据库：Semantic Scholar Graph API

**端点**：

```
https://api.semanticscholar.org/graph/v1/paper/search
```

**通用参数**（所有检索式共用）：

- `fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy`
- `limit=100`（单次上限；用 `offset` 翻页）
- `year=2017-2026`（时间窗，见 §1.5）

> **翻页与取全量**：`offset` 递增翻页取全量。**B-2 必须先实测确认 `/paper/search` 的 `offset` 上限**（S2 对各端点的分页上限有过变动，本协议不凭记忆写死数值）；若触及上限，改用 `/paper/search/bulk`（按相关度取前若干条）或收紧检索式分片（按年份切片：`year=2017-2019`、`2020-2022`、`2023-2024`、`2025-2026`）。**切片必须留痕**，切片结果合并后仍走同一套去重与筛选。

### 1.3 检索式清单（可直接粘贴执行）

以下 `query=` 后的内容已做 URL 编码；`%22` = 双引号（S2 中用于短语精确匹配），`%20` = 空格。

---

**Q1（核心，短语精确）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22rounds%20to%20reach%22%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：本文 §2 指出 RTT 的系统使用最早见于自适应联邦优化（Reddi et al., ICLR 2021，`the manuscript` 参考文献 [5]），其原文字面即 "rounds to reach"。"rounds to reach" 是达标计时最直白的词面，召回的精度（命中率）应最高，用作**核心池**。

---

**Q2（核心，短语精确）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22rounds%20to%20target%22%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：与 Q1 近义但词面不同（"target" 显式点出阈值概念）。与 Q1 互补，覆盖把阈值显式命名为 "target accuracy" 的一支文献。

---

**Q3（扩展，双短语）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22communication%20rounds%22%20%22target%20accuracy%22%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：把 C2（通信轮）与 C4（目标精度）拆成两个短语，覆盖不写 "rounds to reach" 但在表格里同时给出"通信轮数"和"目标精度"的论文。**⚠ 实测警告：本条在试跑中返回 `total` 过大（见 §1.7），作为独立检索式不可直接用于筛查**，B-2 必须要么改为全短语化（见 Q3b），要么在取回后按字段硬性过滤。

---

**Q3b（Q3 的收紧替代，B-2 优先用此条）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22communication%20rounds%22%20%22target%20accuracy%22%20%22federated%20learning%22&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：把 `federated learning` 也加引号，强制三短语共现。**未实测**，B-2 须先跑一次看 `total` 是否落到可用量级（经验目标：≤ 500）。

---

**Q4（核心，短语 + 精度词）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22rounds%20to%20reach%22%20%22accuracy%22%20federated&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：在 Q1 基础上把 `accuracy` 也短语化（虽然单词引号效果有限），并检查 `federated`（词干，覆盖 federated / federation）。用于检验 Q1 池对"精度类阈值"的收敛性。

---

**Q5（扩展，数量表述）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22number%20of%20communication%20rounds%22%20%22accuracy%22%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：覆盖 "the number of communication rounds required to reach X accuracy" 这一完整表述，是综述类与工程类论文最常见的写法。

---

**Q6（扩展，收敛轮次）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22convergence%20rounds%22%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：覆盖把达标轮数写作 "convergence rounds / rounds to converge" 的一支。**⚠ 试跑未取到数值（两次 429）**，量级待 B-2 实测确认。

---

**Q7（扩展，achieve 词面）**

```
https://api.semanticscholar.org/graph/v1/paper/search?query=%22rounds%20to%20achieve%22%20accuracy%20federated%20learning&fields=title,abstract,year,venue,publicationVenue,externalIds,authors,openAccessPdf,publicationTypes,fieldsOfStudy&limit=100&year=2017-2026
```

*理由*：与 reach/target 并列的第三词面。**⚠ 实测 `total` 过大（见 §1.7）**，与 Q3 同属"需收紧后使用"。

---

**Q8–Q10（N3<50 时的预注册备用检索式，仅在 §4.6 触发时启用）**

```
Q8:  query=%22rounds%20required%20to%20reach%22%20federated%20learning
Q9:  query=%22rounds%20to%20reach%20a%20target%22%20federated
Q10: query=%22communication%20rounds%20to%20reach%22%20%22accuracy%22
```

*理由*：这三条形同 Q1–Q7 的词面变体。**关键纪律：它们在此处预先写死，B-2 不得在分析过程中临时发明新检索式来"凑数"**——任何未预注册的检索式若被使用，必须在筛选日志中单列并说明理由，且属于需要向审稿人披露的方案偏离。

---

**去重种子检索（滚雪球用，非主检索）**：

```
https://api.semanticscholar.org/graph/v1/paper/{paperId}/references?fields=title,abstract,year,venue,externalIds&limit=1000
https://api.semanticscholar.org/graph/v1/paper/{paperId}/citations?fields=title,abstract,year,venue,externalIds&limit=1000
```

### 1.4 补充数据库

**(a) arXiv（补全文词面命中）**

S2 只索引摘要与元数据，而 RTT 常常**只出现在正文表格里、摘要中不出现**。这是本调查最大的召回风险，必须由全文检索补足。

- arXiv API（摘要/标题级）：
  ```
  http://export.arxiv.org/api/query?search_query=all:%22rounds+to+reach%22+AND+all:%22federated%22&start=0&max_results=200&sortBy=submittedDate&sortOrder=descending
  ```
- arXiv **全文**词面检索：arXiv 官方检索接口对全文短语检索的支持有限，实操上以 **Google Scholar 全文检索**（下条）为主；arXiv API 用于按 ID 批量取回元数据与 PDF 链接。
- 用途：① 为 S2 命中记录补齐 `openAccessPdf`；② 作为 §4.5 全文获取升级梯队的第二级。

**(b) Google Scholar（人工，补全文词面命中）**

无官方 API，只能人工操作。**操作方式（B-2 必须照此执行并留痕）**：

1. 检索框输入（逐条执行）：
   - `"rounds to reach" "federated learning" accuracy`
   - `"rounds to target" "federated learning"`
   - `"communication rounds" "target accuracy" federated`
   - `"number of communication rounds" "accuracy" federated learning`
2. 选项：取消勾选 patents、citations；排序 = 按相关度（**不要用按日期**，相关度排序才保证前面的条目最可能命中）。
3. 每个检索式**人工浏览前 200 条**（ Scholar 在约 1000 条后结果质量急剧下降，实际可取回量也受限），逐条记录：标题、年份、来源、是否已在 S2 池中。
4. 用 Scholar 的 "Save" 或导出到 BibTeX 后与 S2 池合并去重；** Scholar 无法批量导出到 1000 条以上，超出部分逐条手工登记**。
5. 留痕：`survey_screening_log.md` 中单列 "GS-Supplement" 段落，写明每个检索式实际浏览条数、新增唯一记录数、检索日期。GS 的 `total` 数字**不可信（估算值，常数量级失真），一律不写进论文，只写"人工浏览 N 条、新增 M 条唯一记录"**。

**(c) 不纳入的数据库及理由**：Scopus/Web of Science（本机无订阅，无法访问）；IEEE Xplore / ACM DL（无全文 API，且 S2 已覆盖其元数据；仅作全文获取用）；DBLP（无摘要，无法做 C3/C4 判定）。

### 1.5 时间窗：2017-01 至 2026-10

**起点理由**：RTT 的计时单位是"通信轮（communication round）"，这一单位由 FedAvg（McMahan et al., AISTATS 2017，`the manuscript` 参考文献 [1]）确立——它引入了"客户端本地训练若干 epoch → 服务器聚合一次 = 一轮"的结构，并把通信轮数作为首要效率指标。在此之前的分布式优化文献没有"轮"这个可比单位，RTT 无从定义。因此 2017-01 是**概念起点**，不是任意截断。

**终点**：检索执行日（预计 2026-10），协议中写作 `year=2017-2026`；若 B-2 实际执行跨月，改为实际年份并在日志中记录检索日期。2026 年数据不完整，**B-4 描述统计中按年份分布报告并注明 2026 为部分年份**。

### 1.6 语言：仅纳入英文全文

- **决定**：仅纳入**可获取英文全文**的研究。
- **理由**：本调查的判定核心是"论文对阈值、统计口径、lr schedule 的**确切措辞**"（例如 "first passage" 与 "moving average over four rounds" 的差别只在原文措辞里）。抽取者无法可靠裁定非英文全文中的这些措辞，勉强纳入会引入不可控的判定误差。
- **边界裁定**：
  - 非英文期刊论文但有**英文预印本**（如 arXiv 英文版）→ **纳入**，以英文预印本为准核对，字段 `notes` 注明原文语种。
  - 仅有非英文全文（如中文期刊无英文版）→ **排除**，筛选日志原因记 `non-English full text`（这是语言排除，不是内容排除，需与 E 类分开计数，便于 B-4 报告语言偏差）。
  - S2 记录语言字段缺失 → 以实际可获取的全文语种裁定；无法获取全文的走 E5。
- **必须披露**：B-4 与论文小节必须写明"仅英文全文"，作为本调查的一项已知局限（会低估中文/其他语种 FL 文献的报告实践）。

### 1.7 试跑实测结果（B-1 阶段，未执行筛查）

**预算使用**：Semantic Scholar API 共发出 **20 次请求**（协议允许上限 20 次），全部为检索可用性试跑。

| ID | 检索式（`query=` 内容） | S2 `total` | 状态 |
|---|---|---|---|
| Q1 | `"rounds to reach" federated learning` | **209** | 实测 |
| Q2 | `"rounds to target" federated learning` | **197** | 实测 |
| Q4 | `"rounds to reach" "accuracy" federated` | **163** | 实测 |
| Q5 | `"number of communication rounds" "accuracy" federated learning` | **1821** | 实测 |
| Q3 | `"communication rounds" "target accuracy" federated learning` | **10730** | 实测（数值异常，见下） |
| Q7 | `"rounds to achieve" accuracy federated learning` | **10367** | 实测（数值异常，见下） |
| Q6 | `"convergence rounds" federated learning` | — | **未测到（两次 429）**，待 B-2 实测 |

**对这些数字的三条必要说明（禁止被误读）**：

1. **这些是 S2 相关度检索的命中计数，不是入选论文数，也不是"报告了 RTT 的论文数"。** 本阶段**未做任何筛查**，因此**精度（命中率）完全未知**。从 Q1/Q2 返回的前 3 条标题看，命中的确是 FL 论文，但这只是 3 条的观察，不能外推为精度估计。
2. **Q3/Q7 的万级 `total` 说明 S2 对未加引号的词做了宽松（近似 OR）处理**，这两条检索式如按现状直接翻页取全量，会带来数量级失控的噪声。**处置：B-2 一律改用 Q3b 式全短语化写法，或按年份切片后逐片硬性过滤。**
3. **去重后的并集规模 N1 未实测**（需要取回全部结果才能算）。Q1/Q2/Q4 三条严格短语检索各落在 **163–209** 区间，可作为"核心池量级"的**下界参考**。**B-2 必须实测并集规模与逐阶段通过率，本协议不给出任何 N1/N2/N3 的预期数字。**

**可用性结论（实测）**：

- 无 API key 的匿名端点**频繁返回 429**。本次 20 次请求中约一半首次请求即被限流，需退避重试（实测 12–15 秒退避后多数可成功；Q6 两次均未成功）。**B-2 必须**：① 请求间隔 ≥ 10 秒 + 429 指数退避重试；② 优先申请 S2 API key（显著提升配额）；③ 每次检索把原始 JSON 落盘，避免重跑。
- 字段 `externalIds`（含 DOI / ArXiv）与 `openAccessPdf` 在试跑中正常返回，可用于 §4.2 去重与 §4.4 全文获取。

---

## 2. 纳入标准

一篇记录进入全文筛（进而可能入选）必须**同时满足 I1–I5**。每条都写成可判定形式；判定不确定时按 §2.6 的裁决顺序处理。

### I1 联邦学习实证研究

论文报告了**自己运行的**实验（含模拟实验），且训练组织方式为联邦结构：存在一个中心服务器/聚合器，客户端在本地数据上训练，周期性聚合。

- **纳入**：FedAvg 及其变体；去中心化 FL（无中心服务器但有对等聚合轮次）；分层/边缘 FL；个性化 FL；跨设备/跨竖井 FL。
- **纳入**：arXiv 预印本。**理由**：FL 文献大量以预印本形式流通，且本文 §3.1 Table 2 已引用的 FedPA（arXiv:2010.05273）与 FedZMG（arXiv:2602.18384）均为预印本；若排除预印本，会与本文既有引用口径冲突并引入发表偏差。字段 `venue` 如实记 `arXiv preprint`。
- **边界 → 排除**：分布式 SGD / 参数服务器架构，**且论文未自称 federated、且无部分客户端参与机制** → 排除（E6），日志注明。
- **边界 → 纳入**：论文自称 federated 或明确使用"部分客户端参与 + 本地多 epoch"结构 → 纳入。

### I2 报告了"达到某精度阈值所需轮数"或可等价换算的表述

论文在至少一个（数据集 × 任务）单元上，给出了"达到某个**明确 stated** 精度水平所需的**通信轮数**"。

**被接受的字面表述（枚举，非穷尽，新词面按同构判定并记入 `notes`）**：

- "rounds to reach X% accuracy" / "rounds to target X"
- "communication rounds required to achieve X"
- "X rounds to converge to Y accuracy"
- 表格列头形如 `# rounds @ target acc`、`Rounds (acc ≥ 0.80)`、`Convergence rounds (80%)`
- 正文形如 "FedAvg needs 42 rounds to reach 80% while …"

**等价换算规则（严格）**：

- **接受**：论文**自己给出**换算所需的全部因子（如"每轮 E 个本地 epoch"，报告总 epoch 数）→ 纳入，字段 `rtt_derived = yes`，`derivation_note` 写出换算式与所引原文位置。
- **接受**：论文以"通信次数/聚合次数"计数且明确等于通信轮数 → 纳入。
- **不接受**：需要**我们**自行假设或外部推断换算因子（例如论文只给总 epoch 数而本地 epoch 数需查代码）→ **排除**，日志记 `no explicit conversion factors`。
- **不接受**：以 wall-clock 时间 / FLOPs / 传输字节数计时的速度比较（除非同时给出轮数）→ 若同时给出轮数则纳入，否则排除（E3）。

### I3 阈值是一个精度类量，且落在具名 split 上

- **接受**：accuracy、top-1 accuracy、test accuracy、weighted/client-averaged accuracy；F1、AUC **仅在论文自己把它当作"target"并给出达标轮数时**接受，字段 `metric_name` 如实记录（B-4 按 metric 分组报告）。
- **接受**：split 为 global test / server-held validation / client-local test / 加权客户端平均——**只要论文指名是哪个**。`metric_split` 记录，未指名记 `unspecified`。
- **边界 → 排除**：阈值是 **loss**（训练损失或测试损失）→ 排除主计数，登记为"次级池"（见 E3 边界），因为本文 §3.1 的论点是精度阈值，loss 阈值不可与之混算。
- **边界 → 排除**：阈值是**相对量**（"达到 FedAvg 最终精度的 95%"）→ 排除主计数，登记次级池（相对阈值与绝对阈值的协议问题不同，混算会污染 §3.1 的"阈值取值跨度"统计）。

### I4 可获得英文全文

见 §1.6。必须有可打开的全文（PDF/HTML），且能定位到 RTT 报告的具体位置。

### I5 时间窗与类型

- 发表年份 ∈ [2017, 检索年]，以**最早公开版本**的年份计（预印本年份优先于期刊年份；两者都记入 `notes`）。
- 原始研究（含提出新方法的论文、测量/基准研究、系统论文），只要含自身实验。

### 2.6 裁决顺序（不确定时）

1. **题摘阶段存疑 → 一律推进到全文**。RTT 常常只出现在正文表格中，题摘看不出 ≠ 没有。**题摘阶段只允许排除" unambiguous 不满足"的情形**（见 §4.3）。
2. **全文阶段存疑 → 两名抽取者独立裁定**；仍不一致 → 记 `notes`，取保守判定（**不纳入**），并把该条列入待议清单交主 agent 裁定。
3. 所有存疑条目在筛选日志中单列 `uncertain` 标记，B-4 报告其数量。

---

## 3. 排除标准

每条给出**判定依据**与**边界如何裁定**。排除计数按**主原因**计一条（一条记录只记一个 E 类主因），避免重复计数。

### E1 纯理论，无实验

- **判定**：全文无任何自己运行的实验（无精度轨迹、无数据集、无实测曲线）。
- **边界 → 纳入**：理论论文**附带**数值验证小节，且该小节报告了 RTT → **纳入**（"含实验的理论论文"不是纯理论）。`notes` 记 `theory paper with empirical section`。
- **边界 → 排除**：只有大 O 收敛率（如 $O(1/\sqrt{T})$）、只有引理证明、只有合成玩具plot而无真实数据集 → 排除。
- **边界 → 排除**：只在他人已发表 trace 上做数值模拟、没有自己训练 → 排除（属二次分析，非原始实验）。

### E2 仅报最终精度，无阈值轮数

- **判定**：报告了最终/最佳精度，但从未给出"达到某阈值需要多少轮"。
- **边界 → 排除**：报告"round R 时的精度"网格（如 R ∈ {50, 100, 200, 500} 各给一个精度值），**但没有声明目标线** → **排除**。这正是本文 §2 提到的 Morafah 等人批评的 accuracy-at-chosen-round 做法，与 RTT 是不同构造，混算会直接摧毁本调查的构念效度。
- **边界 → 纳入**：上述网格**且**正文/表注/图注中明确写出目标值（"the horizontal line marks 80%"）→ 纳入，`rtt_report_location` 记明目标值出处（是正文还是图注）。
- **边界 → 排除**：只给收敛曲线图，图上有视觉上的水平参考线但**全文无任何数值** → 排除（无法抽取 `target_value`，抽到的是我们读图，不是论文报告）。
- **边界 → 排除**：只报"在给定轮数预算内达到的最佳精度"（budgeted final accuracy）→ 排除（方向相反：固定轮数看精度，不是固定精度看轮数）。

### E3 阈值存在，但构造上不构成 RTT

- **(a) best-accuracy-so-far 曲线，无目标线** → 排除。理由：没有"达标事件"，只有单调包络。
- **(b) 收敛判据是精度变化量**（"当连续 k 轮精度提升 < ε 视为收敛"）→ 排除主计数，登记次级池。理由：这是停止准则，不是精度阈值；其"轮数"随 ε 变化的方式与本文 §3.1 研究的阈值取值问题不同构。
- **(c) 收敛判据是梯度范数 / loss < ε** → 排除主计数，登记次级池（同 I3 的 loss 边界）。
- **(d) 有目标值但无轮数**（"all methods eventually reach 80%"，未说各需多少轮）→ 排除（E2 的一种具体情形，主原因记 E2 还是 E3？→ **记为 E3(d)**，因为它已经有阈值概念，只是缺计时；这样 B-4 能区分"完全没阈值概念"与"有阈值但没计时"两类，后者对本文论点更有信息量）。
- **(e) 带资源约束的目标**（"在通信预算 B 内达到 80%"）→ **纳入**，`notes` 记预算约束。理由：仍是阈值计时，只是加了约束条件；约束本身属于协议信息，值得抽取。
- **(f) 阈值是"达到最优方法的 X 分位"等相对口径** → 排除主计数，登记次级池（同 I3）。

### E4 综述 / 非原始研究

- **判定**：无自身实验，只综合他人结果。
- **边界 → 纳入**：提出新方法的论文**同时**含文献综述章节 → 纳入（以其自身实验为准）。
- **边界 → 纳入**：**基准/测量研究**（benchmark / measurement study）——它提出新的测量协议并有自己跑的实验，即使不提新算法 → 纳入。**理由**：本文自己就是这类研究；把这类排除会造成自我排除，且它们的 RTT 报告实践正是调查对象。
- **边界 → 排除**：基准论文的 RTT 数字**全部引自他文**、自己没有跑 → 排除（二次来源），原因记 `E4-secondary`。
- **排除**：survey、review、systematic literature review、editorial、commentary、book chapter 综述、纯数据集论文、纯框架/系统论文（无实验）。

### E5 无法获取全文

- **判定**：按 §4.4 的四级获取梯队全部尝试失败。
- **边界 → 排除**：arXiv 只有 abstract 页面、无 PDF、无其他版本 → 排除，原因记 `E5-no-fulltext`，并记 `last_accessed` 日期。
- **边界 → 纳入**：付费墙，但可在 (1) arXiv 预印本、(2) 作者主页、(3) 机构仓储/PMC 中任一处获得免费全文 → **纳入**，以该免费版本核对，`check_method` 记实际来源。
- **边界 → 排除**：全文存在但为扫描件且文字层不可检索 → 排除（无法可靠定位 RTT 表述），原因记 `E5-unreadable`。
- **必须留痕**：每条 E5 记录**四级梯队各自的尝试结果与日期**，不得只写"无法获取"。

### E6 非联邦轮次结构 / 超出时间窗 / 非英文（见 §1.6）

- **判定**：不满足 I1 的结构要求，或年份 < 2017，或无可获取的英文全文。
- **边界**：见 I1 与 §1.6 各自条款。
- **注意**：语言排除**单独计数**（`E6-language`），与内容性排除分开，便于 B-4 量化语言偏差。

### 次级池（secondary pool）

E3(b)(c)(f) 与 I3 的 loss / 相对阈值条目**不进主计数**，但**必须登记在筛选日志的次级池中**（字段同主表，另加 `pool = secondary`）。理由：它们是"邻近构造"，B-4 可单独报一句"另有 M 篇使用 loss 阈值/停止准则类口径"，既诚实又避免污染主构造。

---

## 4. 抽样流程

### 4.1 阶段定义与计数

| 阶段 | 记号 | 定义 |
|---|---|---|
| 原始命中 | **N0** | 各检索式返回记录数之和（**去重前**，含检索式间重叠） |
| 去重后 | **N1** | 唯一研究（study）数 |
| 题摘筛后 | **N2** | 通过题摘筛、进入全文筛的记录数 |
| 全文筛后 | **N3** | **最终纳入**的记录数（主池） |

外加：`N3s` = 次级池条数（不计入 N3）；`N3_snowball` = 由滚雪球补充纳入的条数（计入 N3，但单独标记来源）。

**每个阶段必须在 `results/survey_screening_log.md` 留档**：逐条记录（编号、标题、年份、来源检索式、该阶段决定、原因/依据）。阶段末尾必须有计数小计，且满足 `N1 = N2 + 题摘排除数`、`N2 = N3 + 全文排除数 + 无法获取数`。**计数不闭环 = 该阶段返工。**

### 4.2 第 1 步：检索（→ N0）

1. 按 §1.3 逐条执行，原始 JSON **逐请求落盘**至 `results/survey/raw/q{ID}_offset{OFFSET}.json`，**不覆盖、不后处理**。
2. 每个检索式单独记录：`query` 原文、执行时间、S2 返回 `total`、实际取回条数、HTTP 状态（429/超时需重试并记录）。
3. 人工补充（arXiv / Google Scholar）单独一段留痕，不并入 N0 的 API 计数，而作为 `N0_gs`、`N0_arxiv` 分列后一起进入去重。

### 4.3 第 2 步：去重（→ N1）

**去重键优先级**（取第一个可用者）：

1. **DOI**：小写、去前缀（`https://doi.org/`）、去首尾空白。
2. **arXiv ID**：去版本号（`2507.15601v2` → `2507.15601`）。
3. **标题 + 第一作者姓 + 年份**：标题规范化 = 小写、去变音符号、去全部标点、空白折叠为单空格。

**预印本 / 正式版合并规则**：同一研究的 arXiv 版与期刊版 → **合并为一行**，`arxiv_id` 与 `doi` 两个字段**都填**，`venue` 取正式版，`year` 取**最早公开年份**（见 I5）。**严禁把同一研究计为 2 篇**——这会直接虚增 N3。

**N1 = 合并后唯一研究数。**

### 4.4 第 3 步：题摘筛（→ N2）

- **输入**：N1 条记录的标题 + 摘要 + 关键词 + venue + 年份。
- **筛法**：**从宽**。题摘阶段**只排除 unambiguous 的情形**：
  - 明显不是 FL（E6）
  - 明显是综述/书章节/社论（E4）
  - 明显纯理论（E1）
  - 无可获取英文全文（E6-language）
- **凡与"是否报告了 RTT"有关的不确定性 → 一律推进到全文**。理由见 §2.6-1（RTT 常只在正文表格里）。
- **校准**（必须做）：**前 50 条由两名抽取者独立筛**，计算一致率；若一致率 < 90%，**先修订本协议的纳排措辞**（并在日志中记录修订），再继续；不允许带着分歧措辞往后跑。
- 输出：N2，以及每条被排除记录的 E 类主因。

### 4.5 第 4 步：全文筛（→ N3）

- **输入**：N2 条记录的全文。
- **全文获取四级梯队**（逐级尝试，逐级留痕；任一级成功即停）：
  1. S2 返回的 `openAccessPdf`
  2. arXiv（按 `arxiv_id` 或标题检索）
  3. DOI 出版社页面 / 机构仓储 / PMC
  4. Google Scholar 的 [PDF] 链接 / 作者主页
- **判定**：应用 I1–I5 与 E1–E6。
- **入选必填证据**（缺一不可，否则视为未完成）：
  - `url_checked`：实际打开的 URL
  - `check_method`：`publisher_page` / `arxiv_pdf` / `local_pdf` / `arxiv_abs` / `repository`
  - `rtt_report_location`：**RTT 报告的确切位置**（如 `Table 4, p.8`、`Section 5.2, Fig. 3 caption`）。这一项是"开原文核对"的硬证据，**填 `unspecified` 的行视为无效，退回重抽**。
  - `check_date`

### 4.6 第 5 步：若 N3 < 50 —— 补充策略（预注册，强制）

**触发条件**：主流程全文筛完成后 `N3 < 50`。**`execution_plan_20261011.md` B-2 的验收要求 N3 ≥ 50**，因此补充检索是协议的组成部分，不是临时补救。

**执行顺序（每一轮都留痕，新增记录回到去重与筛选的同一管道，不另设宽松标准）**：

**第 1 轮 —— 引文回溯（backward snowballing）**

- 种子集（**全部来自本文 `the manuscript` 参考文献表，无一条凭记忆新增**）：
  | 种子 | 本文引用号 | 论文本节角色 |
  |---|---|---|
  | FedAvg（McMahan et al., AISTATS 2017） | [1] | RTT 计时单位的起源 |
  | FedProx（Li et al., MLSys 2020） | [2] | 主流基线方法 |
  | SCAFFOLD（Karimireddy et al., ICML 2020） | [3] | 主流基线方法 |
  | FedDyn（Acar et al., ICLR 2021） | [4] | 主流基线方法 |
  | Adaptive Federated Optimization（Reddi et al., ICLR 2021） | [5] | 本文 §2 指出的 RTT 最早系统使用者 |
  | HEM（Yuan et al., TST 2025） | [6] | 本文 §4 案例研究的规则来源 |
- 操作：用 S2 把每个种子解析为 `paperId`（用标题精确检索取第一条，人工核对标题一致），调 `/paper/{id}/references?limit=1000`，取回其**全部参考文献**。
- **预过滤**：对取回记录的 title+abstract 做词面正则过滤（轮次词 `rounds?|communication` 与阈值词 `target|reach|threshold|accuracy` 共现），未命中者不进入人工筛（但**计数留痕**：`检索到 / 预过滤通过 / 进入题摘筛 / 最终纳入`）。
- 命中者进入 §4.3 题摘筛 → §4.5 全文筛的**同一管道**。

**第 2 轮 —— 引文追踪（forward snowballing）**

- 对象：① 上述 6 个种子；② **所有已入选论文**（引用链延伸）。
- 操作：`/paper/{id}/citations?limit=1000`，同样预过滤 + 同一管道。
- **预注册停止规则**：**当某一轮（一轮 = 处理完一批种子）新增纳入 < 5 篇时停止**。这防止无限扩张，也给 B-4 一个可报告的饱和点。

**第 3 轮 —— 启用预注册备用检索式**

- 启用 §1.3 的 Q8–Q10，以及 Q3b、Q6（若主流程未跑）。同一管道。

**第 4 轮 —— 仍未达 50：如实报告，不放宽标准**

- **硬纪律：绝不为凑够 50 而放宽纳入标准。** 放宽 I2（"是否报告了 RTT"）等于更换被测量的构念，会让整个调查失去意义。
- 若穷尽上述轮次后 N3 仍 < 50：B-4 与论文小节**如实写 N = 实际值**，并写明：① 已执行的补充轮次与各自的召回；② N<50 对 Wilson CI 宽度的影响；③ 本调查因此只能作为"现有报告实践的指示性证据"而非精确 prevalence 估计。
- **所有偏离本协议的动作**（启用未预注册的检索式、放宽某条标准、更换数据库）必须在筛选日志顶部"方案偏离登记表"中单列，并在论文小节中披露。

**留痕要求（每一轮）**——`survey_screening_log.md` 中设独立小节，含：

```
轮次 | 种子/检索式 | 端点 | 执行日期 | 取回记录数 | 预过滤通过 | 进题摘筛 | 全文筛后新增纳入 | 累计 N3 | 备注
```

并保留每轮的原始 JSON。

### 4.7 PRISMA 式流程

```
                     ┌─────────────────────────────────────────────┐
                     │  检索（Semantic Scholar API 主检索）          │
                     │  Q1,Q2,Q4,Q5,Q6(+Q3b)  →  N0_api            │
                     │  补充：arXiv API        →  N0_arxiv         │
                     │  补充：Google Scholar 人工 →  N0_gs          │
                     └────────────────────┬────────────────────────┘
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  N0 = N0_api + N0_arxiv + N0_gs （去重前）   │
                     └────────────────────┬────────────────────────┘
                                          │  去重（DOI > arXivID > 标题+作者+年）
                                          │  预印本/正式版合并为同一研究
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  N1  唯一研究                                │
                     └────────────────────┬────────────────────────┘
                                          │  题摘筛（从宽；存疑→全文）
                                          │  排除：E1纯理论 / E4综述 / E6非FL·非英文
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  N2  进入全文筛                              │
                     └────────────────────┬────────────────────────┘
                                          │  全文筛（I1–I5 / E1–E6）
                                          │  排除：E2无阈值轮数 / E3非RTT构造
                                          │        E5无法获取全文 / E6
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  N3  主池纳入            ──┐                 │
                     │  N3s 次级池（loss/停止准则）│ 若 N3 ≥ 50 → 完成│
                     └───────────────────────────┼─────────────────┘
                                                 │ 若 N3 < 50
                                                 ▼
                     ┌─────────────────────────────────────────────┐
                     │  补充轮（预注册）                             │
                     │  R1 引文回溯（6 个种子的 references）         │
                     │  R2 引文追踪（citations，饱和即停：<5/轮）    │
                     │  R3 备用检索式 Q8–Q10                        │
                     │  R4 仍不足 → 如实报 N=实际值，不放宽标准       │
                     │  每轮新增记录回到 N1/N2/N3 同一管道            │
                     └────────────────────┬────────────────────────┘
                                          ▼
                                    最终 N3（含 N3_snowball 标记）
```

### 4.8 抽取复核机制（质量控制）

**批次划分**：B-3 每批约 10 篇（对齐 `execution_plan_20261011.md` B-3）。

**每批交付时的三重检查**：

1. **行数核对**：CSV 行数 = 该批篇数。
2. **必填字段无空**：所有"未说明"类字段填 `unspecified`（**不算缺失**）；但 `study_id`、`rtt_report_location`、`check_method`、`url_checked`、`check_date`、`target_value` 所属的构造性字段若为 `unspecified` 需逐条说明理由（见 §5.2 的"硬必填 vs 软必填"）。
3. **随机复核（G4 关卡）**：**主 agent 从每批随机抽 2 篇，打开原文逐字段核对**。
   - **1 处错 → 整批返工**（全部 10 篇重抽），不是只改错的那篇。
   - "错"的定义：任何字段与原文不符（含把 `no` 误判为 `yes`、把 `unspecified` 误填为具体值、引用位置错误）。
   - 返工记录写入筛选日志，返工次数本身在 B-4 中报告（作为抽取可靠性的一项证据）。

**额外一致性检查（建议，成本可控）**：

- 每批抽取前，两名抽取者对**同一篇**独立抽取（双人抽 1 篇），逐字段比对，记录不一致字段。整批做完后汇总**逐字段一致率**，B-4 报告（尤其 `chk1`–`chk5` 五个字段的一致率，因为它们是论文结论的直接依据）。
- 若 `chk1`–`chk5` 任一字段一致率 < 90%，**该字段的判定规则需细化后全量重抽**（不能只修这一批）。

---

## 5. 抽取字段表

### 5.1 通用取值规则（适用于全部字段）

1. **三态取值**：凡是"论文是否披露了 X"的字段，取值域为 `yes | no | unspecified`：
   - `yes` —— 原文明确写出（必须能指出位置）。
   - `no` —— **已查全文，确认没有**（这是"缺失的肯定证据"，需要全文核对支撑，不能凭题摘填）。
   - `unspecified` —— 无法判定（措辞含糊、或该项在此研究中不适用且无法分辨）。
2. **`unspecified` 不算缺失值**，不进入"必填为空"的返工判定；但**必须在 `notes` 或字段自身说明为何无法判定**。
3. **B-4 的主分析口径**：`no` 与 `unspecified` **合并计为"未披露"**；同时**必须做敏感性分析**分别报告 `no` 与 `unspecified` 的比例（因为两者含义不同：前者是确定的缺失，后者是我们不知道）。这个双口径是预先指定的，防止"把不知道当成没报"或反之。
4. **数值字段**：填数字，单位按论文原文；无法获得填 `unspecified`，**不得填 0、不得留空、不得填 -1**。
5. **枚举字段**：只能填"允许值域"内列出的值，大小写与下划线照抄。
6. **多值字段**：同一篇涉及多个（数据集 × 阈值）单元时，按 **§5.4 的行粒度规则**处理。
7. **自由文本字段**：英文填写，引用原文措辞时加双引号并给出位置。

### 5.2 硬必填 vs 软必填

- **硬必填**（为空/`unspecified` 则该行无效，退回重抽）：`study_id`、`title`、`venue`、`year`、`url_checked`、`check_method`、`check_date`、`rtt_report_location`、`dataset`、`target_value`、`rtt_statistic_type`、`chk1`–`chk5`。
- **软必填**（可填 `unspecified`）：其余全部。

### 5.3 字段表（对齐 5 条 checklist）

#### A. 标识与核对证据（provenance）

| # | 字段名（CSV 列名） | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 1 | `study_id` | string | `S001`… | 本研究分配的主键，稳定不变 |
| 2 | `title` | string | 原文标题 | 照抄 |
| 3 | `venue` | string | 期刊/会议名，或 `arXiv preprint` | 正式版优先 |
| 4 | `year` | integer | 2017–2026 | 最早公开年份（I5） |
| 5 | `doi` | string | DOI 或 `unspecified` | 去 `https://doi.org/` 前缀 |
| 6 | `arxiv_id` | string | `YYMM.NNNNN` 或 `unspecified` | 去版本号 |
| 7 | `url_checked` | string | URL | **实际打开的那个 URL**（硬必填） |
| 8 | `check_method` | enum | `publisher_page`｜`arxiv_pdf`｜`local_pdf`｜`arxiv_abs`｜`repository`｜`author_page` | 核对方式（硬必填） |
| 9 | `check_date` | date | `YYYY-MM-DD` | 核对日期（硬必填） |
| 10 | `rtt_report_location` | string | 如 `Table 4, p.8` | **RTT 报告的确切位置**（硬必填，"开原文核对"的证据） |

#### B. 目标指标定义（哪个 split、什么精度）

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 11 | `dataset` | string | 数据集名，多个用 `;` 分隔 | 硬必填 |
| 12 | `model` | string | 模型名或 `unspecified` | |
| 13 | `metric_name` | enum | `top1_accuracy`｜`accuracy`｜`f1`｜`auc`｜`loss`｜`other`｜`unspecified` | 什么精度（I3） |
| 14 | `metric_split` | enum | `global_test`｜`server_validation`｜`client_local_test`｜`weighted_client_average`｜`train`｜`other`｜`unspecified` | **哪个 split** |
| 15 | `metric_definition_note` | string | 自由文本或 `unspecified` | 加权方式、是否按样本数加权等 |

#### C. 阈值与目标值 —— **checklist 1**

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 16 | `target_value` | numeric | 论文原文单位的数值，或 `unspecified` | **硬必填**（本文 §3.1 的核心变量；抽不到说明该研究本不该入选，需回查 E3(d)） |
| 17 | `target_value_scale` | enum | `fraction_0_1`｜`percent_0_100`｜`other`｜`unspecified` | 归一化用；B-4 统一换算为 0–1 |
| 18 | `target_justified` | enum | `yes`｜`no`｜`post_hoc`｜`unspecified` | `post_hoc` = 论文自述为事后选定（本文 §3.1 引 FedPA "selected qualitatively"、HEM "deemed satisfactory" 即此类） |
| 19 | `target_justification_text` | string | 自由文本或 `unspecified` | 原文措辞，加引号 |
| 20 | **`chk1_target_value_and_justification`** | enum | `reported`｜`partial`｜`absent` | **checklist 1**：`reported` = 同时给出 $t$ 且给出理由；`partial` = 给出 $t$ 但无理由（或理由只是形容词）；`absent` = 未给出 $t$ |

#### D. 可达天花板 —— **checklist 2**

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 21 | `ceiling_reported` | enum | `yes`｜`no`｜`unspecified` | 是否报告了该 setup 下任何参与方法达到的最佳精度 |
| 22 | `ceiling_value` | numeric | 0–1（归一化后）或 `unspecified` | 同时记原文单位于 `notes` |
| 23 | `ceiling_definition` | string | 自由文本或 `unspecified` | 天花板的口径（跨方法？跨种子？run 内峰值？） |
| 24 | **`chk2_reachable_ceiling`** | enum | `reported`｜`partial`｜`absent` | **checklist 2**：`partial` = 有最终精度表但读者无法据此确定"该 setup 下任何方法达到的最佳精度"（例如只报了被比较方法之一） |

#### E. RTT 统计类型

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 25 | `rtt_statistic_type` | enum | `first_passage`｜`final_window_mean`｜`moving_window`｜`sustained_k_rounds`｜`other`｜`unspecified` | **硬必填**。`first_passage` = 首次触及阈值；`final_window_mean` = 末窗均值（Morafah 式）；`moving_window` = 滑动窗（FedZMG 式）；`sustained_k_rounds` = 连续 k 轮保持 |
| 26 | `rtt_window_size` | integer | ≥1 或 `unspecified` | 窗大小；`first_passage` 时填 `unspecified` |
| 27 | `rtt_statistic_note` | string | 自由文本或 `unspecified` | 原文对"reached"的措辞 |
| 28 | `rtt_derived` | enum | `yes`｜`no` | 轮数是否由我们按论文**自给的**因子换算（I2） |
| 29 | `derivation_note` | string | 自由文本或 `unspecified` | 换算式与原文位置 |

#### F. 规模与数据划分

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 30 | `n_seeds` | integer | ≥1 或 `unspecified` | **种子数** |
| 31 | `per_seed_results_reported` | enum | `yes`｜`no`｜`unspecified` | 是否逐种子报告 |
| 32 | `seed_dispersion_reported` | enum | `yes`｜`no`｜`unspecified` | 是否报告种子间离散度 |
| 33 | `stability_measure_reported` | enum | `yes`｜`no`｜`unspecified` | 是否有稳定性度量（末窗 spread / post-peak regression 等） |
| 34 | `stability_measure_note` | string | 自由文本或 `unspecified` | 具体是哪种度量 |
| 35 | `n_clients` | integer | ≥1 或 `unspecified` | **客户端数** |
| 36 | `client_sampling_rate` | string | 如 `0.1`；`all`；`unspecified` | 每轮参与比例 |
| 37 | `noniid_type` | enum | `dirichlet`｜`sharding`｜`label_skew`｜`feature_skew`｜`quantity_skew`｜`iid`｜`other`｜`unspecified` | **non-IID 设定** |
| 38 | `noniid_parameter` | string | 如 `alpha=0.1`；`unspecified` | 划分参数 |
| 39 | `noniid_note` | string | 自由文本或 `unspecified` | 划分实现细节 |

#### G. 全局训练计划 —— **checklist 3**

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 40 | `lr_schedule_disclosed` | enum | `yes`｜`no`｜`partial`｜`unspecified` | **lr schedule 是否披露**。`partial` = 给了初始 lr 但没给衰减/调度 |
| 41 | `lr_schedule_detail` | string | 自由文本或 `unspecified` | 具体调度（step decay / cosine / 常数 + 参数） |
| 42 | `lr_schedule_tuned_per_method` | enum | `yes`｜`no`｜`unspecified` | 是否逐方法调参 vs 全局固定（checklist 3 后半句） |
| 43 | `total_rounds_budget` | integer | ≥1 或 `unspecified` | 总轮数预算（决定右删失，见本文 §3.1 删失讨论） |
| 44 | `local_epochs` | integer | ≥1 或 `unspecified` | 本地 epoch 数 |

#### H. 五条 checklist 打勾（逐条对应 §0.2）

| # | 字段名 | 类型 | 允许值域 | 对应论文 §5 条目 |
|---|---|---|---|---|
| 45 | **`chk1_target_value_and_justification`** | enum | `reported`｜`partial`｜`absent` | 第 1 条 Target value and its justification |
| 46 | **`chk2_reachable_ceiling`** | enum | `reported`｜`partial`｜`absent` | 第 2 条 Reachable ceiling |
| 47 | **`chk3_global_training_schedule`** | enum | `reported`｜`partial`｜`absent` | 第 3 条 Global training schedule |
| 48 | **`chk4_statistic_definition`** | enum | `reported`｜`partial`｜`absent` | 第 4 条 Statistic definition |
| 49 | **`chk5_stability_and_dispersion`** | enum | `reported`｜`partial`｜`absent` | 第 5 条 Stability and dispersion |
| 50 | `checklist_items_present` | integer | 0–5 | `reported` 计 1，`partial` 计 0.5（B-4 需同时报告"严格计数（仅 reported）"与"宽松计数（reported+partial）"两种口径） |
| 51 | `checklist_items_absent` | integer | 0–5 | 5 − 宽松计数 |

**`chk3` 的打勾规则**（由 #40/#42 派生，避免主观）：
- `reported` = `lr_schedule_disclosed ∈ {yes}` **且** `lr_schedule_tuned_per_method ≠ unspecified`
- `partial` = `lr_schedule_disclosed = partial`，或披露了 schedule 但未说明是否逐方法调参
- `absent` = `lr_schedule_disclosed = no`

**`chk4` 的打勾规则**（由 #25/#26 派生）：
- `reported` = `rtt_statistic_type ∉ {unspecified, other}` **且**（若为窗类统计，`rtt_window_size ≠ unspecified`）
- `partial` = `rtt_statistic_type = other`（说了，但说不清归哪类）
- `absent` = `rtt_statistic_type = unspecified`

**`chk5` 的打勾规则**（由 #31/#32/#33 派生）：
- `reported` = `per_seed_results_reported = yes` **且** `stability_measure_reported = yes`
- `partial` = 二者之一为 `yes`，或 `seed_dispersion_reported = yes` 而 `stability_measure_reported = no`
- `absent` = 三者均非 `yes`

> **派生规则的意义**：把 5 条 checklist 的判定**尽可能落到可机械复现的字段组合**上，减少抽取者主观空间。凡派生规则无法覆盖的情形，在 `notes` 中写明人工裁定理由，B-4 报告人工裁定的条数。

#### I. 记录管理

| # | 字段名 | 类型 | 允许值域 | 说明 |
|---|---|---|---|---|
| 52 | `pool` | enum | `main`｜`secondary` | 主池 / 次级池（E3(b)(c)(f)、loss 阈值、相对阈值进 `secondary`） |
| 53 | `source_query` | string | 如 `Q1`；`snowball_R1_FedAvg` | 来源检索式或滚雪球轮次+种子 |
| 54 | `notes` | string | 自由文本或 `unspecified` | 边界裁定理由、人工裁定说明等 |
| 55 | `extractor` | string | 抽取者标识 | |
| 56 | `extraction_date` | date | `YYYY-MM-DD` | |

### 5.4 行粒度规则（关键，必须在 B-3 前定死）

一篇论文若报告了**多个（数据集 × 阈值）单元**：

- **主分析行 = 该论文的"主单元"**：定义为**论文自己用作头条比较**的那一个（通常是第一个数据集 + 主阈值）。若无法判断，取**正文首个 RTT 表格的第一行**。`notes` 记录选择理由。
- **额外单元**：**不新建行**（否则一篇论文会被计多次，分母失真），而是把其余单元摘要写进 `notes`（格式：`DS2=CIFAR10,target=0.40,rtt=112`）。
- **若不同单元的协议披露情况不同**（例如只在 CIFAR-10 上给了 lr schedule）：`chk*` 按**主单元**判定，`notes` 记录差异。
- **B-4 的分母一律是"论文数"而非"单元数"**，与 N3 闭环。

### 5.5 CSV 表头（可直接复制，UTF-8）

```
study_id,title,venue,year,doi,arxiv_id,url_checked,check_method,check_date,rtt_report_location,dataset,model,metric_name,metric_split,metric_definition_note,target_value,target_value_scale,target_justified,target_justification_text,ceiling_reported,ceiling_value,ceiling_definition,rtt_statistic_type,rtt_window_size,rtt_statistic_note,rtt_derived,derivation_note,n_seeds,per_seed_results_reported,seed_dispersion_reported,stability_measure_reported,stability_measure_note,n_clients,client_sampling_rate,noniid_type,noniid_parameter,noniid_note,lr_schedule_disclosed,lr_schedule_detail,lr_schedule_tuned_per_method,total_rounds_budget,local_epochs,chk1_target_value_and_justification,chk2_reachable_ceiling,chk3_global_training_schedule,chk4_statistic_definition,chk5_stability_and_dispersion,checklist_items_present,checklist_items_absent,pool,source_query,notes,extractor,extraction_date
```

共 **54 列**（上述 56 个编号中，`chk1` 与 `chk2` 分别在 C 节 / D 节与 H 节各出现一次，是同一列，不重复计入）。

### 5.6 字段 ↔ checklist ↔ 论文章节 对齐表

| 论文 §5 条目 | 对应字段 | 直接支撑的论文主张 |
|---|---|---|
| 1 Target value and its justification | `target_value`, `target_value_scale`, `target_justified`, `target_justification_text`, **`chk1`** | §3.1 阈值取值跨度、无人论证 |
| 2 Reachable ceiling | `ceiling_reported`, `ceiling_value`, `ceiling_definition`, **`chk2`** | §3.1 "无天花板的阈值无意义"；§4 HEM 4 点余量 |
| 3 Global training schedule | `lr_schedule_disclosed`, `lr_schedule_detail`, `lr_schedule_tuned_per_method`, **`chk3`** | §3.2 lr 衰减的 6–11× / 19–28× 效应 |
| 4 Statistic definition | `rtt_statistic_type`, `rtt_window_size`, **`chk4`** | §3.3 first passage 偏袒振荡 |
| 5 Stability and dispersion | `n_seeds`, `per_seed_results_reported`, `seed_dispersion_reported`, `stability_measure_reported`, **`chk5`** | §3.1 种子平均掩盖 2/1/1 分裂 |
| （上下文，非 checklist） | `dataset`, `metric_split`, `noniid_type`, `n_clients`, `total_rounds_budget` | §6 局限：现象随 α/数据集而变 |

---

## 6. 本协议未做的事（明确边界）

1. **未执行检索**（B-2），**未执行抽取**（B-3），**未做汇总分析**（B-4）。
2. **未给出任何 N1/N2/N3 的预期数值**。§1.7 只给出实测的**原始命中计数**（S2 `total`），它与最终 N3 之间隔着去重、题摘筛、全文筛三重衰减，**衰减率完全未知，禁止外推**。
3. **未运行任何训练进程或分析脚本**。本阶段唯一的外部调用是 §1.7 的 20 次 Semantic Scholar API 试跑请求。
4. **B-4 的分析方案不在本协议范围**（Wilson CI、Table 2 重设计、小节草稿属 B-4）。

---

## 7. 待 G1 审核裁定的开放问题（我认为审核时最该被挑的毛病）

详见交付汇报；此处只列出需要在审核中被明确裁定的几点：

1. **Q3/Q7 检索式实测 `total` 达万级**（§1.7），说明 S2 对未加引号词的宽松处理会让检索式失效。是否接受"改用 Q3b 全短语化"，或要求 B-2 先做一次召回/精度双测（取回 100 条人工判精度）再定稿？
2. **Google Scholar 补充检索的可复现性弱**（人工浏览、无 `total`、结果随账号与地区变化）。是否接受"只报人工浏览条数与新增唯一记录数、不报 `total`"这一留痕口径？
3. **`unspecified` 与 `no` 的区分依赖抽取者判断**（§5.1）。是否接受"主分析合并计为未披露 + 敏感性分析分开报"的双口径？
4. **行粒度规则**（§5.4）把多单元论文压成一行，会损失信息。是否接受？或改为"主池一行 + 单元级附表"？
5. **`chk*` 的 `partial` 档**是我新增的、论文 §5 原文没有的中间档。是否接受三档（`reported|partial|absent`）还是必须压成两档（有/无）？
