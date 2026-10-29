薇斯纳桌宠 (VesnaPet)
=====================

【运行环境】
  Windows 10/11 + Python 3.12(安装时请勾选 "Add python.exe to PATH")。

【启动】
  双击 run.bat。首次运行会自动 pip install PySide6(需联网,约几百 MB,请稍等),
  之后会用 pythonw 无黑窗启动,桌面右下角出现薇斯纳,系统托盘出现图标。
  若 pip 太慢,可手动换源:
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  依赖装好后会生成 .deps_ok 文件;想重新安装依赖时删除它即可。

【玩法】
  - 待机(idle):轻微呼吸、上下浮动;偶尔自己开心 2~3 秒;偶尔冒出一句话。
  - 单击:吓一跳(惊讶) 1 秒后恢复。
  - 快速连点 3 次以上:生气 2 秒。
  - 左键按住拖动:可移动位置(拖动时是惊讶表情),松开恢复;位置会被记住。
  - 3 分钟没有任何互动:睡着(zZ)。点击或把鼠标移上去会醒来(先惊讶)。
  - 右键菜单 / 托盘图标:
      说句话 / 窗口置顶 / 静音气泡 / 联动 Grok App / 边缘探头 / 离开边缘回到桌面 / 大小(小、中、大) / 显示隐藏 / 退出
  (菜单里还有一行灰色文字,显示当前联动状态)
  - 托盘图标单击或双击:让她现身(取消隐藏、提到最前;位置异常会回到屏幕内)。想隐藏请用菜单"显示 / 隐藏"。

【找不到她?再点一次】
  - 再次双击快捷方式 / run.bat:已经在运行的她会"现身"——取消隐藏/最小化、提到最前、变开心并说"我在这里哦~"。
    若她的位置不在任何屏幕内(换屏、分辨率变化等),会自动回到屏幕右下角的默认位置并退出探头。
  - 托盘图标单击/双击效果相同。隐藏状态不会被保存,重启后一定可见。
  - 注意:升级后第一次需先退出旧版本(托盘右键退出),新版本才支持这个"现身"。

【边缘探头(睡觉也会靠着墙)】
  - 把她拖到屏幕左边、右边或上边的边缘(松手时离边缘约 40 像素以内,或已拖出一部分),
    她会吸附过去,只露出脑袋和扒着屏幕边缘的小手,像从墙后探头偷看。
    左边缘探头朝右、右边缘是镜像、上边缘是旋转 90 度(头朝下探出)。下边缘不做(留给任务栏)。
  - 探头时:鼠标靠近、点击或被联动唤醒,她会惊喜地多探出一点;点击仍有气泡反应。
  - 不理她约 60 秒:闭眼睡着(头靠着边缘,带 z);点击、鼠标移上去或 Grok 联动事件会醒来。
  - 气泡跟着方向走:靠左边缘气泡在右侧,靠右边缘在左侧,靠上边缘在下方。
  - 再次按住拖离边缘,松手后回到普通站立;也可右键菜单"离开边缘回到桌面"。
  - 右键菜单"边缘探头"可整体开关。探头位置(边缘+沿边位置+所在屏幕)会保存,重启后恢复。
  - 多显示器:按各屏幕的可用区域(扣除任务栏)判断;两块屏幕相邻的那一侧不会触发吸附。
  - 若屏幕布局变化导致位置不可见,启动时/运行中会自动回到屏幕内(并在 error.log 记一行)。
  - 可调参数在 main.py 开头:SNAP_DIST(吸附距离)、PEEK_SLEEP_SEC(探头睡觉等待秒数)、PEEK_SCALE 等。

