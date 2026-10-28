# -*- coding: utf-8 -*-
"""从 main.py 的 ACTIVITIES / AUTO 表打印互动矩阵(Markdown), 贴进 docs/接口规范.md。
只做语法解析, 不 import main(不需要装 PySide6)。用法: python tools/print_matrix.py"""
import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent / "main.py"
NAMES = {   # 自动行为的中文说明
    "idle_action": "空闲小动作", "danika_auto": "达妮卡自己来", "danika": "叫达妮卡(手动也查)",
    "random_bubble": "随机冒一句", "sneak": "偷吃", "auto_butterfly": "蝴蝶自己飞来", "chase": "去追蝴蝶",
    "fall_asleep": "没人理就睡着", "reminder": "喝水/久坐/整点/饿了提醒", "live_say": "DLC 的 say",
}


def tables():
    out = {}
    for node in ast.parse(MAIN.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("ACTIVITIES", "AUTO"):
                out[node.targets[0].id] = ast.literal_eval(node.value)
    return out["ACTIVITIES"], out["AUTO"]


def main():
    acts, auto = tables()
    cols = list(acts)
    print("| 自动行为 | 只在这些表情 | " + " | ".join(cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    for k, (states, blockers) in auto.items():
        st = "、".join(states) if states else "不限"
        cells = ["●" if c in blockers else "" for c in cols]
        print(f"| {NAMES.get(k, k)} `{k}` | {st} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
