# Step 3 Review Gate

## 调用约束（硬规则）

- 必须使用 `Task` 调用审查 subagent，禁止主流程直接内联"自审结论"。
- 审查任务可并行发起，必须在全部返回后统一聚合。
- `overall_score` 必须来自聚合结果，不可主观估分。
- 单章写作场景下，统一传入：`{chapter, chapter_file, project_root}`。

## 合并检查器说明（Token 优化）

为减少 Task 启动开销，核心检查器已合并为两个联合 agent：

| 联合 Agent | 包含检查器 | 执行条件 |
|------------|-----------|---------|
| `structural-checker` | consistency-checker + continuity-checker | 始终执行 |
| `character-rhythm-checker` | ooc-checker + pacing-checker | 始终执行（pacing 在 agent 内按章号条件触发） |

每个联合 agent 输出两份独立 JSON（以 `## {checker-name} 结果` 分隔），聚合时按分隔符拆分处理。

## 审查路由模式

- 标准/`--fast`：`auto` 路由（核心 2 个联合 agent + 条件命中的独立审查器）。
- `--minimal`：只跑 2 个核心联合 agent（不启用 reader-quality-checker 及条件审查器）。

核心审查器（始终执行，共 3 次 Task）：
- `structural-checker`（= consistency-checker + continuity-checker）
- `character-rhythm-checker`（= ooc-checker + pacing-checker，pacing 在 agent 内按条件执行）
- `reader-quality-checker`（= 精彩度检查：场景三增量/流水账检测/高潮质量评估）

条件审查器（仅在特定场景启用，共 0-2 次 Task）：
- `reader-pull-checker`
- `high-point-checker`

## Auto 路由判定信号

输入信号来源：
1. 大纲标签（关键章/高潮章/卷末章/弧末章）。
2. 本章正文（战斗/反转/高光等信号）。
3. 用户显式要求。

路由规则：
- `reader-pull-checker`：**仅在以下场景启用**（日常章节不跑）
  - 弧末章（细纲标注的弧最后一章）；
  - 卷末章；
  - 用户显式要求"追读力审查"。
- `high-point-checker`：当满足任一条件时启用
  - 关键章/高潮章/卷末章；
  - 正文出现战斗、反杀、打脸、身份揭露、大反转等高光信号。

> `pacing-checker` 已内置于 `character-rhythm-checker`，由其内部按章号（≥10）和 strand_tracker 历史自动触发，不再作为独立条件审查器。

## Task 调用模板（示意）

```text
# 核心联合 agent（始终并行发起，共 3 个 Task）
selected = ["structural-checker", "character-rhythm-checker", "reader-quality-checker"]

# 条件独立审查器（auto 路由追加）
if mode != "minimal":
  if trigger_reader_pull: selected.append("reader-pull-checker")
  if trigger_high_point:  selected.append("high-point-checker")

parallel Task(agent, {chapter, chapter_file, project_root}) for agent in selected
```

## 联合 Agent 输出聚合规则

联合 agent 输出格式（以 `structural-checker` 为例）：
```
## consistency-checker 结果
{ ...标准 schema JSON... }

## continuity-checker 结果
{ ...标准 schema JSON... }
```

聚合时：
1. 按 `## {checker-name} 结果` 分隔符拆分，提取各子 JSON。
2. `skipped: true` 的子结果（如 pacing 未触发时）跳过 issues 统计，在 `notes` 中记录。
3. 其余子结果与独立 agent 结果统一处理，合并 `issues`、计算 `dimension_scores`、取加权平均 `overall_score`。

## 输出契约（统一）

每个 checker 返回值必须遵循 `/Users/dongliang04/Documents/个人/小说/女频/.claude/references/checker-output-schema.md`：
- 必含：`agent`、`chapter`、`overall_score`、`pass`、`issues`、`metrics`、`summary`
- 允许扩展字段（如 `hard_violations`、`soft_suggestions`），但不得替代必填字段

聚合输出最小字段：
- `chapter`（单章）
- `start_chapter`、`end_chapter`（单章时二者都等于 `chapter`）
- `selected_checkers`
- `overall_score`
- `severity_counts`
- `critical_issues`
- `issues`（扁平化聚合）
- `dimension_scores`（按已启用 checker 计算）

