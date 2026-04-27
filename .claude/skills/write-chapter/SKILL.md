---
name: write-chapter
description: Writes webnovel chapters (default 2000-3000 words). Use when the user asks to write a chapter or runs /webnovel-write. Runs context, drafting, review, polish, and data extraction.
allowed-tools: Read Write Edit Grep Bash Task
---

# 执行指令

当此 skill 被调用时，必须按以下步骤执行，不能仅显示文档：

1. 提取章节号参数（如 "第16章" → 16）
2. 运行 Step 0: 预检与环境设置
3. 运行 Step 1: 上下文搜集与执行包组装（主 Agent 内联，加载 context-guide 参考）
4. 运行 Step 1-save: 执行包存档（Write 写入 tmp 目录）
5. 运行 Step 2: 正文起草（主 Agent）
6. 运行 Step 3: 自审 + 机械扫描（主 Agent 内联审查 + Bash 执行 chapter_scan.py）
7. 运行 Step 4: 润色（消费 Step 3 审查报告 + 扫描结果，1 轮）
8. 运行 Step 5: Data Agent（通过 Task 调用）
9. 运行 Step 6: Git 备份

禁止仅显示本文档内容而不执行 workflow。

# Chapter Writing (Structured Workflow)

## 目标

- 以稳定流程产出可发布章节：优先使用 `正文/第{NNNN}章-{title_safe}.md`；细纲无标题时，自动生成标题并写回细纲，始终产出带标题的文件。
- 默认章节字数目标：2000-3000（用户或大纲明确覆盖时从其约定）。
- 保证审查、润色、数据回写完整闭环，避免"写完即丢上下文"。
- 输出直接可被后续章节消费的结构化数据：`review_metrics`、`summaries`、`chapter_meta`。

## 执行原则

1. 先校验输入完整性，再进入写作流程；缺关键输入时立即阻断。
2. 审查与数据回写是硬步骤，`--minimal` 只允许降级可选环节。
3. 参考资料严格按步骤按需加载，不一次性灌入全部文档。
4. Step 4 同时负责问题修复与风格转译（2B 已合并入 Step 4）。
5. 任一步失败优先做最小回滚，不重跑全流程。

## 模式定义

- `/webnovel-write`：Step 0 → 1 → 1-save → 2 → 3 → 4 → 5 → 6（单章）
- `/webnovel-write --minimal`：Step 0 → 1 → 1-save → 2 → 3（仅结构+角色维度，跳过精彩度）→ 4 → 5 → 6（单章）

最小产物：
- `正文/第{NNNN}章-{title_safe}.md`（始终带标题）
- `index.db.review_metrics` 新纪录（含 `overall_score`）
- `.webnovel/summaries/ch{NNNN}.md`
- `.webnovel/state.json` 的进度与 `chapter_meta` 更新

### 流程硬约束（禁止事项）

- **禁止并步**：不得将两个 Step 合并为一个动作执行（如同时做 2 和 3）。
- **禁止跳步**：不得跳过未被模式定义标记为可跳过的 Step。
- **禁止临时改名**：不得将 Step 的输出产物改写为非标准文件名或格式。
- **禁止自创模式**：`--minimal` 只允许按上方定义裁剪步骤，不允许自创混合模式、"半步"或"简化版"。
- **禁止源码探测**：脚本调用方式以本文档与 data-agent 文档中的命令示例为准，命令失败时查日志定位问题，不去翻源码学习调用方式。

## 引用加载等级（strict, lazy）

- L0：未进入对应步骤前，不加载任何参考文件。
- L1：每步仅加载该步"必读"文件。
- L2：仅在触发条件满足时加载"条件必读/可选"文件。

路径约定：
- `references/...` 相对当前 skill 目录。
- `../../references/...` 指向全局共享参考。

## References（逐文件引用清单）

### 根目录

- `references/context-guide.md`
  - 用途：Step 1 上下文搜集的 CLI 命令、文件清单、执行包 5 板块格式、章形/时间模式定义、红线校验。
  - 触发：Step 1 必读。
- `../../references/shared/core-constraints.md`
  - 用途：Step 2 写作硬约束（大纲即法律 / 设定即物理 / 发明需识别）。
  - 触发：Step 2 必读。
- `references/step-3-review-gate.md`
  - 用途：Step 3 内联审查的维度清单与评分规范。
  - 触发：Step 3 必读。
- `references/polish-guide.md`
  - 用途：Step 4 问题修复、风格转译（含原 2B 逻辑）、Anti-AI 与 No-Poison 规则。
  - 触发：Step 4 必读。