【联动 Grok App(可选,默认开启)】
  桌面上运行着 Grok App(grok-app.exe)时,薇斯纳会跟着它的工作状态做出反应:
    - Grok App 启动 / 首次检测到运行:开心 + 问候
    - 搜索/查资料:"正在帮你查资料~"   读写代码:"在看/改代码,我给你盯着!"
    - 跑终端命令:"在跑命令啦,要小心喔"  其他工具:"忙着呢~"
    - 需要你确认权限:惊讶 + 提醒(气泡停留更久)
    - 工具出错:惊讶 + "出错啦!别急我陪着你"
    - 工作停下约 8 秒后:开心 + "做完啦~ 快来看看吧!"
    - Grok App 退出:"拜拜~",之后恢复普通行为
    联动期间她会保持清醒(睡着时会醒来),随机气泡暂停;原有点击/拖拽/菜单照常。
  原理与隐私:
    - 只读 Grok App 的工具审计日志 %APPDATA%\grokapp\grok-app\data\audit\tool_ledger.jsonl
      的"新增行"(启动时跳到文件末尾,不处理历史内容),并只查看 sessions\*\messages.json 的修改时间。
    - 不修改任何 Grok 文件,不读取会话内容,不读取 session-api.json,不访问 Grok 的本地接口和令牌,不联网。
    - 进程检测用 Windows 系统接口(ctypes)按进程名 grok-app.exe 判断,不调用外部命令。
    - 没开 Grok App 时,行为和不装联动完全一样。
    - 在托盘/右键菜单取消勾选"联动 Grok App"即可完全关闭联动。
  限制:
    - 只能知道"工具调用的开始/结束/权限/出错"和"会话文件有变化",
      无法知道模型"正在思考"的精确时刻;"做完啦"是根据静默时间推断的。
    - 日志里的权限事件只记录决定结果(auto_allow 自动放行 / allow_session 已授权),
      自动放行不会打扰你,"需要你确认"类提醒只在出现 deny/ask 等非自动结果时触发。
    - 日志路径是 Grok App 0.2.38 的约定,版本升级后格式变化可能导致联动失效(但不会影响桌宠本体)。
  出错记录:联动或程序的异常会写到 %APPDATA%\VesnaPet\error.log,桌宠不会因此退出。

【DLC 状态协议(可选)】
  桌宠会在本机开一条管道 VesnaPet-{用户名}-live, 给独立扩展读她现在的状态
  (表情、饱腹、好感、位置、转圈/睡觉/生气等)。DLC 不装、不运行, 她完全照常。
  协议: UTF-8, 一行一个 JSON。发 {"v":1,"cmd":"get"} 或纯文本 get, 回一行快照。
  ping 用于探活, 回应里带 "proto":2 和 "caps":["get","subscribe","say"]。
  v2 新增(只在 DLC 连上并使用时生效, 旧 DLC 只发 get/ping 完全不受影响):
    - {"v":2,"cmd":"subscribe"} (或纯文本 subscribe): 这条连接之后会收到事件推送行
      {"v":2,"ev":"click","t":1760000000.0, ...}。事件有 click/double_click/pet/drag_start/drag_end/
      throw/bonk/throw_land/spin_start/spin_end/dizzy/feed/sleep/wake/state/say/idle_action/sneak_caught/
      sulk/makeup/level_up/danika_visit/danika_end/butterfly/food_effect_start/food_effect_end/
      rps/fortune/focus_start/focus_end/reminder, 字段见 live_link.py 顶部说明或 docs\接口规范.md。
    - {"v":2,"cmd":"say","text":"...","expr":"happy","sec":4}: 让她头顶冒一句气泡, 可选临时换表情
      (只认已有表情, 不认识就忽略; sec 夹在 1–8 秒, 到时回原状态)。文本最多 60 字;
      同一连接 1.2 秒内只能说一句(否则回 err "rate"); 她在睡觉/被拖/被转/被丢/晕/达妮卡来访时
      回 {"ok":false,"err":"busy"} 不打断; 静音气泡时回 "muted"。
    - 依然没有喂食/改好感/改饱食的命令, 扩展改不了她的数值。
  手工测: 桌宠开着时, 在程序目录执行  python live_link.py
  连不上就是她没在跑, 扩展应当成「桌宠不在」继续自己的逻辑。