## 汇总输出模板

```text
审查汇总 - 第 {chapter_num} 章
- 已启用审查器: {list}
- 严重问题: {N} 个
- 高优先级问题: {N} 个
- 综合评分: {score}
- 可进入润色: {是/否}
```

## 审查指标落库（必做）

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 文件字段约束（当前工作流约定只传以下字段）：
- `start_chapter`（int）、`end_chapter`（int）：单章时二者相等
- `overall_score`（float）：必填
- `dimension_scores`（Dict[str, float]）：按已启用 checker 计算
- `severity_counts`（Dict[str, int]）：键为 critical / high / medium / low
- `critical_issues`（List[str]）
- `report_file`（str）
- `notes`（str）：在当前执行契约中必须是单个字符串；`selected_checkers`、`timeline_gate`、`anti_ai_force_check` 等扩展信息统一压成单行文本写入此字段，不得作为独立顶层键传入
- 当前工作流不额外传入其它顶层字段；脚本侧未在此处做新增硬校验

## 审查清单（逐项执行）

### 第一层：硬性检查（自动化，必做）

执行完所有审查 Task 后，主 agent 必须逐项确认：

| 检查项 | 方法 | 不通过则 |
|--------|------|---------|
| 字数是否达标（1800-3000中文字符，高潮章按需超出不追究） | `python -X utf8 -c "import re;print(len(re.findall(r'[\u4e00-\u9fff]', open(' 正文/第0032章-xxx.md').read())))"` | 不足则修 |
| 是否出现"chXX"章节号引用 | `grep -E "ch[0-9]" 正文/` | 必须修 |
| 是否出现 OOC 关键词（"问了她就说"等） | 黑名单 grep | 必须修 |

### 第二层：内容审查（逐项打勾）

#### A. 场景密度
- [ ] 本章是否有 ≥3 个具体场景（时间+地点+人物+动作）
- [ ] 每个场景是否有环境细节（不是空转）
- [ ] 场景之间是否有合理的时间/空间过渡

#### B. 情节推进
- [ ] 本章是否有明确的情节推进（不是原地踏步）
- [ ] 是否有上章钩子的承接或回应
- [ ] 是否有下章钩子的铺垫或悬念

#### C. 人物行为
- [ ] 苏绾音的行为是否符合当前 trust/阶段设定？（参照 CLAUDE.md 阶段表）
- [ ] 谢沉渊的行为是否与他的人设一致？
- [ ] 反派是否有具体的行动而非"筹划中"一句话带过？

#### D. 对话质量
- [ ] 对话是否推进情节或揭示信息（而非寒暄）
- [ ] 是否没有连续出现3轮以上的"他问/她答"？
- [ ] 对话是否符合人物身份和关系？

#### E. 重复检查
- [ ] 同一句话/意象是否在某章内重复出现超过2次？
- [ ] 相邻章节是否有重复的场景描写（如两个"夜深了"场景）？

#### F. 读者收获（核心检查）
- [ ] 读完本章，读者带走的最大感受是什么？**三选一**：
  - 信息增量："原来如此"/"比我想的更危险"
  - 情感增量："这个感觉真好"/"好甜"
  - 悬念增量："好想看下一章"/"她会怎么做"
- [ ] 若三选一都说不清，说明是流水账（必须修复）
- [ ] 有没有整段/整章是"谁做了什么、谁又做了什么"的纯事件罗列？

### 第三层：细纲对照

- [ ] 本章【硬】约束是否完成？
- [ ] 本章【中】约束是否偏离？
- [ ] 是否有细纲未提及的重要情节/转折？

### 第四层：时间线推进检查

> 读取前3章的 summary（`^time:` / `^location:` 字段），检查本章是否触发"禁止模式"。

**逐项打勾**（任一项命中，且连续3+章出现2种模式，则标记为高优先级问题）：
- [ ] 本章与前2章是否存在同一时段（清晨/午后/夜间）重复开头？（每日开机检查）
- [ ] 本章地点是否与前3章高度重复（同一室内为主）？（地点锁死检查）
- [ ] 是否连续3+章都是"N日后"机械推进无跳跃？（机械日进检查）

