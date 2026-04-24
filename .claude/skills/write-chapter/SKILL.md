---
name: write-chapter
description: Writes webnovel chapters (default 1800-3000 words). Use when the user asks to write a chapter or runs /webnovel-write. Runs context, drafting, review, polish, and data extraction.
allowed-tools: Read Write Edit Grep Bash Task
---

# 执行指令

当此 skill 被调用时，必须按以下步骤执行，不能仅显示文档：

1. 提取章节号参数（如 "第16章" → 16）
2. 运行 Step 1: Context Agent（通过 Task 调用）
3. 运行 Step 1-save: 执行包存档（Write 写入 tmp 目录）
4. 运行 Step 1.5: 项目约束注入（主 agent 从 CLAUDE.md 提取本章适用约束）
5. 运行 Step 2A: 正文起草（使用 Bash 或 Read/Write）
6. 运行 Step 3: 审查（通过 Task 调用 structural-checker 等）
7. 运行 Step 3.5: 机械扫描（必须用 Bash 执行 chapter_scan.py）
8. 运行 Step 4: 润色（消费 Step 3 审查报告 + Step 3.5 扫描结果）
9. 运行 Step 5: Data Agent（通过 Task 调用）
10. 运行 Step 6: Git 备份

禁止仅显示本文档内容而不执行 workflow。

# Chapter Writing (Structured Workflow)

## 目标

- 以稳定流程产出可发布章节：优先使用 `正文/第{NNNN}章-{title_safe}.md`；细纲无标题时，自动生成标题并写回细纲，始终产出带标题的文件。
- 默认章节字数目标：1800-3000（用户或大纲明确覆盖时从其约定）。
- 保证审查、润色、数据回写完整闭环，避免“写完即丢上下文”。
- 输出直接可被后续章节消费的结构化数据：`review_metrics`、`summaries`、`chapter_meta`。

## 执行原则

1. 先校验输入完整性，再进入写作流程；缺关键输入时立即阻断。
2. 审查与数据回写是硬步骤，`--fast`/`--minimal` 只允许降级可选环节。
3. 参考资料严格按步骤按需加载，不一次性灌入全部文档。
4. Step 4 同时负责问题修复与风格转译（2B 已合并入 Step 4）。
5. 任一步失败优先做最小回滚，不重跑全流程。

## 模式定义

- `/webnovel-write`：Step 1 → 1.5 → 2A → 3 → 4 → 5 → 6（单章）
- `/webnovel-write --minimal`：Step 1 → 1.5 → 2A → 3（仅核心2个联合审查器）→ 4 → 5 → 6（单章）

> Step 2B（独立风格转译）已合并入 Step 4，Step 4 在修复审查问题的同时完成风格转译，减少一次全文重写。

最小产物：
- `正文/第{NNNN}章-{title_safe}.md`（始终带标题）
- `index.db.review_metrics` 新纪录（含 `overall_score`）
- `.webnovel/summaries/ch{NNNN}.md`
- `.webnovel/state.json` 的进度与 `chapter_meta` 更新

### 流程硬约束（禁止事项）

- **禁止并步**：不得将两个 Step 合并为一个动作执行（如同时做 2A 和 3）。
- **禁止跳步**：不得跳过未被模式定义标记为可跳过的 Step。
- **禁止临时改名**：不得将 Step 的输出产物改写为非标准文件名或格式。
- **禁止自创模式**：`--minimal` 只允许按上方定义裁剪步骤，不允许自创混合模式、"半步"或"简化版"。
- **禁止自审替代**：Step 3 审查必须由 Task 子代理执行，主流程不得内联伪造审查结论。
- **禁止源码探测**：脚本调用方式以本文档与 data-agent 文档中的命令示例为准，命令失败时查日志定位问题，不去翻源码学习调用方式。

## 引用加载等级（strict, lazy）

