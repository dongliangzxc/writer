#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性迁移脚本：将 state.json 中的 chapter_meta 和 known_truths 迁移到 index.db，
然后裁剪 state.json 只保留最近 10 章的 chapter_meta 和最近 20 条 known_truths。

用法：
    python3 migrate_state_to_db.py --project-root /path/to/book

执行前会自动备份 state.json → state.json.bak
"""

import json
import shutil
import sys
from pathlib import Path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="迁移 state.json → index.db")
    parser.add_argument("--project-root", required=True, help="书项目根目录")
    parser.add_argument("--dry-run", action="store_true", help="只分析不修改")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    state_file = project_root / ".webnovel" / "state.json"

    if not state_file.exists():
        print(f"错误：{state_file} 不存在")
        sys.exit(1)

    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)

    original_size = len(json.dumps(state, ensure_ascii=False))
    print(f"=== state.json 迁移工具 ===")
    print(f"原始大小: {original_size:,} 字符")
    print()

    # ========== 1. 迁移 chapter_meta ==========
    chapter_meta = state.get("chapter_meta", {})
    ns = state.get("protagonist_state", {}).get("narrative_state", {})
    ns_chapter_meta = ns.get("chapter_meta", {})

    # 合并两处 chapter_meta（顶层优先）
    all_meta = {}
    for key, val in ns_chapter_meta.items():
        ch_num = int(key.replace("ch", "").replace("Ch", ""))
        all_meta[ch_num] = val
    for key, val in chapter_meta.items():
        ch_num = int(key.replace("ch", "").replace("Ch", ""))
        all_meta[ch_num] = val  # 顶层覆盖

    print(f"chapter_meta 条目数: {len(all_meta)}")

    # ========== 2. 迁移 known_truths ==========
    known_truths = ns.get("known_truths", [])
    print(f"known_truths 条目数: {len(known_truths)}")

    if args.dry_run:
        print("\n[DRY RUN] 不会修改任何文件")
        # 计算裁剪后大小
        trimmed = _trim_state(state, keep_meta=10, keep_truths=20)
        new_size = len(json.dumps(trimmed, ensure_ascii=False))
        print(f"裁剪后预估大小: {new_size:,} 字符（节省 {original_size - new_size:,}，{(original_size - new_size) / original_size * 100:.0f}%）")
        return

    # ========== 3. 写入 index.db ==========
    # 添加脚本目录到 path
    scripts_dir = Path(__file__).parent.parent if (Path(__file__).parent.parent / "webnovel.py").exists() else Path(__file__).parent
    # Try to find the right scripts location
    possible_scripts = [
        Path(__file__).parent,
        Path(__file__).parent.parent,
    ]

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from data_modules.index_manager import IndexManager, ChapterMetaArchive, KnownTruthRecord
    from data_modules.config import get_config

    config = get_config(project_root=str(project_root))
    manager = IndexManager(config)

    # 写入 chapter_meta_archive
    meta_count = 0
    for ch_num, val in sorted(all_meta.items()):
        if not isinstance(val, dict):
            # 有些条目可能是字符串或其他类型，包装一下
            val = {"raw": val}
        hook = val.get("hook", {}) if isinstance(val.get("hook"), dict) else {}
        pattern = val.get("pattern", {}) if isinstance(val.get("pattern"), dict) else {}
        ending = val.get("ending", {}) if isinstance(val.get("ending"), dict) else {}
        meta = ChapterMetaArchive(
            chapter=ch_num,
            opening_type=pattern.get("opening", ""),
            hook_type=hook.get("type", pattern.get("hook", "")),
            hook_content=hook.get("content", ""),
            hook_strength=hook.get("strength", ""),
            emotion_rhythm=pattern.get("emotion_rhythm", ""),
            info_density=pattern.get("info_density", ""),
            ending_time=ending.get("time", ""),
            ending_location=ending.get("location", ""),
            ending_emotion=ending.get("emotion", ""),
            meta_json=json.dumps(val, ensure_ascii=False),
        )
        manager.save_chapter_meta_archive(meta)
        meta_count += 1
    print(f"✓ 已写入 {meta_count} 条 chapter_meta_archive 到 index.db")

    # 写入 known_truths
    # known_truths 可能是字符串列表或字典列表
    truths = []
    for item in known_truths:
        if isinstance(item, str):
            truths.append(KnownTruthRecord(chapter=0, content=item, category=""))
        elif isinstance(item, dict):
            truths.append(KnownTruthRecord(
                chapter=item.get("chapter", 0),
                content=item.get("content", str(item)),
                category=item.get("category", ""),
            ))
    if truths:
        manager.save_known_truths_batch(truths)
    print(f"✓ 已写入 {len(truths)} 条 known_truths 到 index.db")

    # ========== 4. 备份并裁剪 state.json ==========
    backup_path = state_file.with_suffix(".json.bak")
    shutil.copy2(state_file, backup_path)
    print(f"✓ 已备份: {backup_path}")

    trimmed = _trim_state(state, keep_meta=10, keep_truths=20)
    new_size = len(json.dumps(trimmed, ensure_ascii=False))

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)

    print(f"✓ state.json 已裁剪: {original_size:,} → {new_size:,} 字符（节省 {(original_size - new_size) / original_size * 100:.0f}%）")
    print()
    print("=== 迁移完成 ===")
    print("查询命令：")
    print(f"  webnovel.py index get-chapter-meta --chapter 10")
    print(f"  webnovel.py index get-recent-chapter-meta --limit 10")
    print(f"  webnovel.py index get-chapter-meta-range --start 1 --end 50")
    print(f"  webnovel.py index get-known-truths --limit 20")
    print(f"  webnovel.py index get-known-truths-by-chapter --chapter 10")
    print(f"  webnovel.py index get-all-known-truths")


def _trim_state(state: dict, keep_meta: int = 10, keep_truths: int = 20) -> dict:
    """裁剪 state.json，只保留最近 N 章的 chapter_meta 和最近 M 条 known_truths"""
    import copy
    trimmed = copy.deepcopy(state)

    # 裁剪顶层 chapter_meta：只保留最近 keep_meta 章
    chapter_meta = trimmed.get("chapter_meta", {})
    if chapter_meta:
        sorted_keys = sorted(chapter_meta.keys(), key=lambda k: int(k.replace("ch", "").replace("Ch", "")))
        if len(sorted_keys) > keep_meta:
            for key in sorted_keys[:-keep_meta]:
                del chapter_meta[key]
        trimmed["chapter_meta"] = chapter_meta

    # 删除 narrative_state.chapter_meta（与顶层重复）
    ns = trimmed.get("protagonist_state", {}).get("narrative_state", {})
    if "chapter_meta" in ns:
        del ns["chapter_meta"]

    # 裁剪 known_truths：只保留最近 keep_truths 条
    if "known_truths" in ns:
        kt = ns["known_truths"]
        if len(kt) > keep_truths:
            ns["known_truths"] = kt[-keep_truths:]

    # 裁剪 strand_tracker.history：只保留最近 10 条
    st = trimmed.get("strand_tracker", {})
    if "history" in st and len(st["history"]) > 10:
        st["history"] = st["history"][-10:]

    return trimmed


if __name__ == "__main__":
    main()
