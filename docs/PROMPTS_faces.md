# 新表情（只换脸）立绘提示词（2026-10-31）

这是提示词，不是成品图，用 Grok 出图。
- 这四张：`sulk`（赌气）、`held`（被拎起）、`yuck`（皱脸）、`wet`（湿漉漉）。成品放 `assets/<名字>.png`，放进去就生效，没有图时会回退到原来那张（见 `docs/接口规范.md` 第 2.6 节）。
- `pout`、`hungry`、`smug`、`queasy` 四张是在原立绘上直接改脸做的，不用再出。
- Grok 出来的原图直接拿去处理就行，不用自己抠图。之后要做的是：去掉灰背景、缩放到 512×512、底边对齐、和原立绘比对大小。

## 2026-10-31 第一轮出图结果
- 每张出了 4 版，现在用的是：赌气第 4 版（侧身扭头，没出真正的背面），被拎起第 6 版，湿漉漉第 11 版，皱脸第 14 版。
- 改图时 Grok 保留了参考图的构图（1024 正好是 2 倍），所以原样缩一半就和原立绘对齐了。
- 被拎起的第 5、8 版卷发甩得太高，塞进共用裁剪框要缩小约 17%，抓起来时她会突然变小，所以改用第 6 版（缩到 0.48 倍）。
- 想换哪一版，或者以后重出：灰底原图照样抠，大小以对应参考图（angry / surprised）为准，底边落在 y≈497。

## 规格（和 vomit / shocked 两张一样）
- 512×512 RGBA，透明背景。构图是半身像，底边平切在 y≈498，角色高度约 363px（大约占画面 70%）。外面一圈白色粗描边，贴纸风，7–9px。
- 装饰符号（💢、汗滴、动作线）可以画，但不能超出 x 14–498、y 130–498。现有 21 张图共用一个裁剪框，哪张超出了，所有立绘都会跟着缩一下。
- 角色设定照现有这套来，不要照官方立绘：两侧对称的螺旋卷金发带青色挑染、银色头冠（额前一颗青宝石）、两个青色蝴蝶结加白发带、精灵耳、青色眼睛、左眼下一颗泪痣、白手套、白色荷叶边披肩、金色肩章、小小的薄荷色半透明翅膀。

## Grok 的用法
- 每张都用「上传参考图 + 改图指令」来出，只靠文字很难画得像本人。参考图用包里带的 `ref_*.png`：就是原立绘铺上灰底，免得透明背景被当成黑色。
- Grok 没有单独的反向提示词框，所以「不要什么」已经写进了通用前缀。
- 背景要求是纯灰色，因为白描边贴在白底上就抠不出来了。
- 每张出 3–4 个版本，挑头冠、发型、泪痣都对的那一张。如果画风跑偏了，就在末尾加一句 `The art style must match the uploaded image exactly.` 再出。

## 通用前缀（每张都先贴这段，后面接正文）
Edit the uploaded image. Keep the exact same chibi girl: same art style, line weight and colours, symmetrical twin drill-curl blonde hair with teal streaks, silver tiara with a teal forehead gem, two teal ribbon bows and white hairband, pointed elf ears, teal eyes, small tear mole under her left eye, white gloves, white ruffled capelet, gold epaulettes, small mint translucent fairy wings. Keep the same bust-shot framing cropped flat at the bottom edge and the thick white sticker outline around the whole figure. Plain flat solid medium grey background (#808080), no gradient, no shadow, nothing on the ground. No text, no watermark, no extra characters, no full body, no legs. Change only the following:

## sulk.png 赌气（参考图 `ref_angry.png`）
用在闹别扭期间。头部那句是「背对着你,假装在看风景……」。

she is sulking and has turned her back on the viewer: three-quarter back view, so we mostly see her back, the back of her tiara and ribbons, her twin drill curls and her little fairy wings; her head is turned just enough to peek back over her shoulder with one narrowed eye, cheek puffed out in a pout, arms crossed in front of her (hidden by her body), a small red anger mark floating near her head. Petty and cute, not genuinely furious.

备注：这张的角度变化最大，Grok 很容易把她的脸又转回正面。如果一直转不过去，可以退一步：画侧身，脸扭向一边，鼻子朝上"哼"，也能说明她在赌气。

## held.png 被拎起（参考图 `ref_surprised.png`）
用在被拖着、被丢到半空中的时候。头部那句是「双脚离地,风都不听使唤了……」。

she has just been picked up and is dangling in mid-air: both arms flung up and flailing with open gloved hands, eyes wide and a little teary, small wobbly open mouth as if wailing "waah", her drill curls, ribbons and capelet fluttering upward from the motion, a few short motion lines beside her and two tiny sweat drops. Still a bust shot, no legs visible.

## yuck.png 皱脸（参考图 `ref_angry.png`）
用在吃到辣的、苦的、蔬菜，或者推开不爱吃的东西的时候。这一张要同时管这几种情况，所以画成"难吃"，不要画成"辣"。

she has just tasted something she really dislikes: face scrunched up, eyes squeezed shut into > < shapes, nose wrinkled, tongue sticking out, cheeks flushed pink, one gloved hand raised in front of her as if pushing the food away, a few tiny blue disgust lines on her forehead and one sweat drop. Comedic and cute, not sick.

## wet.png 湿漉漉（参考图 `ref_angry.png`）
用在被浇水之后生气、被强行浇水、超级生气的时候。头部那句是「头发还在滴水,火气倒是很旺」。

she has just been soaked with water and is grumpy about it: blonde hair a shade darker and flattened, drill curls drooping and dripping, a few wet strands stuck to her cheeks, water droplets falling from her hair, tiara and ribbons, half-lidded glaring eyes, cheeks puffed in an angry pout, a small red anger mark. The water stays on her only: no puddle, no splash on the ground.

备注：头冠和蝴蝶结即使湿了也必须看得清。头发会变暗，这时候它们就是认出她最关键的地方。