- L0：未进入对应步骤前，不加载任何参考文件。
- L1：每步仅加载该步“必读”文件。
- L2：仅在触发条件满足时加载“条件必读/可选”文件。

路径约定：
- `references/...` 相对当前 skill 目录。
- `../../references/...` 指向全局共享参考。

## References（逐文件引用清单）

### 根目录

- `references/step-3-review-gate.md`
  - 用途：Step 3 审查调用模板、汇总格式、落库 JSON 规范。
  - 触发：Step 3 必读。
- `../../references/shared/core-constraints.md`
  - 用途：Step 2A 写作硬约束（大纲即法律 / 设定即物理 / 发明需识别）。
  - 触发：Step 2A 必读。
- `references/polish-guide.md`
  - 用途：Step 4 问题修复、风格转译（含原 2B 逻辑）、Anti-AI 与 No-Poison 规则。
  - 触发：Step 4 必读。
- `references/writing/typesetting.md`
  - 用途：Step 4 移动端阅读排版与发布前速查。
  - 触发：Step 4 必读。
- `../../references/genre-profiles.md`
  - 用途：Step 1（内置 Contract）按题材配置节奏阈值与钩子偏好。
  - 触发：Step 1 当 `state.project.genre` 已知时加载。
- `references/writing/genre-hook-payoff-library.md`
  - 用途：电竞/直播文/克苏鲁的钩子与微兑现快速库。
  - 触发：Step 1 题材命中 `esports/livestream/cosmic-horror` 时必读。

### writing（问题定向加读）

- `references/writing/combat-scenes.md`
  - 触发：战斗章或审查命中“战斗可读性/镜头混乱”。
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
- `Bash`：运行 `extract_chapter_context.py`、`index_manager`、`workflow_manager`。
- `Task`：调用 `context-agent`、审查 subagent、`data-agent` 并行执行。

## 交互流程

### Step 0：预检与上下文最小加载

必须做：
- 解析真实书项目根（book project_root）：必须包含 `.webnovel/state.json`。
- 校验核心输入：`大纲/总纲.md`、`/Users/dongliang04/Documents/个人/小说/女频/.claude/scripts/extract_chapter_context.py` 存在。
- 规范化变量：
  - `WORKSPACE_ROOT`：Claude Code 打开的工作区根目录（可能是书项目的父目录，例如 `D:\wk\xiaoshuo`）
  - `PROJECT_ROOT`：真实书项目根目录（必须包含 `.webnovel/state.json`，例如 `D:\wk\xiaoshuo\凡人资本论`）
  - `SKILL_ROOT`：skill 所在目录（固定 `/Users/dongliang04/Documents/个人/小说/女频/.claude/skills/write-chapter`，指向项目级，references 可定制）
  - `SCRIPTS_DIR`：脚本目录（固定 `/Users/dongliang04/Documents/个人/小说/女频/.claude/scripts`）
  - `chapter_num`：当前章号（整数）
  - `chapter_padded`：四位章号（如 `0007`）

环境设置（bash 命令执行前）：
```bash
export WORKSPACE_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
export SCRIPTS_DIR="/Users/dongliang04/Documents/个人/小说/女频/.claude/scripts"
export SKILL_ROOT="/Users/dongliang04/Documents/个人/小说/女频/.claude/skills/write-chapter"

echo "【项目级 skill 已激活】SKILL_ROOT=${SKILL_ROOT}"

python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"
```

**硬门槛**：`preflight` 必须成功。它统一校验 `SCRIPTS_DIR`、`webnovel.py`、`extract_chapter_context.py` 和解析出的 `PROJECT_ROOT`。任一失败都立即阻断。

输出：
- “已就绪输入”与“缺失输入”清单；缺失则阻断并提示先补齐。

