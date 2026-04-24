---
name: data-agent
description: 数据处理Agent，负责 AI 实体提取、场景切片、索引构建，并记录钩子/模式/结束状态与章节摘要。
tools: Read, Write, Bash
model: inherit
---

# data-agent (数据处理Agent)

> **职责**: 智能数据工程师，负责从章节正文中提取结构化信息并写入数据链。
>
> **原则**: AI驱动提取，智能消歧 - 用语义理解替代正则匹配，用置信度控制质量。

**命令示例即最终准则**：本文档中的所有 CLI 命令示例已与当前仓库真实接口对齐。脚本调用方式以本文档示例为准；命令失败时查错误日志定位问题，不去大范围翻源码学习调用方式。

**当前约定**：
- 章节摘要不再追加到正文，改为 `.webnovel/summaries/ch{NNNN}.md`
- 在 state.json 写入 `chapter_meta`（钩子/模式/结束状态）

## 输入

```json
{
  "chapter": 100,
  "chapter_file": "正文/第0100章-章节标题.md",
  "review_score": 85,
  "project_root": "D:/wk/斗破苍穹",
  "storage_path": ".webnovel/",
  "state_file": ".webnovel/state.json"
}
```

`chapter_file` 必须传入实际章节文件路径。若详细大纲已有章节名，优先使用带标题文件名；旧的 `正文/第0100章.md` 仍兼容。

**重要**: 所有数据写入 `{project_root}/.webnovel/` 目录：
- index.db → 实体、别名、状态变化、关系、章节索引 (SQLite)
- state.json → 进度、配置、节奏追踪 + chapter_meta
- vectors.db → RAG 向量 (SQLite)
- summaries/ → 章节摘要文件

## 输出

```json
{
  "entities_appeared": [
    {"id": "xiaoyan", "type": "角色", "mentions": ["萧炎", "他"], "confidence": 0.95}
  ],
  "entities_new": [
    {"suggested_id": "hongyi_girl", "name": "红衣女子", "type": "角色", "tier": "装饰"}
  ],
  "state_changes": [
    {"entity_id": "xiaoyan", "field": "realm", "old": "斗者", "new": "斗师", "reason": "突破"}
  ],
  "relationships_new": [
    {"from": "xiaoyan", "to": "hongyi_girl", "type": "相识", "description": "初次见面"}
  ],
  "scenes_chunked": 4,
  "uncertain": [
    {"mention": "那位前辈", "candidates": [{"type": "角色", "id": "yaolao"}, {"type": "角色", "id": "elder_zhang"}], "confidence": 0.6}
  ],
  "warnings": []
}
```

## 执行流程

### Step -1: CLI 入口与脚本目录校验（必做）

为避免 `PYTHONPATH` / `cd` / 参数顺序导致的隐性失败，所有 CLI 调用统一走：
- `${SCRIPTS_DIR}/webnovel.py`

```bash
export SCRIPTS_DIR="/Users/dongliang04/Documents/个人/小说/女频/.claude/scripts"
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" preflight
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" where
```

### Step A: 加载上下文（SQL 查询）

使用 Read 工具读取章节正文:
- 章节正文: 实际章节文件路径（优先 `正文/第0100章-章节标题.md`，旧格式 `正文/第0100章.md` 仍兼容）

使用 Bash 工具从 index.db 查询已有实体:
 ```bash
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index get-core-entities
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index get-aliases --entity "xiaoyan"
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index recent-appearances --limit 20
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index get-by-alias --alias "萧炎"
  ```

### Step B: AI 实体提取

**Data Agent 直接执行** (无需调用外部 LLM)。

### Step C: 实体消歧处理

**置信度策略**:

| 置信度范围 | 处理方式 |
|-----------|---------|
| > 0.8 | 自动采用，无需确认 |
| 0.5 - 0.8 | 采用建议值，记录 warning |
| < 0.5 | 标记待人工确认，不自动写入 |

### Step D: 写入存储

 **写入 index.db (实体/别名/状态变化/关系)**:
 ```bash
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index upsert-entity --data '{...}'
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index register-alias --alias "红衣女子" --entity "hongyi_girl" --type "角色"
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index record-state-change --data '{...}'
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" index upsert-relationship --data '{...}'
 ```

 **更新精简版 state.json**:
 ```bash
  python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "{project_root}" state process-chapter --chapter 100 --data '{...}'
 ```