- `references/writing/typesetting.md`
  - 用途：Step 4 移动端阅读排版与发布前速查。
  - 触发：Step 4 必读。
- `../../references/genre-profiles.md`
  - 用途：Step 1（内置 Contract）按题材配置节奏阈值与钩子偏好。
  - 触发：Step 1 当 `state.project.genre` 已知时加载。

### writing（问题定向加读）

- `references/writing/combat-scenes.md`
  - 触发：战斗章或审查命中"战斗可读性/镜头混乱"。
- `references/writing/dialogue-writing.md`
  - 触发：审查命中 OOC、对话说明书化、对白辨识差。
- `references/writing/emotion-psychology.md`
  - 触发：情绪转折生硬、动机断层、共情弱。
- `references/writing/scene-description.md`
  - 触发：场景空泛、空间方位不清、切场突兀。
- `references/writing/desire-description.md`
  - 触发：主角目标弱、欲望驱动力不足。

## 工具策略（按需）

- `Read/Grep`：读取 `state.json`、大纲、章节正文与参考文件。
- `Bash`：运行 `extract_chapter_context.py`、`index_manager`、`workflow_manager`、`chapter_scan.py`。
- `Task`：调用 `data-agent`（Step 5）。
- 条件 Task：仅在关键章（弧末/卷末/高潮）时调用 `reader-pull-checker` 或 `high-point-checker`。

## 交互流程

### Step 0：预检与上下文最小加载

必须做：
- 解析真实书项目根（book project_root）：必须包含 `.webnovel/state.json`。
- 校验核心输入：`大纲/总纲.md`、`${SCRIPTS_DIR}/extract_chapter_context.py` 存在。
- 规范化变量：
  - `WORKSPACE_ROOT`：Claude Code 打开的工作区根目录（可能是书项目的父目录，例如 `D:\wk\xiaoshuo`）
  - `PROJECT_ROOT`：真实书项目根目录（必须包含 `.webnovel/state.json`，例如 `D:\wk\xiaoshuo\凡人资本论`）
  - `SKILL_ROOT`：skill 所在目录（`${WORKSPACE_ROOT}/.claude/skills/write-chapter`，指向项目级，references 可定制）
  - `SCRIPTS_DIR`：脚本目录（`${WORKSPACE_ROOT}/.claude/scripts`）
  - `chapter_num`：当前章号（整数）
  - `chapter_padded`：四位章号（如 `0007`）

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="${WORKSPACE_ROOT}/.claude/scripts"
export SKILL_ROOT="${WORKSPACE_ROOT}/.claude/skills/write-chapter"

echo "【项目级 skill 已激活】SKILL_ROOT=${SKILL_ROOT}"

python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

**硬门槛**：`preflight` 必须成功。它统一校验 `SCRIPTS_DIR`、`webnovel.py`、`extract_chapter_context.py` 和解析出的 `PROJECT_ROOT`。任一失败都立即阻断。

输出：
- "已就绪输入"与"缺失输入"清单；缺失则阻断并提示先补齐。

---

### Step 1：上下文搜集与执行包组装（主 Agent 内联）

执行前必须加载：
```bash
cat "${SKILL_ROOT}/references/context-guide.md"
```

按 `context-guide.md` 中的指引依次执行：

1. **运行 CLI 命令**：context 快照 + extract-context + 按需查询（章节模式/实体）
2. **读取文件**：细纲、state.json、上章正文、上上章末尾 300 字、上章摘要、CLAUDE.md、时间线表（可选）
3. **分析判定**：承接上章、场景状态、伏笔筛选、角色推断
4. **组装 5 板块执行包**（含核心三问、CLAUDE.md 约束注入）
5. **红线校验**：5 项自检通过后输出

硬要求：
- 若 `state.json` 或大纲不可用，立即阻断并返回缺失项
- 输出必须是简洁的 5 板块执行包：
  - 板块1：本章写什么（核心三问、章形、时间模式、硬/中约束、核心冲突、章末画面）
  - 板块2：从哪里接上（场景快照、承接方式、断裂禁止）
  - 板块3：出场角色（状态、动机、情绪底色、红线）
  - 板块4：不可变事实（大纲/设定/承接事实、到期伏笔、感情线/道具约束）
  - 板块5：禁止事项（不超过 9 条）