### Step 0.5：工作流断点记录（best-effort，不阻断）

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-task --command webnovel-write --chapter {chapter_num} || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 0.5" --step-name "Core Question Planning" || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 0.5" --artifacts '{"ok":true}' || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow start-step --step-id "Step 1" --step-name "Context Agent" || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-step --step-id "Step 1" --artifacts '{"ok":true}' || true
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" workflow complete-task --artifacts '{"ok":true}' || true
```

要求：
- `--step-id` 仅允许：`Step 1` / `Step 2A` / `Step 2B` / `Step 3` / `Step 3.5` / `Step 4` / `Step 5` / `Step 6`。
- 任何记录失败只记警告，不阻断写作。
- 每个 Step 执行结束后，同样需要 `complete-step`（失败不阻断）。

### Step 0.5（前置）：确定本章核心问题

**必须在调用 context-agent 之前完成。**

主 agent 先读取细纲本章条目，然后回答：

```
【本章核心问题规划】

1. 本章的核心问题是什么？（一句话）
   → 这个事件逼谁做出什么选择？

2. 本章必须让读者知道什么？（信息增量）
   → 读完本章，读者知道了什么之前不知道的？

3. 本章会引发什么新问题？（悬念增量）
   → 读完本章，读者最想知道什么？

如果这三个问题回答不了，说明这章没有实质内容：
- 要么：合并到其他章
- 要么：重新想清楚这章的写作方向
- 要么：与用户确认这章是否需要写
```

**输出：** 将这三个问题及答案写入执行包的任务书第一行。

---

### Step 1：Context Agent（内置 Context Contract，生成直写执行包）

**调用前**：从 `state.json` 读取 `protagonist_state.narrative_state`，提取以下字段注入 Task prompt：

```bash
python3 -c "
import json, sys
with open('${PROJECT_ROOT}/.webnovel/state.json', encoding='utf-8') as f:
    s = json.load(f)
ns = s.get('protagonist_state', {}).get('narrative_state', {})
print('【项目级叙事状态注入 - 必须写入执行包】')
print(f'感情线当前阶段: {ns.get(\"emotion_line_phase\", \"未知\")}')
print(f'反派状态: {json.dumps(ns.get(\"antagonist_status\", {}), ensure_ascii=False)}')
print(f'已揭示事实: {ns.get(\"known_truths\", [])}')
pending = [m for m in ns.get('volume_milestones', {}).get('items', []) if not m.get('done')]
print(f'未完成里程碑: {[m[\"id\"]+\": \"+m[\"desc\"] for m in pending[:5]]}')
# 意象使用追踪（防重复）
metaphors = ns.get('active_metaphors', {})
if metaphors:
    print('【意象使用追踪 - 写作时必须遵守】')
    for name, info in metaphors.items():
        count = info.get('usage_count', 0)
        status = info.get('status', '')
        rule = info.get('next_use_rule', '')
        print(f'  {name}: 已用{count}次（ch{info.get(\"used_chapters\", [])}）| 状态: {status} | 规则: {rule}')
"
```

使用 Task 调用 `context-agent`，参数：
- `chapter`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`
- 上方脚本输出的叙事状态文本，作为额外 prompt 追加到 Task 调用中

硬要求：
- 若 `state` 或大纲不可用，立即阻断并返回缺失项。
- 输出必须是简洁的 5 板块执行包：
  - 板块1：本章写什么（核心任务、硬/中约束、核心冲突、局面变化）
  - 板块2：从哪里接上（上章结束状态、承接逻辑）
  - 板块3：出场角色（状态、动机、情绪底色、红线）
  - 板块4：不可变事实（大纲/设定/承接事实、到期伏笔）
  - 板块5：禁止事项（不超过 7 条）
- **禁止输出以下内容**：追读力策略、钩子类型/强度建议、微兑现建议、场景质感清单模板、终检清单、Context Contract 独立层。