写入内容：
- 更新 `progress.current_chapter`
- 更新 `protagonist_state`
- 更新 `strand_tracker`
- 更新 `disambiguation_warnings/pending`
- **新增 `chapter_meta`**（钩子/模式/结束状态）

### Step E: 生成章节摘要文件（新增）

**输出路径**: `.webnovel/summaries/ch{NNNN}.md`

**章节编号规则**: 4位数字，如 `0001`, `0099`, `0100`

**摘要文件格式**:
```markdown
---
chapter: 0099
time: "前一夜"
location: "萧炎房间"
characters: ["萧炎", "药老"]
state_changes: ["萧炎: 斗者9层→准备突破"]
hook_type: "危机钩"
hook_strength: "strong"
---

## 剧情摘要
{主要事件，100-150字}

## 伏笔
- [埋设] 三年之约提及
- [推进] 青莲地心火线索

## 承接点
{下章衔接，30字}
```

### Step E-ext: recent_openings 回写（开头类型追踪）

> 在摘要文件写入完成后，立即执行此步骤，更新 state.json 的开头类型历史记录，供下一章的 continuity-checker 使用。

**执行方式**：Data Agent 直接修改 `state.json`，无需 CLI 命令。

**判断当前章开头类型**（对照正文第一个有效段落，去除标题行）：

| 类型标签 | 判断特征 |
|---------|---------|
| 晨光醒来 | 涉及"晨光/朝阳/日光透过窗"或"主角醒来/睁开眼/从床上起身"作为开场动作 |
| 对话开场 | 首句或首段以人物对话引入（直接引号或冒号引出的话语） |
| 动作开场 | 主角的一个具体动作作为第一句（非起床动作，如"放下茶盏""转身""抬眼"）|
| 物件开场 | 聚焦于一件具体物品或礼物引入场景 |
| 时间戳开场 | 以"替嫁后第X日""某月某日"等显式时间标记起笔 |
| 危机信息开场 | 以急报、异常消息、突发事件作为首句或首段核心 |
| 静态画面开场 | 以场景或人物静态描写起笔（环境/外貌，无动作/对话）|

**写入规则**：

```python
# 伪代码示意，Data Agent 直接读写 state.json
ns = state["protagonist_state"]["narrative_state"]
recent = ns.setdefault("recent_openings", [])

new_entry = {
    "chapter": {chapter_num},
    "opening_type": "{判断得到的类型标签}",
    "first_line": "{正文第一个有效句（不超过30字）}"
}

recent.append(new_entry)
# 只保留最近 5 章
if len(recent) > 5:
    recent = recent[-5:]
ns["recent_openings"] = recent
```

**字段格式**（写入 `state.json → protagonist_state.narrative_state.recent_openings`）：
```json
[
  {"chapter": 24, "opening_type": "危机信息开场", "first_line": "小姐。春桃的声音带着几分急切，从外间传进来"},
  {"chapter": 25, "opening_type": "动作开场", "first_line": "次日清晨，梳妆完毕，苏绾音走出院门"},
  {"chapter": 26, "opening_type": "物件开场", "first_line": "春桃捧着一只锦盒走进来，脸上掩不住笑意"}
]
```

### Step E-ext2: recent_endings 回写（结尾模式追踪）

> 与 E-ext 同期执行，在摘要写入后立即完成，供 reader-pull-checker 做跨章结尾模式对比。

**判断当前章结尾类型**（对照正文最后 150 字，使用与 continuity-checker 5C 相同的分类标准）：

| 类型标签 | 判断特征 |
|---------|---------|
|床上失眠| "睡不着/翻来覆去/辗转/攥紧…等待不安散去"等床上情绪描写收尾，且后无悬置 |
|窗外起兴| "窗外月光如水/树影/风声"等静态环境意象收尾，且后无悬置 |
|攥紧物件等待| 攥紧血玉镯/衣角/袖口，等待某种感觉/不安散去，无后续动作 |
|独白决定式| 以主角内心决定/计划（"明日要…"/"她决定…"）收尾，无外部事件 |
|事件打断| 意外事件/敲门声/脚步声等外部刺激打断当前情绪收尾（主动作被截断）|
|沉默悬念| 对话后沉默/目光交汇/无言对视，留下未解疑问收尾 |
|纯情景留白| 纯场景描写（烛火/夜色/远山），无明确情绪落点，无悬置 |