- **钩子承接规则**：
  - 剧情承诺兑现（硬性）：上章钩子承诺的事件/信息必须在本章落地
  - 意象传承：禁止原词复用；若 `active_metaphors` 中该意象已用 ≥2 次，写入禁止事项
- 合同与任务书冲突时，以大纲与设定约束更严格者为准

### Step 1-save：执行包存档（Step 1 完成后立即执行）

> 将执行包写入文件，供事后审查。失败不阻断后续流程。

用 Write 工具写入：
- 路径：`${PROJECT_ROOT}/.webnovel/tmp/execution_pack_ch{chapter_padded}.md`
- 文件头追加：`<!-- 生成时间：{timestamp}，章节：第{chapter_num}章 -->`

写入后输出：`✅ 执行包已存档：.webnovel/tmp/execution_pack_ch{chapter_padded}.md`


---

### Step 2：正文起草

执行前必须加载：
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

**起草前必须输出**（硬要求，缺失则阻断起草）：

```
[写作红线确认]

1. 感情线阶段：{阶段名}
   本章禁止行为：{列出 Step 1 执行包中的禁止清单}
   ✅ 已确认执行包中无违规行为

2. 伏笔保护：
   本章受保护伏笔：{列出}
   ✅ 已确认执行包中无泄露风险

3. 道具一致性：
   本章涉及道具：{列出}
   ✅ 已确认与注册表一致

4. 【硬】约束确认：
   本章【硬】必须完成：① xxx  ② xxx
   ✅ 已确认全部纳入

确认完成，开始起草正文。
```

硬要求：
- **遵循细纲【硬】约束**：任务书中的【硬】约束事件必须在本章完成，不可删除、不可替换、不可偏离主线
- **尊重细纲【中】约束**：主线方向必须保持，实现方式可在合理范围内发挥。执行包中【中】约束带有编号和信息载体指示，必须在正文中体现
- **参考细纲【软】约束**：可按写作需要灵活调整或删除
- **章末最后画面**：若执行包板块1包含"章末最后画面"，正文必须以该画面收束，**禁止在最后画面之后追加独处感悟、内心总结、环境收束等段落**。章节的最后一段就是那个画面。若执行包无此项，章节停在故事的自然停歇处
- 只输出纯正文到章节正文文件；**标题来源优先级**：①详细大纲已有章节名 → 直接使用；②大纲无标题 → 根据本章核心事件/情绪自动生成 2-4 字标题，将生成的标题**写回细纲对应行**，并用于文件名和章节标题行。统一使用 `正文/第{chapter_padded}章-{title_safe}.md`，禁止输出无标题文件（`正文/第{chapter_padded}章.md` 格式不再使用）。
- 章节标题行格式：`# 第{chapter_padded}章 {title}`（标题与章号之间空一格）。
- 默认按 2000-3000 字执行；若大纲为关键战斗章/高潮章/卷末章或用户明确指定，则按大纲/用户优先，不以字数上限为由压缩高潮场景。
- 禁止占位符正文（如 `[TODO]`、`[待补充]`）。
- 保留承接关系：若上章有明确钩子，本章必须回应（可部分兑现）。

中文思维写作约束（硬规则）：
- **禁止"先英后中"**：不得先用英文工程化骨架（如 ABCDE 分段、Summary/Conclusion 框架）组织内容，再翻译成中文。
- **中文叙事单元优先**：以"动作、反应、代价、情绪、场景、关系位移"为基本叙事单元，不使用英文结构标签驱动正文生成。
- **禁止英文结论话术**：正文、审查说明、润色说明、变更摘要、最终报告中不得出现 Overall / PASS / FAIL / Summary / Conclusion 等英文结论标题。
- **英文仅限机器标识**：CLI flag（`--fast`）、checker id（`consistency-checker`）、DB 字段名（`anti_ai_force_check`）、JSON 键名等不可改的接口名保持英文，其余一律使用简体中文。

**禁止流水账**：不得出现"谁做了什么、谁又做了什么、再做了什么"的纯事件罗列。每段必须服务于本章核心目标——在信息增量、情感增量、悬念增量中至少交付一种。

**场景质感清单（Soft — 每个情感/关键场景写前必须填）**：

每个情感场景或关键场景（建议选2-3个）起草前必须明确以下三点，填入执行包的"章节节拍"：

```
场景N（描述）：
- 【感官锚点】这个场景里，读者闭上眼睛能"看见"的画面是什么？（声音/气味/触感/温度等具体细节）
- 【情感弧度】这段情绪怎么爬的？（起点→阻力→峰值→余韵，任何省略都要有理由）
- 【读者记住的那一句】写完后，这段最让人记住的是哪一句？（没有的话说明场景没写透）
```