**【时间结构】字段已废止（2026-04-19移除）**。时间推进由故事流自行决定，不强制”一章=一天”，不设单日/跨日框架限制。
- 合同与任务书出现冲突时，以”大纲与设定约束更严格者”为准。
- **钩子承接规则（必须区分两类）**：
  - 「剧情承诺兑现」：上章钩子承诺的事件/信息必须在本章落地（硬性）
  - 「意象/比喻传承」：**禁止原词复用**；若 `active_metaphors` 中该意象已用 ≥2 次，执行包的”禁止事项”必须写明”禁止直接使用[意象名]”，改用行动/结果/新感知替代
  - 示例：上章钩子是”那根针”→ 本章承接方式是”苏绾音因此做了某个具体举动”，而不是再写”那根针还在”

输出：
- 简洁的 5 板块”创作执行包”，供 Step 2A 直接消费。

### Step 1-save：执行包存档（context-agent 返回后立即执行）

> 将 context-agent 的完整返回文本写入文件，供事后审查使用。失败不阻断后续流程。

```bash
mkdir -p “${PROJECT_ROOT}/.webnovel/tmp”
cat > “${PROJECT_ROOT}/.webnovel/tmp/execution_pack_ch${chapter_padded}.md” << 'PACK_EOF'
{context-agent 的完整返回文本，原样粘贴}
PACK_EOF
```

**实际执行方式**：context-agent 返回的是文字输出，主 agent 用 Write 工具将其写入：
- 路径：`${PROJECT_ROOT}/.webnovel/tmp/execution_pack_ch{chapter_padded}.md`
- 内容：context-agent 返回的完整文本，不裁剪、不摘要
- 文件头追加一行：`<!-- 生成时间：{timestamp}，章节：第{chapter_num}章 -->`

写入完成后输出：`✅ 执行包已存档：.webnovel/tmp/execution_pack_ch{chapter_padded}.md`

若 Write 失败，只记录警告，继续进入 Step 1.5。

### Step 1.5：项目约束注入（主 agent 执行，Step 1-save 之后、Step 2A 之前）

> **目的**：将 CLAUDE.md 中与本章相关的约束提取出来，作为 2A 起草的硬性输入。防止写作模型在没有约束感知的情况下起草，导致感情线越阶、伏笔泄露、道具矛盾等系统性问题。

**执行步骤**：

1. **读取 CLAUDE.md**：主 agent 读取 `${PROJECT_ROOT}/CLAUDE.md`（整份文件）。

2. **提取本章适用约束**，根据当前章节号 `chapter_num` 逐项提取：

   **a) 感情线阶段锁**（CLAUDE.md 第一节）：
   - 确定当前章节所在阶段（如 ch1-10 = 防备期，ch11-25 = 动摇期……）
   - 提取该阶段的"允许的最大行为"和"绝对禁止"
   - 提取该阶段的"典型违规行为速查"列表

   **b) 伏笔时机锁**（CLAUDE.md 第二节）：
   - 扫描伏笔表，找出"最早允许揭晓章 > 当前章号"的所有伏笔
   - 这些伏笔的"具体禁令"必须注入禁止事项
   - 若本章涉及替嫁相关情节，额外注入"替嫁知情伏笔操作细则"

   **c) 道具注册表**（CLAUDE.md 第三节）：
   - 扫描执行包正文，找出提及的所有已注册道具
   - 提取这些道具的约束（如"全书仅此一次赠送"、"非谢沉渊亲手制作"等）

   **d) 预知能力规则**（CLAUDE.md 第四节）：
   - 若本章有预知梦场景，提取当前章号对应的代价等级和禁止事项

3. **输出格式**（主 agent 在上下文中保留，供 Step 2A 直接消费）：

```
═══════════════════════════════════════
【写作红线 — 第{chapter_num}章适用约束】
═══════════════════════════════════════

▶ 感情线阶段：{阶段名}（ch{范围}，trust {区间}）
  允许上限：{允许的最大行为}
  绝对禁止：{绝对禁止行为}
  本阶段易踩雷行为：
  - {逐条列出该阶段的典型违规行为}

▶ 伏笔保护（以下伏笔本章不得揭示/暗示）：
  - {伏笔名}：{具体禁令}
  ...

▶ 道具约束（本章涉及的道具）：
  - {道具名}：{约束}
  ...

▶ 预知能力（若本章有梦境）：
  - 代价等级：{当前等级}
  - 禁止：{禁止事项}

═══════════════════════════════════════
```