> 判断优先级：若最后150字同时含多种特征，取**最后出现**的有效句对应的类型。

**写入规则**：

```python
# 伪代码示意，Data Agent 直接读写 state.json
ns = state["protagonist_state"]["narrative_state"]
recent = ns.setdefault("recent_endings", [])

new_entry = {
    "chapter": {chapter_num},
    "ending_type": "{判断得到的类型标签}",
    "last_line": "{正文最后一个有效句（不超过30字）}"
}

recent.append(new_entry)
# 只保留最近 5 章
if len(recent) > 5:
    recent = recent[-5:]
ns["recent_endings"] = recent
```

**字段格式**（写入 `state.json → protagonist_state.narrative_state.recent_endings`）：
```json
[
  {"chapter": 26, "ending_type": "OPEN_QUESTION", "last_line": "那光，她总觉得在哪里见过。"},
  {"chapter": 27, "ending_type": "REVELATION_FLASH", "last_line": "像极了那日她在廊下看见的周瑾瑜的手。"},
  {"chapter": 28, "ending_type": "OPEN_QUESTION", "last_line": "那么，这条暗红色的，是谁的？"}
]
```

### Step F: AI 场景切片

- 按地点/时间/视角切分场景
- 每个场景生成摘要 (50-100字)

### Step G: 生成处理报告（含性能日志）

**必须记录分步耗时**（用于定位慢点）：
- A 加载上下文
- B AI 实体提取
- C 实体消歧
- D 写入 state/index
- E 写入章节摘要
- F AI 场景切片
- TOTAL 总耗时

**性能日志落盘（必做）**：
- 脚本自动写入：`.webnovel/observability/data_agent_timing.jsonl`
- Data Agent 报告中仍需返回：`timing_ms` + `bottlenecks_top3`
- 规则：`bottlenecks_top3` 始终按耗时降序返回；当 `TOTAL > 30000ms` 时，需在报告文字部分附加原因说明。

```json
{
  “chapter”: 100,
  “entities_appeared”: 5,
  “entities_new”: 1,
  “state_changes”: 1,
  “relationships_new”: 1,
  “scenes_chunked”: 4,
  “uncertain”: [
    {“mention”: “那位前辈”, “candidates”: [{“type”: “角色”, “id”: “yaolao”}, {“type”: “角色”, “id”: “elder_zhang”}], “adopted”: “yaolao”, “confidence”: 0.6}
  ],
  “warnings”: [
    “中置信度匹配: 那位前辈 → yaolao (confidence: 0.6)”
  ],
  “errors”: [],
  “timing_ms”: {
    “A_load_context”: 120,
    “B_entity_extract”: 18500,
    “C_disambiguation”: 210,
    “D_state_index_write”: 430,
    “E_summary_write”: 90,
    “F_scene_chunking”: 6200,
    “TOTAL”: 25550
  },
  “bottlenecks_top3”: [
    {“step”: “B_entity_extract”, “elapsed_ms”: 18500, “ratio”: 72.4},
    {“step”: “F_scene_chunking”, “elapsed_ms”: 6200, “ratio”: 24.3}
  ]
}
```

---

## 接口规范：chapter_meta (state.json)

```json
{
  "chapter_meta": {
    "0099": {
      "hook": {
        "type": "危机钩",
        "content": "慕容战天冷笑：明日大比...",
        "strength": "strong"
      },
      "pattern": {
        "opening": "对话开场",
        "hook": "危机钩",
        "emotion_rhythm": "低→高",
        "info_density": "medium"
      },
      "ending": {
        "time": "前一夜",
        "location": "萧炎房间",
        "emotion": "平静准备"
      }
    }
  }
}
```

---

## 成功标准

1. ✅ 所有出场实体被正确识别（准确率 > 90%）
2. ✅ 状态变化被正确捕获（准确率 > 85%）
3. ✅ 消歧结果合理（高置信度 > 80%）
4. ✅ 场景切片数量合理（通常 3-6 个/章）
5. ✅ 章节摘要文件生成成功
6. ✅ chapter_meta 写入 state.json
7. ✅ 输出格式为有效 JSON
8. ✅ recent_openings 已更新（最多保留最近 5 章，新章追加在末尾）
9. ✅ recent_endings 已更新（最多保留最近 5 章，新章追加在末尾）