**时间跳跃锚点**（满足任一即通过时间线检查）：
- [ ] 本章有跨天跳跃（"三日后"/"数日后"/"又过X日"）
- [ ] 本章为多地点场景（非单一室内）
- [ ] 本章与上章为同一时刻的同天不同视角

**修复建议**（若命中禁止模式）：
- 每日开机 → 下章改用事件/对话触发开场，或跳跃到下个时段
- 地点锁死 → 加入外出/访客/突发场景切换
- 机械日进 → 压缩过渡段，或改为同天多视角并置

### 审查报告模板

```text
## {chapter_num} 章审查报告

**字数**: {count} 字 [达标/不足（需修）/充足（高潮章可超出）]

**硬性检查**:
- [ ] 无 "chXX" 引用
- [ ] 无 OOC 关键词

**场景密度**: {n} 个具体场景
- [通过/不足]

**情节推进**:
- [通过/不足] — {简要说明}

**人物行为**:
- 苏绾音: [符合/不符合] 阶段设定（{phase}）
- 谢沉渊: [符合/不符合] 人设
- 反派: [有具体行动/只有概述]

**对话质量**: [通过/不足]

**重复检查**:
- [有/无] 重复意象
- [有/无] 相邻章重复场景

**读者收获**:
- [信息增量/情感增量/悬念增量] — {一句话描述读者带走什么}
- [有/无] 流水账段落

**细纲对照**:
- [硬约束]: [完成/未完成] — {描述}
- [中约束]: [符合/偏离]

**问题汇总**:
- Critical: {n}
- High: {n}
- Medium: {n}
- Low: {n}

**结论**: [可进入润色/需修复后重审]
```

## 进入 Step 4 前闸门

- `overall_score` 已生成。
- `save-review-metrics` 已成功。
- 审查报告中的 `issues`、`severity_counts` 可被 Step 4 直接消费。
- **时间线闸门（新增）**：若存在 `TIMELINE_ISSUE` 且 `severity >= high`，禁止进入 Step 4/5，必须先修复。
- **第四面墙闸门（新增）**：若存在 `FOURTH_WALL_BREAK` 且 `severity >= high`，禁止进入 Step 4/5，必须先修复。

### 时间线闸门规则

**Hard Block（必须修复才能继续）**：
- `TIMELINE_ISSUE` + `severity = critical`（倒计时算术错误）
- `TIMELINE_ISSUE` + `severity = high`（事件先后矛盾/年龄冲突/时间回跳/大跨度无过渡）

**Soft Warning（建议修复但可继续）**：
- `TIMELINE_ISSUE` + `severity = medium`（时间锚点缺失）
- `TIMELINE_ISSUE` + `severity = low`（轻微时间模糊）

**闸门判定逻辑**：
```text
timeline_issues = filter(issues, type="TIMELINE_ISSUE")
critical_timeline = filter(timeline_issues, severity in ["critical", "high"])

if len(critical_timeline) > 0:
    BLOCK: "存在 {len(critical_timeline)} 个严重时间线问题，必须修复后才能进入润色步骤"
    for issue in critical_timeline:
        print(f"- 第{issue.chapter}章: {issue.description}")
    return BLOCKED
else:
    通过: "时间线检查通过"
```

**修复指引**：
- 倒计时错误 → 修正倒计时推进，确保 D-N → D-(N-1) 连续
- 时间回跳 → 添加闪回标记，或调整时间锚点
- 大跨度无过渡 → 添加时间过渡句/段，或插入过渡章
- 事件先后矛盾 → 调整事件发生顺序或添加时间跳跃说明

### 第四面墙闸门规则

**Hard Block（必须修复才能继续）**：
- `FOURTH_WALL_BREAK` + `severity = high`（正文中出现章节编号如"ch44"、"ch47"等）
- `FOURTH_WALL_BREAK` + `severity = critical`（角色道具中出现元小说引用，如"第3章"、"上一章"等）

**修复指引**：
- 章节编号 → 改为叙事内时间描述（如"四月中"、"赏花宴前"、"今晨"、"昨日"）
- 元小说引用 → 改为角色视角的自然记录（如"上月替嫁坦白"、"赏花宴上应对从容"）
- 叙述者提及"读者"、"本章" → 改为角色内心独白或场景动作