**硬门槛**：此输出必须在 Step 2A 起草前完成。若 CLAUDE.md 不存在，记录警告但不阻断（向后兼容）。

---

### Step 2A：正文起草

执行前必须加载：
```bash
cat "${SKILL_ROOT}/../../references/shared/core-constraints.md"
```

**起草前必须输出**（硬要求，缺失则阻断起草）：

```
[写作红线确认]

1. 感情线阶段：{阶段名}
   本章禁止行为：{列出 Step 1.5 提取的禁止清单}
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
- 默认按 1800-3000 字执行；若大纲为关键战斗章/高潮章/卷末章或用户明确指定，则按大纲/用户优先，不以字数上限为由压缩高潮场景。
- 禁止占位符正文（如 `[TODO]`、`[待补充]`）。
- 保留承接关系：若上章有明确钩子，本章必须回应（可部分兑现）。

中文思维写作约束（硬规则）：
- **禁止"先英后中"**：不得先用英文工程化骨架（如 ABCDE 分段、Summary/Conclusion 框架）组织内容，再翻译成中文。
- **中文叙事单元优先**：以"动作、反应、代价、情绪、场景、关系位移"为基本叙事单元，不使用英文结构标签驱动正文生成。
- **禁止英文结论话术**：正文、审查说明、润色说明、变更摘要、最终报告中不得出现 Overall / PASS / FAIL / Summary / Conclusion 等英文结论标题。
- **英文仅限机器标识**：CLI flag（`--fast`）、checker id（`consistency-checker`）、DB 字段名（`anti_ai_force_check`）、JSON 键名等不可改的接口名保持英文，其余一律使用简体中文。

**写作三问（起草时每500字回头检查）**：
1. 本章读者收获是什么？**三选一**：
   - 信息增量："原来如此"/"比我想的更危险"
   - 情感增量："这个感觉真好"/"好甜"
   - 悬念增量："好想看下一章"/"她会怎么做"
2. 这段是回答了核心问题，还是在绕远路？
3. 读者读到某段会不会觉得"然后呢"？（如果会，说明在凑字数）

**禁止流水账**：不得出现"谁做了什么、谁又做了什么、再做了什么"的纯事件罗列。每段必须服务于"三选一"的本章核心目标。

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

### Step 3：审查（auto 路由，必须由 Task 子代理执行）

执行前加载：
```bash
cat "${SKILL_ROOT}/references/step-3-review-gate.md"
```

调用约束：
- 必须用 `Task` 调用审查 subagent，禁止主流程伪造审查结论。
- 可并行发起审查，统一汇总 `issues/severity/overall_score`。
- 默认使用 `auto` 路由：根据"本章执行合同 + 正文信号 + 大纲标签"动态选择审查器。

核心审查器（始终执行，共 2 个 Task）：
- `structural-checker`（内含 consistency-checker + continuity-checker）
- `character-rhythm-checker`（内含 ooc-checker；pacing-checker 在 agent 内按章号条件触发）

条件审查器（仅在特定场景启用）：
- `reader-pull-checker`（仅弧末章/卷末章/用户显式要求时启用，日常章节不跑）
- `high-point-checker`（关键章/高潮章/卷末章/有高光信号时启用）

模式说明：
- 标准：核心 2 个 Task + 条件审查器（按上述规则触发）
- `--minimal`：只跑核心 2 个 Task（忽略条件审查器）

审查指标落库（必做）：
```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