【食物包(可选)】
  把 JSON 放进 <程序目录>\dlc\foods\ 即可给投喂卡片加新食物; 没有这个目录她完全照常。
  每个文件格式: {"foods": [ {食物}, ... ]}, 字段(除 key/name 外都可省):
    key      必填, 小写字母/数字/下划线, ≤32 字; 和原版或别的包重复 -> 跳过并记 error.log
    name     必填, 中文名(≤16 字);  short 卡片上的短名(≤7 字, 默认=name)
    emoji    没图时显示;  desc 说明;  fill 饱腹 0-40(默认 12)
    tier     fav / like / ok / dislike / weird (同原版喜好档, 默认 ok)
    trait    stew/sweet/cold/drink/spicy/veggie/bitter/dark 或省略
    origin   teyvat(提瓦特扩展) / real(现实世界) / prank(整蛊), 决定分页, 默认 teyvat
    icon     相对包目录的 .png(如 "icons/food_x.png", 不许出包目录); 也认 assets\food\food_<key>.png; 都没有用 emoji
    lines    吃时台词;  refuse 拒绝台词;  curious 第一次见到时的好奇台词(先好奇再吃)
    effect   吃后效果, 只认白名单(写 "hyper" 或 {"type":"hyper",参数...}, 超范围自动夹住):
               hyper  满屋乱跑  sec 4-20(12)  speed 2-5(3.5); 可被拖住, 拖住时继续嚷嚷, 松手跑完剩余时间
               jitter 打哆嗦    sec 1-6(3)
               hop    连跳      n 2-8(4)
               sneeze 打喷嚏    delay 0.5-3(1.2)
               stink  熏晕再生气 sec 1-5(2.4)
             可选 face: surprised/angry/shy/dizzy/happy/content/cheer;  burst: steam/sweat/note/sparkle/drop/star/puff
    effect_lines 效果中每 1.5-2.5 秒一句;  effect_drag_lines 被拖住时;  effect_end_lines 结束时一句
    affection    有效果的食物吃后好感变化 -5..5 (prank 默认 -1, 其他 0)
    refuse_again_sec 吃过后多少秒内再喂同一种会拒绝 0-3600(默认 300)
  效果期间不犯困、不做空闲动作、不叫达妮卡; 睡着/被丢/被转圈会直接结束效果。
  坏 JSON 或坏字段只记 error.log 并跳过那一项; 全部包合计最多 64 种; 每页 8 个, 放不下自动翻页。
  示例: dlc\foods\world_and_prank.json;  图标需求: dlc\foods\ICON_REQUEST.md

【设置与数据】
  设置保存在 %APPDATA%\VesnaPet\config.json(位置、大小、置顶、静音、联动开关、边缘探头开关与所在边缘)。
  删除该文件即可恢复默认。

【其他说明】
  - 只会运行一个实例,重复双击 run.bat 不会出现第二只。
  - 窗口属于工具窗口:不会出现在任务栏,也不抢键盘焦点。
  - 文件说明: main.py 主程序; panels.py / ui_kit.py 面板与组件; content.py 台词与数据; stats.py 存档;
    effects.py 粒子; food_fx.py 吃后效果; companion.py 蝴蝶与达妮卡; sounds.py 合成音效;
    grok_link.py Grok 联动; live_link.py DLC 管道; sysidle.py 系统空闲时间; interaction_hooks.py 插件加载;
    assets/ 立绘与食物图标; dlc/ 可选扩展; docs/接口规范.md 扩展接口; tools/ 小工具; run.bat 启动脚本。
  - 想改行为参数(睡觉等待时间、气泡文字、大小像素等),用记事本打开 main.py,
    修改文件开头的"可调参数"区域即可。

