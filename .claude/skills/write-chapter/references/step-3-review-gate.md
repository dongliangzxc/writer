# Step 3 Review Gate（内联审查版）

> **2026-04-25 变更**：审查从独立子 Agent 改为主 Agent 内联执行。主 Agent 在 Step 2 起草后已持有完整章节和上下文，直接按维度审查，省去 3-5 次子 Agent 的重复上下文加载。

## 设计理由

原方案：3 个核心子 Agent（structural-checker + character-rhythm-checker + reader-quality-checker）并行执行，每个独立加载章节正文+state+大纲。
问题：同一章文本被加载 3-5 次，仅审查步骤的输入 token 就占总量 ~40%。
新方案：主 Agent 自审，上下文零额外加载，条件审查器仍保留为 Task。

## 内联审查维度

### 维度1：设定一致性（原 consistency-checker）

检查三层 + 叙事边界：

| 层级 | 检查内容 | issue 类型 |
|------|---------|-----------|
| 战力 | 境界/能力与 state.json 一致 | POWER_CONFLICT |
| 地点 | 移动路径合法 | LOCATION_ERROR |
| 时间线 | 锚点连贯、无回跳/倒计时错误 | TIMELINE_ISSUE |
| 叙事边界 | 无 ch编号/元叙事词汇 | FOURTH_WALL_BREAK |

时间线 severity 参照：

| 问题类型 | severity |
|---------|----------|
| 倒计时算术错误（D-5 跳 D-2） | critical |
| 事件先后矛盾 / 年龄冲突 / 时间回跳 / 大跨度无过渡 | high |
| 时间锚点缺失 | medium |
| 轻微时间模糊 | low |

### 维度2：叙事连贯性（原 continuity-checker）

| 检查项 | 评级/标准 |
|--------|----------|
| 场景转换流畅度 | A/B/C/F 四级 |
| 情节线连贯 | 引入未回收/无铺垫回收/遗忘线索（>15章） |
| 伏笔管理 | 短期1-3章/中期4-10章/长期10+章 |
| 大纲一致性 | 轻微可接受/中等标记确认/重大标记deviation |

### 维度3：角色一致性（原 ooc-checker）

三级判定：

| 级别 | 定义 | 处理 |
|------|------|------|
| 轻微偏离 | 有合理世界观内解释 | 记录，可通过 |
| 中度失真 | 缺乏充分铺垫 | 标记 warning |
| 严重崩坏 | 与既定特征完全相反且无解释 | 必须修复 |

包含对话风格校验：角色口吻与设定档案匹配。

### 维度4：精彩度（原 reader-quality-checker，`--minimal` 模式跳过）

- 逐场景三增量检查（信息/情感/悬念）
- 流水账检测：300字+场景且三增量均空 + 连续3句无情绪描写 → dead_weight
- 高潮质量：有结论无过程 → `high_scene_lacks_detail: true`，扣10分
- quality_rate = 有价值场景数 / 总场景数

### 维度5：节奏检查（章号 ≥ 10 时执行）

- Strand Weave 平衡：Quest/Fire/Constellation 理想占比 55-65% / 20-30% / 10-20%
- 违规检测：Quest 过载（连续5+章 high）、Fire 干旱（>10章 medium）、Constellation 缺席（>15章 low）

## 条件审查器（仍通过 Task 调用）

日常章节不跑，仅在特定场景启用：

| 审查器 | 触发条件 |
|--------|---------|
| `reader-pull-checker` | 弧末章 / 卷末章 / 用户显式要求 |
| `high-point-checker` | 关键章/高潮章/卷末章 / 正文有高光信号 |

## 审查输出聚合

内联审查 + 条件 Task 结果统一聚合为：
- `overall_score`（加权平均）
- `dimension_scores`（按维度）
- `severity_counts`（critical/high/medium/low）
- `issues`（扁平化列表）

## 审查指标落库（必做）

```bash
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" index save-review-metrics --data "@${PROJECT_ROOT}/.webnovel/tmp/review_metrics.json"
```

字段约束：
- `start_chapter`（int）、`end_chapter`（int）：单章时二者相等
- `overall_score`（float）：必填
- `dimension_scores`（Dict[str, float]）
- `severity_counts`（Dict[str, int]）
- `critical_issues`（List[str]）
- `report_file`（str）
- `notes`（str）：扩展信息压成单行文本

## 进入 Step 4 前闸门

- `overall_score` 已生成
- `save-review-metrics` 已成功
- **时间线闸门**：`TIMELINE_ISSUE` + `severity >= high` → 必须先修复
- **第四面墙闸门**：`FOURTH_WALL_BREAK` + `severity >= high` → 必须先修复

### 时间线修复指引
- 倒计时错误 → 修正倒计时推进
- 时间回跳 → 添加闪回标记或调整锚点
- 大跨度无过渡 → 添加过渡句/段
- 事件先后矛盾 → 调整事件顺序

### 第四面墙修复指引
- 章节编号 → 改为叙事内时间描述（"四月中"、"赏花宴前"）
- 元小说引用 → 改为角色视角的自然记录