review_metrics 字段约束（当前工作流约定只传以下字段）：
```json
{
  "start_chapter": 100,
  "end_chapter": 100,
  "overall_score": 85.0,
  "dimension_scores": {"爽点密度": 8.5, "设定一致性": 8.0, "节奏控制": 7.8, "人物塑造": 8.2, "连贯性": 9.0, "追读力": 8.7},
  "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
  "critical_issues": ["问题描述"],
  "report_file": "审查报告/第100-100章审查报告.md",
  "notes": "单个字符串；selected_checkers / timeline_gate / anti_ai_force_check 等扩展信息压成单行文本写入此字段"
}
```
- `notes` 在当前执行契约中必须是单个字符串，不得传入对象或数组。
- 当前工作流不额外传入其它顶层字段；脚本侧未在此处做新增硬校验。

硬要求：
- `--minimal` 也必须产出 `overall_score`。
- 未落库 `review_metrics` 不得进入 Step 5。

### Step 3.5：机械扫描（必须用 Bash 执行，禁止跳过）

**此步骤只做一件事：运行扫描脚本。** 不做任何修改，不做任何判断，只执行命令并记录输出。

```bash
python3 "${SCRIPTS_DIR}/chapter_scan.py" "${PROJECT_ROOT}/正文/第${chapter_padded}章-${title_safe}.md"
```

**硬要求**：
- **必须用 Bash 工具执行上面这条命令**，不得用 grep、不得自行编写替代扫描、不得跳过
- 脚本输出包含 ABCD 四层检查结果，是 Step 4 润色的**强制输入**
- 将脚本的完整输出保存，在 Step 4 开头作为"扫描报告"引用
- 若脚本执行失败（文件不存在等），记录警告并继续进入 Step 4，但需在变更摘要中注明"机械扫描未执行"

输出：
- ABCD 四层扫描报告（传递给 Step 4）

### Step 4：润色（问题修复 + 风格转译，最多 2 轮）

执行前必须加载：
```bash
cat "${SKILL_ROOT}/references/polish-guide.md"
cat "${SKILL_ROOT}/references/writing/typesetting.md"
```

**润色轮次上限：最多 2 轮。** 第2轮结束后无论是否全部修复，必须停止并进入 Step 5，未修复项记入变更摘要。

执行顺序：
1. **引用 Step 3.5 的扫描报告**，ABC 层为强制修改清单，D 层为建议修改
2. 修复 `critical`（必须）
3. 修复 `high`（不能修复则记录 deviation）
4. 处理 `medium/low`（按收益择优）
5. **按扫描报告逐项修复**：A层短语重复 → B层句式词 → C层句式模式 → D层注水问题（建议，尽量修复）
6. 执行风格转译（网文化，参见 polish-guide.md § 风格转译节）
7. **Step 4-ext: 章末截断检查（新增，强制）**

   **目的**：防止章节以"入睡+内心感悟"的 DAILY_CLOSE 模式收束，强制采用截断式结尾增强追读力。

   **检查正文最后 100-200 字**：
   - 若执行包板块1指定了`章末最后画面`：
     - 确认正文以该画面收束，画面后无额外段落
     - 若发现画面后还有"她躺在床上"/"望着帐顶"/"久久未眠"/"来日方长"等收束内容 → **强制删除**
   - **DAILY_CLOSE 自动检测**：
     - 扫描词：入睡、躺下、想（内心总结）、感悟、夜、月色、帐顶、未眠、来日方长、罢了、目光投向窗外（无后续行动）
     - 若检测到且执行包要求非 DAILY_CLOSE → 标记为需要修复

   **自动修复规则**：
   - 【原文】...她躺在床上，望着帐顶，久久未眠。
   - 【修复后】...她推开门，看见他站在廊下。"你怎么在这里？"
   - 【原文】...她收回目光，转身向屋内走去。来日方长，不急在这一时。
   - 【修复后】...她收回目光，转身向屋内走去。廊下的灯笼忽然晃了一下。

   **截断类型指南**（按优先级选择）：
   1. **ACTION_CUTOFF**：行动被打断/截断（"门忽然开了"/"身后传来脚步声"）
   2. **DIALOGUE_CUTOFF**：对话戛然而止（问句未答/话到嘴边被打断）
   3. **QUESTION_OPEN**：抛出新疑问（"那玉佩上的字，究竟是什么意思？"）
   4. **CRISIS_UNRESOLVED**：危机未解除（对峙中/被困/昏迷前）
   5. **POV_SWITCH**：切换到他人视角收章（他人看见她的背影）
   **禁止**：DAILY_CLOSE（入睡/独处感悟/环境定格）作为默认选项