【互动扩展 dlc/interactions/】(2026-10-12)
启动时可选加载 dlc/interactions/*.py(interaction_hooks.py), 目录不存在则完全不影响原版。
写插件前先看 docs\接口规范.md(钩子、可用的公开方法、她「在忙什么」的活动表、自动行为让路的互动矩阵、事件表)。
插件只用公开接口, 不碰下划线属性; 检查: python tools\check_plugins.py。插件可实现 on_event 收全部事件、busy() 报自己的活动。
vomit.py「转吐了」: 滚轮转到最晕(转太多)、停下晕完 2.4 秒后, 干呕 1.4s + 吐 2.2s, 冒 2 句台词;
饱食度 -20(最低0)、好感 -1, 推事件 "vomit"; 之后 60 秒内再转只晕(走原版生气)。
图: dlc/interactions/vomit_pre.png / vomit.png, 缺图时用晕眩立绘泛绿+抖动。
comfort.py「哄她」: 生气(含闹别扭/转晕转吐后)起 30 秒内摸头 -> 别扭消气, 好感 +2, 事件 "comforted"; 每次生气只能哄一次, 接管时原版摸头效果不叠加。
companion_time.py「陪伴奖励」: 显示且醒着累计 1 小时(隐藏/睡觉暂停), 不忙时说一句, 好感 +1, 每天最多 3 次,
  计数在 数据目录/companion_time.json; 测试用环境变量 VESNA_COMPANION_SEC=秒数。事件 "companion_bonus"。
食物效果 babble(胡言乱语, 参数 sec 6-25, 默认15): 每 1.5-2.5 秒从 effect_lines 洗牌抽一句(一轮不重复), 轻晃 + 淡彩虹泛光, 结束说 effect_end_lines。
  整蛊页新增「七彩毒蘑菇」(mushroom, weird, 好感 -1, 300 秒内会拒吃)。图标 icons/food_mushroom.png 缺图时用 🍄。
食物效果 burp(打嗝, sec 4-12 默认8, n 3-5 默认4) / fly(满屏乱飞, sec 4-15 默认10, speed 0.5-1.6): fly 限当前屏幕、撞边反弹转圈、彩色拖尾,
  到时滑回原位晕一下; 被鼠标抓住 = 接住, 效果结束(可选 effect_caught_lines)。新食物: 现实世界「冰镇可乐」cola(+2, 不拒喝)、整蛊「怪味糖果」weirdcandy(-1, 300 秒)。
食物效果 shock(电击, sec 1.5-4 默认2.5): 一抖+高频抖动+白黄闪+火花, 后半段炸毛, 结束生气; 不计入 FEED_MAX。整蛊页新增「电击口香糖」shockgum(fill 0, 好感 -1, 300 秒内识破)。
  shock 专用立绘: dlc/interactions/shocked.png(首选) 或 dlc/foods/sprites/shocked.png(备用), 512x512, 每次触发重新检查; 缺图用 surprised/angry 脸。

【语音 DLC】(2026-10-16) 音频 dlc/voice/<id>.ogg + voice_map.json, 插件 dlc/interactions/voice.py。
原版 say() 末尾加了一个钩子 _ix.call("say", text, src)。查表: 原文 -> 去首尾空格; 勿扰或关音效时不播; 聊天 DLC(src=dlc)不播。
音量/开关: dlc/voice/voice_config.json {"enabled": true, "volume": 0.8}。播放出错只记一次 error.log 并停用。
  设置 → 设置页「扩展」区: 🗣️ 语音 开关 + 🎚️ 语音音量(0-100), 写 voice_config.json, 即时生效; voice_map.json 改动后自动重载。插件可用 settings_rows() 往「扩展」区注册行。
浇水 water.py: 右键菜单 / 托盘「互动」→ 💧 浇水; 插件可用 menu_items() 注册菜单项。voice.py 只配 src="pet" 的台词。
强行浇水: 左键拖着她时按右键或滚轮键 -> 浇 1.5 秒 + 挣扎, 松手后究极生气 45 秒(好感 -3, 摸头被拍开, 连摸 5 次哄好 +2), 冷却 3 分钟。钩子 on_mouse_press / on_context_menu, 插件 priority。
  究极生气时戳她: 第 1 下瞪你, 第 2 下扭头不理, 3–4 下警告, 第 5 下起跺脚朝你吹风(4 秒一次); 每戳多气 4 秒(最多回到 45 秒);
  摸到一半又戳 = 前功尽弃, 摸头次数清零。钩子 on_click。

【离开 / 回来】(2026-10-29, 只在 Windows 上生效; 新文件 sysidle.py)
她会看整台电脑多久没碰键盘鼠标(GetLastInputInfo, 只读一个系统计时, 不挂钩子, 不知道你按了什么):
  - 10 分钟没碰 = 你离开了; 回来第一次动键盘鼠标时她迎接你(睡着就先伸个懒腰), 离开 2 小时以上换「等了你好久」那组台词。
  - 久坐提醒: 键盘鼠标 5 分钟没动算起来活动过, 计时重来(以前是她睡着就清零, 结果几乎不响)。
  - 喝水 / 久坐 / 整点提醒: 她睡着但你在电脑前时, 会醒过来提醒你; 你不在时不响。
  - 提醒不会再插进达妮卡的对话、拖拽、甩飞、究极生气、转吐。
  - 好感到「好友」(Lv.4)起, 你回来时她跳一下、冒爱心, 换一组更亲近的话; 「心之契约」(Lv.6)再换一组。
  可调参数在 main.py 开头: AWAY_SEC / SIT_BREAK_SEC / BACK_LONG_SEC / RETURN_CHEER_LV。事件 user_away / user_back。
  全屏看视频超过 10 分钟不碰键盘鼠标也会被当成离开, 动一下鼠标她就会迎接你。
  不是 Windows 时读不到, 一切按原来的规矩(她睡着算你不在)。

【小心愿】(2026-10-29) dlc/interactions/wish.py
她安静待着时, 隔一阵(启动后 6–12 分钟, 之后 20–40 分钟)会小声提一个心愿, 都是现成的互动:
  摸摸头 / 想吃甜的 / 想吃冰的或喝凉的 / 想喝热汤 / 陪我猜拳 / 想看蝴蝶(要你从菜单召唤, 自己飞来的不算)。
  - 2 分钟内满足: 专门的道谢 + 爱心, 好感 +4(在那次互动原本的奖励之外)。头顶会时不时冒心愿的小图标, 1 分钟时提示一次怎么做。
  - 没理她: 嘟囔一句就算了, 不扣好感。她睡着 / 隐藏 / 闹别扭 / 被强行浇水 / 你离开电脑时, 心愿作废。
  - 勿扰时不提; 吃饱(饱腹 >= 80)时不提吃的; 每天最多 8 个。累计次数在 stats.json 的 wish_done / wish_missed。
  - 正在等的心愿会显示在托盘图标的提示和小屋的心情行里(还剩多少秒), 气泡没看到也不会错过。
  - 事件 "wish"(stage: start / done / miss / cancel)。测试用环境变量 VESNA_WISH_SEC=秒数 缩短间隔。
  不想要就删掉 wish.py(或改名成 _wish.py)。

【她记得】(2026-10-29) dlc/interactions/memories.py
她会记下每天发生了什么(只记次数), 偶尔提起来:
  - 每天第一次安静下来时(启动 1.5 分钟后)说一句「昨天 / 上次」的事: 被丢了几次、摸了几次头、喂了几次什么、
    陪你专注了多久、猜拳谁赢、帮她实现了几个心愿……挑一件那天真发生过的; 那天没什么可说就不说。
  - 偶尔(40–90 分钟)说一句累计的事: 一共喂过几次某样菜、撞过几次墙、认识几天了……同一类 7 天内不重复。
  - 一天最多 3 句; 勿扰时不说; 有小心愿在等时不插嘴。事件 "memory"。
  - 记录在 数据目录/memories.json, 只留最近 8 天; 测试用环境变量 VESNA_MEMO_SEC=秒数。不想要就删掉 memories.py。

【其他小改动】(2026-10-29)
  - 「图鉴解锁」的提示会等她这句话说完再冒, 不再盖掉别的台词。
  - 升级、专注完成、联动完工时的欢呼表情以前会被紧接着的大跳盖掉, 现在看得到了。
