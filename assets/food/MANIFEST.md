# Food icons (assets/food/)

Official Genshin Impact item icons for every entry in `content.py` `FOODS`, keyed by the FOODS `key`.
All 18 come from the Genshin Impact Fandom wiki (original 256×256 RGBA PNGs, fetched with `&format=original`). No fallback source (Ambr / BWIKI) was needed.

## Spec

- 256×256 px, RGBA PNG, transparent background
- Content trimmed to its alpha bbox (alpha > 8), scaled with Lanczos (premultiplied alpha) so its longer side = 216 px (≈8% / 20 px padding each side), centred
- Naming: `food_<key>.png`

## Files

| key | 中文名 | file | size | content px | source URL |
|---|---|---|---|---|---|
| frostsoup | 霜冻冰花汤 | food_frostsoup.png | 256×256 RGBA, 81 KB | 216×208 | Fandom “Item Hoarfrost Soup.png”: https://static.wikia.nocookie.net/gensin-impact/images/2/2e/Item_Hoarfrost_Soup.png/revision/latest?cb=20260923083403&format=original |
| borscht | 红菜汤 | food_borscht.png | 256×256 RGBA, 66 KB | 216×170 | Fandom “Item Borscht.png”: https://static.wikia.nocookie.net/gensin-impact/images/5/5b/Item_Borscht.png/revision/latest?cb=20260813224123&format=original |
| tofu | 杏仁豆腐 | food_tofu.png | 256×256 RGBA, 59 KB | 216×139 | Fandom “Item Almond Tofu.png”: https://static.wikia.nocookie.net/gensin-impact/images/5/5f/Item_Almond_Tofu.png/revision/latest?cb=20210216225709&format=original |
| chicken | 甜甜花酿鸡 | food_chicken.png | 256×256 RGBA, 56 KB | 216×165 | Fandom “Item Sweet Madame.png”: https://static.wikia.nocookie.net/gensin-impact/images/1/12/Item_Sweet_Madame.png/revision/latest?cb=20210415134415&format=original |
| currantice | 冰醋栗冰淇淋 | food_currantice.png | 256×256 RGBA, 44 KB | 137×216 | Fandom “Item Rimecurrant Ice Cream.png”: https://static.wikia.nocookie.net/gensin-impact/images/d/df/Item_Rimecurrant_Ice_Cream.png/revision/latest?cb=20260815001833&format=original |
| mors | 莫尔斯果酿 | food_mors.png | 256×256 RGBA, 41 KB | 144×216 | Fandom “Item Mors.png”: https://static.wikia.nocookie.net/gensin-impact/images/f/f6/Item_Mors.png/revision/latest?cb=20260923084413&format=original |
| dango | 三彩团子 | food_dango.png | 256×256 RGBA, 39 KB | 216×132 | Fandom “Item Tricolor Dango.png”: https://static.wikia.nocookie.net/gensin-impact/images/5/52/Item_Tricolor_Dango.png/revision/latest?cb=20210723020841&format=original |
| macaron | 缤纷马卡龙 | food_macaron.png | 256×256 RGBA, 56 KB | 216×142 | Fandom “Item Rainbow Macarons.png”: https://static.wikia.nocookie.net/gensin-impact/images/b/bc/Item_Rainbow_Macarons.png/revision/latest?cb=20231220031721&format=original |
| creamstew | 奶油炖鸡 | food_creamstew.png | 256×256 RGBA, 56 KB | 216×142 | Fandom “Item Fricassee de Poulet.png”: https://static.wikia.nocookie.net/gensin-impact/images/3/39/Item_Fricassee_de_Poulet.png/revision/latest?cb=20240717092232&format=original |
| potato | 蒙德土豆饼 | food_potato.png | 256×256 RGBA, 60 KB | 216×170 | Fandom “Item Mondstadt Hash Brown.png”: https://static.wikia.nocookie.net/gensin-impact/images/e/e8/Item_Mondstadt_Hash_Brown.png/revision/latest?cb=20210416221824&format=original |
| rye | 格鲁波夫黑列巴 | food_rye.png | 256×256 RGBA, 58 KB | 216×157 | Fandom “Item Glupov Rye Bread.png”: https://static.wikia.nocookie.net/gensin-impact/images/2/21/Item_Glupov_Rye_Bread.png/revision/latest?cb=20260813224146&format=original |
| tacos | 塔塔可 | food_tacos.png | 256×256 RGBA, 57 KB | 216×129 | Fandom “Item Tatacos.png”: https://static.wikia.nocookie.net/gensin-impact/images/8/8d/Item_Tatacos.png/revision/latest?cb=20240828114910&format=original |
| waterfish | 万民堂水煮鱼 | food_waterfish.png | 256×256 RGBA, 64 KB | 216×148 | Fandom “Item Wanmin Restaurant's Boiled Fish.png”: https://static.wikia.nocookie.net/gensin-impact/images/e/ec/Item_Wanmin_Restaurant%27s_Boiled_Fish.png/revision/latest?cb=20201210062546&format=original |
| salad | 满足沙拉 | food_salad.png | 256×256 RGBA, 58 KB | 216×151 | Fandom “Item Satisfying Salad.png”: https://static.wikia.nocookie.net/gensin-impact/images/8/8f/Item_Satisfying_Salad.png/revision/latest?cb=20210417153219&format=original |
| forestsalad | 雨林沙拉 | food_forestsalad.png | 256×256 RGBA, 65 KB | 216×178 | Fandom “Item Selva Salad.png”: https://static.wikia.nocookie.net/gensin-impact/images/7/75/Item_Selva_Salad.png/revision/latest?cb=20220825090918&format=original |
| bitter | 苦水 | food_bitter.png | 256×256 RGBA, 57 KB | 169×216 | Fandom “Item Xocoatl.png”: https://static.wikia.nocookie.net/gensin-impact/images/6/6b/Item_Xocoatl.png/revision/latest?cb=20241009222010&format=original |
| charcoal | 如同焦炭的蘑幻之菇 | food_charcoal.png | 256×256 RGBA, 47 KB | 216×140 | Fandom “Item Charred Mushroom Phantasm.png”: https://static.wikia.nocookie.net/gensin-impact/images/2/22/Item_Charred_Mushroom_Phantasm.png/revision/latest?cb=20260115234221&format=original |
| weirdchicken | 奇怪的甜甜花酿鸡 | food_weirdchicken.png | 256×256 RGBA, 56 KB | 216×165 | Fandom “Item Suspicious Sweet Madame.png”: https://static.wikia.nocookie.net/gensin-impact/images/4/48/Item_Suspicious_Sweet_Madame.png/revision/latest?cb=20210415140532&format=original |

## Integration note (for the programmer)

- Icons are keyed by the FOODS `key`. Suggested loader:

```python
from pathlib import Path
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

FOOD_DIR = Path(__file__).parent / "assets" / "food"
_food_pix = {}

def food_pixmap(key, size):
    """Return a smooth-scaled QPixmap, or None -> caller falls back to f['emoji']."""
    ck = (key, size)
    if ck not in _food_pix:
        p = FOOD_DIR / f"food_{key}.png"
        pm = QPixmap(str(p)) if p.exists() else QPixmap()
        _food_pix[ck] = None if pm.isNull() else pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return _food_pix[ck]
```

- If the file is missing (or fails to load), keep drawing the existing emoji (`f['emoji']`), so new foods without icons still work.
- Recommended display sizes: 64 px in menu/feeding tiles, 40 px for flying/eating effects. Always use smooth scaling (`Qt.SmoothTransformation`, or `QPainter.SmoothPixmapTransform` when drawing scaled); for HiDPI, scale to size×devicePixelRatio and set the pixmap's devicePixelRatio.
- Icons are game assets © HoYoverse, used here for a personal fan project.