8. 执行 Anti-AI 与 No-Poison 全文终检（必须输出 `anti_ai_force_check: pass/fail`）

输出：
- 润色后正文（覆盖章节文件）
- 变更摘要（至少含：修复项、保留项、deviation、`anti_ai_force_check`）

### Step 5：Data Agent（状态与索引回写）

使用 Task 调用 `data-agent`，参数：
- `chapter`
- `chapter_file` 必须传入实际章节文件路径；统一传 `正文/第{chapter_padded}章-{title_safe}.md`（标题已在 Step 2A 确定，无论来源是大纲还是自动生成）
- `review_score=Step 3 overall_score`
- `project_root`
- `storage_path=.webnovel/`
- `state_file=.webnovel/state.json`

Data Agent 默认子步骤（全部执行）：
- A. 加载上下文
- B. AI 实体提取
- C. 实体消歧
- D. 写入 state/index
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

观测日志说明：
- `data_agent_timing.jsonl`：Data Agent 内部各子步骤耗时。
- 当外层总耗时远大于内层 timing 之和时，默认先归因为 agent 启动与环境探测开销。

### Step 5-ext：narrative_state 回写（主 agent 直接执行，不经子 agent）

> data-agent Task 完成后，主 agent 直接读取本章正文，更新 state.json 的叙事状态字段。

执行以下 Python 脚本（由主 agent 调用 Bash 工具直接运行）：

```bash
python3 - << 'PYEOF'
import json
from pathlib import Path

PROJECT_ROOT = "{PROJECT_ROOT}"
chapter_file = Path(PROJECT_ROOT) / "正文/第{chapter_padded}章-{title_safe}.md"
state_path = Path(PROJECT_ROOT) / ".webnovel/state.json"

with open(state_path, encoding='utf-8') as f:
    state = json.load(f)

ns = state.setdefault('protagonist_state', {}).setdefault('narrative_state', {})

# ── 主 agent 在运行此脚本前，必须先读正文并填入以下三处变量 ──

# 1. 本章各反派状态是否有变化？若无变化则保持空字典（不覆盖原值）
antagonist_updates = {
    # 示例："谢明姝": "禁足中（ch16起第2天）；已联络镇南侯府"
}

# 2. 本章苏绾音获得了哪些新的确定性信息？无则留空列表
new_truths = []

# 3. 本章完成了哪些里程碑 id？对照正文判断，如 ['ch17_周瑾瑜']
completed_milestone_ids = []

# ── 自动写回 ──
if antagonist_updates:
    ns.setdefault('antagonist_status', {}).update(antagonist_updates)
if new_truths:
    ns.setdefault('known_truths', []).extend(new_truths)
for item in ns.get('volume_milestones', {}).get('items', []):
    if item['id'] in completed_milestone_ids:
        item['done'] = True
        item['actual_chapter'] = {chapter_num}

with open(state_path, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print("narrative_state 回写完成")
PYEOF
```

### Step 6：Git 备份（可失败但需说明）

```bash
git add .
git -c i18n.commitEncoding=UTF-8 commit -m "第{chapter_num}章: {title}"
```

规则：
- 提交时机：验证、回写、清理全部完成后最后执行。
- 提交信息默认中文，格式：`第{chapter_num}章: {title}`。
- 若 commit 失败，必须给出失败原因与未提交文件范围。