**情感展示建议（Soft）**：禁止直接用情绪词贴标签，通过生理反应+动作+感官细节表现：
```
✗ 她心头一暖，眼眶有些发热。
✓ 她低下头，手指攥紧了袖口，好一会儿才松开。
✗ 苏绾音心里又酸又软。
✓ 她站在原地，听见自己的心跳声，一下一下，撞在胸腔里。
```

输出：
- 章节草稿（进入 Step 3）。

### Step 3：内联审查 + 机械扫描（主 Agent 执行，无需子 Agent）

> **2026-04-25 变更**：审查逻辑从独立子 Agent 合并回主 Agent。主 Agent 在 Step 2 起草后**已持有完整章节和上下文**，无需再开子 Agent 重新加载相同数据。条件审查器（reader-pull-checker / high-point-checker）仍在关键章时通过 Task 调用。

执行前加载：
```bash
cat "${SKILL_ROOT}/references/step-3-review-gate.md"
```

#### Part A：主 Agent 内联审查（按审查清单逐项执行）

主 Agent 以审查者视角重新审视刚写完的章节，按以下维度输出结构化 JSON：

**维度1：设定一致性（原 consistency-checker）**
- 战力一致性：境界/能力是否与 state.json 一致
- 地点一致性：移动路径是否合法
- 时间线一致性：时间锚点是否连贯、有无回跳/倒计时错误
- 叙事边界：有无第四面墙突破（ch编号/元叙事词汇）

**维度2：叙事连贯性（原 continuity-checker）**
- 场景转换流畅度（A/B/C/F 四级）
- 情节线连贯（引入未回收/无铺垫回收/遗忘线索）
- 伏笔管理（短期/中期/长期）
- 大纲一致性

**维度3：角色一致性（原 ooc-checker）**
- 角色行为与设定档案是否一致
- 对话风格是否匹配
- 角色成长 vs OOC 区分

**维度4：精彩度（原 reader-quality-checker，`--minimal` 模式跳过此维度）**
- 逐场景三增量检查（信息/情感/悬念）
- 流水账检测（300字+场景且三增量均空）
- 高潮质量（有结论无过程扣分）

**维度5：节奏检查（章号 ≥ 10 时执行，否则跳过）**
- Strand Weave 平衡：Quest/Fire/Constellation 占比
- 连续同线检测

**审查输出格式**：

```
[内联审查报告]

维度1 设定一致性：{分数}/100
- issues: [...]

维度2 叙事连贯性：{分数}/100
- issues: [...]

维度3 角色一致性：{分数}/100
- issues: [...]

维度4 精彩度：{分数}/100
- issues: [...]

维度5 节奏：{分数}/100 （或"跳过"）
- issues: [...]

综合评分：{加权平均}
严重问题：{N} 个
高优先级：{N} 个
```

**硬性检查（自动化，必做）**：

| 检查项 | 方法 | 不通过则 |
|--------|------|---------|
| 字数是否达标（2000-3000中文字符） | `python -X utf8 -c "import re;print(len(re.findall(r'[\u4e00-\u9fff]', open('正文/第{NNNN}章-xxx.md').read())))"` | 不足则修 |
| 是否出现"chXX"章节号引用 | Grep 扫描 | 必须修 |
| 是否出现 OOC 关键词 | 黑名单 Grep | 必须修 |

#### Part B：机械扫描（必须用 Bash 执行，禁止跳过）

```bash
python3 "${SCRIPTS_DIR}/chapter_scan.py" "${PROJECT_ROOT}/正文/第${chapter_padded}章-${title_safe}.md"
```

**硬要求**：
- **必须用 Bash 工具执行上面这条命令**，不得用 grep、不得自行编写替代扫描、不得跳过
- 脚本输出包含 ABCD 四层检查结果，是 Step 4 润色的**强制输入**
- 将脚本的完整输出保存，在 Step 4 开头作为"扫描报告"引用
- 若脚本执行失败，记录警告并继续进入 Step 4

#### Part C：条件审查器（仅关键章触发，通过 Task 调用）

- `reader-pull-checker`：**仅在以下场景启用**（日常章节不跑）
  - 弧末章（细纲标注的弧最后一章）
  - 卷末章
  - 用户显式要求"追读力审查"
