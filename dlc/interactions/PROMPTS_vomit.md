# 转圈吐 立绘提示词（2026-10-12）

这是提示词，不是成品图。出图用用户自己的图像工具。原图放 `dlc/interactions/raw/`（vomit_pre_raw.png、vomit_raw.png），抠图、对齐和一致性检查由 Game Art Director 处理，成品是 `vomit_pre.png`、`vomit.png`。

## 规格（照现有 21 张 Q 版立绘量出来的）
- 512×512 RGBA，透明背景。
- 构图是半身像（现有立绘都是胸像，看不到下半身），所以"弯腰"要画成头往前低、肩膀耸起来。
- 底边平切在 y≈498，角色高度大约占画面 70%（idle 的 bbox 是 47,130–465,498，dizzy 是 32,135–480,498），顶部留空大约 25%。
- 外面一圈白色粗描边贴纸风，7–9px。
- 角色设定照现有这套来，不要照官方立绘：两侧对称螺旋卷金发带青色挑染、银色头冠（额前青宝石）、两个青色蝴蝶结加白发带、精灵耳、青色眼睛、左眼下一颗泪痣、白色荷叶边披肩、金色肩章、小薄荷色翅膀。

## 强烈建议：用图生图或参考图模式
上传 `assets/dizzy.png` 当参考图（有角色参考或风格参考功能的工具，就把 `assets/idle.png` 一起传上去），重绘强度设在 0.45–0.6 左右。只靠文字很难画得像本人，这一点之前已经吃过亏。

## 通用前缀（两张都先贴这段）
chibi sticker illustration of the same girl as the reference image, bust shot cropped at the chest, symmetrical twin drill-curl blonde hair with teal streaks, silver tiara with teal forehead gem, two teal ribbon bows and white hairband, pointed elf ears, teal eyes, small tear mole under left eye, white ruffled capelet, gold epaulettes, small mint translucent fairy wings, thick white sticker outline around the whole figure, clean anime cel shading, soft pastel colours, transparent background, nothing on the ground, no text, no watermark

## 反向提示词（工具支持时）
realistic vomit, gross, liquid splash on floor, puddle, mess on ground, blood, photorealistic, extra characters, full body, legs, text, watermark, background scenery

## vomit_pre.png（干呕前摇）
…, dizzy and nauseous expression, face slightly green-tinted pale, head tilted forward and down, shoulders hunched, one gloved hand covering her mouth, cheeks puffed, eyes squeezed shut or swirly spiral eyes, small sweat drops, tiny cartoon swirl symbols floating around her head

## vomit.png（正在吐）
…, comedic cartoon throwing-up pose, head leaning forward, mouth open, a stylised rainbow stream with little sparkles pouring out of her mouth and fading out mid-air before reaching the bottom edge, spiral eyes, sweat drops, cartoon dizzy stars, cute and silly not disgusting

## 备注
- 彩虹必须在画面里就断开（淡出），不能碰到底边，地上什么都不留，这是用户的要求。
- 两张要用同一个工具、同一套设置、同一张参考图来出，否则发型和配色容易跑偏。每张建议出 3–4 个版本挑一张。
