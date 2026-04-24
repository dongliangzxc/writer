#!/usr/bin/env python3
"""
章节机械扫描（ABCD四层）
用法: python3 chapter_scan.py <章节文件路径>

输出润色阶段的强制修改目标：
  A层: 高频重复短语
  B层: 高频句式词
  C层: 重复句式模式
  D层: 内心独白注水检测
"""

import re
import sys
import collections


def scan_chapter(filepath):
    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    print(f"文件: {filepath}")
    print(f"字数: {len(cjk_chars)}")
    print()

    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("#")]

    # ── A层: 3-8字短语重复 ──
    phrases = re.findall(r"[\u4e00-\u9fff]{3,8}", text)
    counts = collections.Counter(phrases)
    repeats = [(p, c) for p, c in counts.most_common(30) if c >= 3]
    if repeats:
        print("【A. 高频重复短语（≥3次）- 非角色名的必须替换】")
        for phrase, count in repeats[:15]:
            print(f"  「{phrase}」{count}次 → 角色名/专有名词保留，其余最多留2次")
    else:
        print("【A】✅ 通过")

    # ── B层: 2字高频修饰词/句式词 ──
    style_words = [
        "像是", "某种", "仿佛", "似乎", "忽然",
        "竟然", "不由", "便是", "只是", "却是",
    ]
    print()
    b_hits = []
    for w in style_words:
        c = text.count(w)
        if c >= 5:
            b_hits.append((w, c))
    if b_hits:
        print("【B. 高频句式词（≥5次）- 必须大幅削减】")
        for w, c in b_hits:
            print(f"  「{w}」{c}次 → 全章最多保留3次，其余改为具体描写或删除")
    else:
        print("【B】✅ 通过")

    # ── C层: 句式模式检测 ──
    patterns = {
        "声音很[轻淡柔低沉]": "声音+形容词",
        "目光[落在一]": "目光+动作",
        "[她他]不知道": "角色+不知道",
        "[她他]只知道": "角色+只知道",
        "没有说话": "XX没有说话",
        "不由[得自]": "不由得/不由自主",
        "眼[神睛]里[藏有却]": "眼神里+情绪",
        "带着[一几某]": "带着+量词",
    }
    print()
    c_hits = []
    for pat, label in patterns.items():
        matches = re.findall(pat, text)
        if len(matches) >= 3:
            c_hits.append((label, len(matches)))
    if c_hits:
        print("【C. 重复句式模式（≥3次）- 必须替换为不同写法】")
        for label, n in c_hits:
            print(f"  [{label}] 模式命中 {n} 次 → 最多保留2次，其余改写")
    else:
        print("【C】✅ 通过")

    # ── D层: 内心独白注水检测（建议层，不阻断流程） ──
    print()
    print("【D. 内心独白注水检测（建议）】")
    d_issues = []

    # D0: 超长段落预警（反合段逃避检测）
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    long_paras = []
    for i, para in enumerate(paragraphs):
        if para.startswith("#") or para.startswith("---"):
            continue
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", para))
        if cjk_count > 150:
            long_paras.append((i + 1, cjk_count))
    if long_paras:
        msg = f"  [超长段落] {len(long_paras)}个段落超过150字："
        print(msg)
        for idx, cnt in long_paras[:5]:
            print(f"    第{idx}段: {cnt}字 → 建议拆分为多个短段落")
        d_issues.append("超长段落")

    # 构建智能段落列表：超长段落按句子二次切分
    smart_paragraphs = []
    for para in paragraphs:
        if para.startswith("#") or para.startswith("---"):
            continue
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", para))
        if cjk_count > 150:
            # 超长段落按句号/问号/感叹号切分
            sentences = re.split(r"(?<=[。！？])", para)
            # 每2-3句合为一个逻辑段
            chunk = ""
            for s in sentences:
                chunk += s
                chunk_cjk = len(re.findall(r"[\u4e00-\u9fff]", chunk))
                if chunk_cjk >= 60:
                    smart_paragraphs.append(chunk.strip())
                    chunk = ""
            if chunk.strip():
                smart_paragraphs.append(chunk.strip())
        else:
            smart_paragraphs.append(para)

    # D1: 收束词滥用
    closure_words = ["不知道", "只知道", "没有说话", "她想", "他想"]
    d1_hits = []
    for w in closure_words:
        c = text.count(w)
        if c >= 3:
            d1_hits.append(f"「{w}」{c}次")
    if d1_hits:
        msg = f"  [收束词滥用] {'、'.join(d1_hits)} → 全章每项最多2次"
        print(msg)
        d_issues.append(msg)

    # D2: 排比追问链（还是……还是……还是……）
    chains = re.findall(r"还是[^。？！\n]{2,20}[？?]", text)
    if len(chains) >= 4:
        msg = f'  [排比追问] "还是...？"出现{len(chains)}次 → 最多保留1组(≤3个)'
        print(msg)
        d_issues.append(msg)

    # D3: 同一关键短语跨段复述（使用智能段落列表，防合段逃避）
    cross_para = collections.Counter()
    for phrase, count in counts.most_common(50):
        if count >= 4 and len(phrase) >= 4:
            para_count = sum(1 for p in smart_paragraphs if phrase in p)
            if para_count >= 3:
                cross_para[phrase] = para_count
    if cross_para:
        print("  [跨段复述] 同一短语在多个段落/句群反复出现：")
        for phrase, pc in cross_para.most_common(5):
            print(f"    「{phrase}」出现在{pc}个不同段落/句群 → 已知信息一笔带过，不要反复复述")
        d_issues.append("跨段复述")

    # D4: 连续纯思绪段（使用智能段落列表，防合段逃避）
    action_signals = re.compile(
        r'["""\u300c]|走|站|转身|拿|握|推|拉|坐|起身|伸手|抬|低头|回头|开口|摩挲|闭上|睁开|点头|摇头|叹|放下|翻|接过|递|取出|攥|蜷|写|跑|停|按|碰|触|扣|掏|捏|倒|挡|打开|点上|划|落在|收回|搁|靠|敲|踏|跪|弯|蹲|跨|撩|别|插|系|解|披|脱|穿|端|捧|举|扶|扔|丢|收|揣|藏'
    )
    consecutive_thought = 0
    max_thought = 0
    thought_start_idx = -1
    for i, para in enumerate(smart_paragraphs):
        if not action_signals.search(para):
            consecutive_thought += 1
            if consecutive_thought >= 3 and thought_start_idx == -1:
                thought_start_idx = i - consecutive_thought + 1
            max_thought = max(max_thought, consecutive_thought)
        else:
            consecutive_thought = 0
            thought_start_idx = -1
    if max_thought >= 3:
        msg = f"  [纯思绪堆叠] 最长连续{max_thought}段/句群无动作/对话"
        print(msg)
        print(f"    修复方向：在思绪段之间【增加】1-2句具体动作（角色移动/拿起物品/环顾/触碰等），而非改写现有思绪段")
        print(f"    错误做法：反复改写同一段思绪文字 ← 这不会减少思绪段数量")
        print(f"    正确做法：第2段思绪后插入一句动作描写（如'她走到窗边''手指摩挲着杯沿'），打断纯思绪链")
        d_issues.append(msg)

    if not d_issues:
        print("  ✅ D层全部通过")

    print()
    # ABC层为阻断项，D层为建议项（不影响exit code）
    abc_issues = bool(repeats or b_hits or c_hits)
    if abc_issues:
        print("【扫描完成 - ABC层标记项为润色强制修改目标】")
    if d_issues:
        print("【D层为建议项 - 尽量修复但不阻断流程】")
    if not abc_issues and not d_issues:
        print("【扫描完成 - 全部通过】")

    # 只有ABC层问题才返回非零exit code（阻断）
    # D层问题只报告不阻断，防止M2.7陷入无限润色循环
    return 0 if not abc_issues else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 chapter_scan.py <章节文件路径>")
        sys.exit(1)
    sys.exit(scan_chapter(sys.argv[1]))