- `high-point-checker`：当满足任一条件时启用
  - 关键章/高潮章/卷末章
  - 正文出现战斗、反杀、打脸、身份揭露、大反转等高光信号

条件审查器通过 Task 并行调用，返回后合并入审查报告。

#### Part D：审查指标落库（必做）

将审查结果写入 `review_metrics.json` 并落库：

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 字段约束：
```json
{
  "start_chapter": 100,
  "end_chapter": 100,
  "overall_score": 85.0,
  "dimension_scores": {"设定一致性": 8.0, "连贯性": 9.0, "人物塑造": 8.2, "精彩度": 8.5, "节奏控制": 7.8},
  "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
  "critical_issues": ["问题描述"],
  "report_file": "审查报告/第100-100章审查报告.md",
  "notes": "selected_checkers=inline; 扩展信息压成单行文本写入此字段"
}
```

**进入 Step 4 的闸门**：
- `overall_score` 已生成
- `save-review-metrics` 已成功
- **时间线闸门**：若存在 `TIMELINE_ISSUE` 且 `severity >= high`，必须先修复再进入 Step 4
- **第四面墙闸门**：若存在 `FOURTH_WALL_BREAK` 且 `severity >= high`，必须先修复再进入 Step 4

### Step 4：润色（问题修复 + 风格转译，1 轮）

> **2026-04-25 变更**：润色从最多 2 轮改为 1 轮。实测第 2 轮改动极少但要付出完整重读代价，性价比过低。未修复项记入变更摘要。

执行前必须加载：
```bash
cat "${SKILL_ROOT}/references/polish-guide.md"
cat "${SKILL_ROOT}/references/writing/typesetting.md"
```

**润色 1 轮完成以下全部任务**：
1. **保护【硬】约束检查**：标记【硬】约束事件位置，润色时绝对禁止删除
2. **引用 Step 3 Part B 扫描报告**：ABC 层为强制修改清单，D 层为建议修改
3. 修复 `critical`（必须）
4. 修复 `high`（不能修复则记录 deviation）
5. 处理 `medium/low`（按收益择优）
6. 按扫描报告逐项修复：A层短语重复 → B层句式词 → C层句式模式 → D层注水问题
7. 执行风格转译（网文化，参见 polish-guide.md § 风格转译节）
8. **Step 4-ext: 章末截断检查**
   - 若执行包板块1指定了`章末最后画面`：确认正文以该画面收束
   - **DAILY_CLOSE 自动检测**：扫描词（入睡/躺下/帐顶/未眠/来日方长等），检测到则修复为截断式结尾
9. 执行 Anti-AI 与 No-Poison 全文终检（必须输出 `anti_ai_force_check: pass/fail`）
10. **【硬】约束复核**：润色后检查所有【硬】约束事件仍完整存在

输出：
- 润色后正文（覆盖章节文件）
- 变更摘要（至少含：修复项、保留项、deviation、`anti_ai_force_check`、遗留问题）

### Step 5：Data Agent（状态与索引回写）

使用 Task 调用 `data-agent`，参数：
- `chapter`
- `chapter_file` 必须传入实际章节文件路径；统一传 `正文/第{chapter_padded}章-{title_safe}.md`
- `review_score=Step 3 overall_score`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

Data Agent 子步骤（全部执行）：
- A. 加载上下文
- B. AI 实体提取
- C. 实体消歧
- D. 写入 state/index（含 chapter_meta、recent_openings、recent_endings、narrative_state 回写，一次性完成）
- E. 写入章节摘要
- F. AI 场景切片

Step 5 失败隔离规则：
- 若 A-E 失败（state/index/summary 写入失败）：仅重跑 Step 5，不回滚已通过的 Step 1-4。
- 禁止因子步骤失败而重跑整个写作链。

执行后检查（最小白名单）：
- `.webnovel/state.json`
- `.webnovel/index.db`
- `.webnovel/summaries/ch{chapter_padded}.md`
- `.webnovel/observability/data_agent_timing.jsonl`（观测日志）

性能要求：
- 读取 timing 日志最近一条；
- 当 `TOTAL > 30000ms` 时，输出最慢 2-3 个环节与原因说明。

### Step 6：Git 备份（可失败但需说明）

```bash
git add .
git -c i18n.commitEncoding=UTF-8 commit -m "第{chapter_num}章: {title}"
```

规则：
- 提交时机：验证、回写、清理全部完成后最后执行。
- 提交信息默认中文，格式：`第{chapter_num}章: {title}`。
- 若 commit 失败，必须给出失败原因与未提交文件范围。
