# 被电击口香糖电到 立绘提示词（2026-11-02 重画）

这是提示词，不是成品图，用 Grok 出图。
- 成品是 `dlc/interactions/shocked.png`（和 vomit 那两张放在一起，都是角色的互动立绘，不是食物图标）。电到期间 `food_fx` 用它，外加白 / 黄闪烁和左右抖。
- 规格和 `assets` 里的立绘一样：512×512 RGBA 透明背景，半身像，底边 y≈497，内容不能超出共用裁剪框 (14,130)–(498,498)。
  程序会先按这个框裁（`pet.fit_sprite`），再缩放到当前立绘大小；框外的部分直接看不见。
- 用法和 `docs/PROMPTS_faces.md` 一样：上传参考图 `ref_surprised.png`，先贴那边的「通用前缀」，再接下面的正文。

## 第一版为什么重画（2026-10-14 那张）
- 头发炸成一大团爆炸头，盖住了蝴蝶结和两边的螺旋卷，人也被挤小了一圈，认不太出是她。
- X 光骨架占了整个身子，眼睛只剩白眼。闪烁和抖动程序本来就有，图里不用再画。
- 另外以前程序把整张 512×512 拉伸到裁好的立绘尺寸（484×368），竖着被压到七成，看起来是扁的。已经改成先裁再缩放。

## 正文
she has just been zapped by an electric shock and is frozen stiff mid-zap: her twin drill curls and bangs frizzed and puffed out with static, a few strands sticking straight out sideways, but the drill-curl shape is still clearly recognisable and no hair rises higher than the top of her ribbon bows; a few hair tips slightly singed darker with two or three tiny puffs of grey smoke; teal eyes wide open with tiny shrunken pupils and a small tear at each corner; teeth clenched in a stiff wavy zigzag grimace; shoulders hunched up and both arms locked rigid, gloved fingers splayed stiff; her tiara knocked slightly crooked with a tiny spark jumping off the forehead gem; small bright blue and yellow zigzag sparks crackling close around her outline. Funny and cute, not hurt. No skeleton, no x-ray, no glowing aura, no blank white eyes.

## 出图结果（2026-11-02）
- 出了四版（17–20），用的是第 17 版。
- 「头冠歪了」这句 Grok 会画成两个头冠：一个戴着，另一个飞出去（17、19）或者叠在一起（20）。以后重出时把这句换成
  `her tiara still sitting on her head, a tiny spark jumping off the forehead gem`。
- 第 18 版有四只手（两只握着法杖，下面还张着两只），第 20 版也多了手。可以在末尾加一句 `exactly two arms and two hands, not holding the wand`。
- 第 17 版 Grok 保留了 2 倍构图，原样缩一半，再左移 4px（右边那撮焦毛超出了 498）。接着做了三件事：
  - 灰烟是独立的小块，删掉。
  - 头顶上沿（y≈143，蝴蝶结的白描边）以上全删，飞走的那个头冠和两边的火花都在上面。头冠右腿挨着蝴蝶结，那一段删到 y=148。
  - 头冠尖上的火花留着，在 130–150 之间渐隐。
- 抠图用的是灰底漫水，螺旋卷圈里那几块灰底没有白描边围着，单独按「颜色是平的灰」挖掉。
