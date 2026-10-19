"""v2：合併店家資料、算實際路程、自動分類，嵌進 index.html 的 /*SHOPS*/ 位置。

輸入
  data/shops_v1.json    v1 的 63 家（直線 1.2 km 內，含營業時間）
  data/shops_v2_rows.json v2 新收集的店（5 km 範圍，含營業時間、消費金額與實際路程），每列：
                         [店名, 評分, 評論數, 緯度, 經度, Google 類別, 地址, 是否飲料, 步行公尺, 開車公尺, 消費金額, 營業時間]
輸出
  data/shops_raw.json   合併後、已篩選的資料
  index.html            嵌入資料
"""
import json
import pathlib
import re
import sys
import time
import urllib.request
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from manual_tags import CAT_FIX, PRICE_GUESS, SHORT, TAGS  # noqa: E402

CENTER = (23.0016, 120.2207)  # 國立成功大學醫學院
WALK_MAX, RIDE_MAX = 1200, 5000


def route(points, profile):
    """OpenStreetMap 路線服務：從醫學院到每個點的實際路程（公尺）。"""
    out = []
    for s in range(0, len(points), 40):
        chunk = points[s:s + 40]
        coords = ";".join([f"{CENTER[1]},{CENTER[0]}"] + [f"{p[1]},{p[0]}" for p in chunk])
        url = f"https://routing.openstreetmap.de/routed-{profile}/table/v1/driving/{coords}?sources=0&annotations=distance"
        with urllib.request.urlopen(url, timeout=60) as r:
            j = json.load(r)
        assert j["code"] == "Ok", j
        out += [round(d) for d in j["distances"][0][1:]]
        time.sleep(1)
    return out


v1 = json.loads((ROOT / "data" / "shops_v1.json").read_text(encoding="utf-8"))
rows = json.loads((ROOT / "data" / "shops_v2_rows.json").read_text(encoding="utf-8"))
KEYS = ["n", "r", "c", "lat", "lng", "cat", "addr", "drink", "walk", "ride", "price", "h"]
new = [dict(zip(KEYS, r)) for r in rows]
ICE = r"冰|八寶|豆花|雪花|杏仁|甜品|かき氷|喫茶"
for s in new:
    if s["cat"] == s["n"] or re.match(r"^[\d.]+\(", s["cat"]):
        s["cat"] = ""  # Google 卡片沒列類別，抓到的是店名或評分
    # 「冰品飲料店」也包含冰店：店名有冰、豆花等字的算甜點，不適用飲料的 4.0 門檻
    s["drink"] = bool(re.search(r"飲料|奶茶|茶飲|果汁|茶舖|茶館", s["cat"] + s["n"])) and not re.search(ICE, s["n"] + s["cat"].replace("冰品飲料店", ""))
    s["h"] = [d or [] for d in s["h"]]

# v1 的店也用實際路程重新算
walk = route([(s["lat"], s["lng"]) for s in v1], "foot")
ride = route([(s["lat"], s["lng"]) for s in v1], "car")
for s, w, r in zip(v1, walk, ride):
    s.update(walk=w, ride=r, drink=TAGS[s["n"]][0] == "drink", src="v1")

by_name = {s["n"]: s for s in v1}
dropped = Counter()
for s in new:
    if s["n"] in by_name:
        continue  # v1 已有（營業時間已人工核對過）
    if not any(s["h"]):
        continue  # 查不到營業時間就不收，避免抽到沒開的店
    if re.search(r"香料|超市|商店|雜貨|市場", s["cat"]):
        dropped["不是餐飲店"] += 1
        continue
    if s["c"] <= 200 or s["r"] < (4.0 if s["drink"] else 4.6):
        dropped["評分／評論不足"] += 1
        continue
    s["src"] = "v2"
    by_name[s["n"]] = s

# ---------- 自動分類（v2 新增的店） ----------
RULES = [  # (標籤, 比對 Google 類別或店名的關鍵字)
    ("早午餐", r"早午餐|早餐|吐司|蛋餅|brunch"),
    ("日式", r"日本|日式|壽司|拉麵|丼|居酒屋|烏龍|定食|燒鳥|鰻|天婦羅|豬排|和食"),
    ("韓式", r"韓"),
    ("火鍋", r"火鍋|鍋物|涮|羊肉爐|薑母鴨"),
    ("燒肉", r"燒肉|燒烤|烤肉"),
    ("牛肉湯", r"牛肉湯"),
    ("台式小吃", r"台灣|台式|小吃|肉燥|滷|魯肉|米糕|碗粿|蝦捲|擔仔|鱔魚|蚵|虱目|粥|香腸|肉圓|湯品|羹|鹹粥|鵝肉|熟食"),
    ("中式料理", r"湘|川菜|四川|重慶|中菜|中式|熱炒|港式|粵|上海|滬|江浙|酒家"),
    ("麵食", r"麵|餃|湯包|小籠|饅頭"),
    ("異國料理", r"印度|泰|越南|墨西哥|Fusion|南洋|中東|土耳其|緬甸|印尼|馬來|新加坡"),
    ("西式義式", r"意大利|義大利|義式|法國|西餐|牛排|扒房|漢堡|披薩|pizza|pasta|美式|歐陸|酒館|bistro"),
    ("便當簡餐", r"便當|簡餐|自助餐|食堂|快餐|沙律|沙拉"),
    ("素食友善", r"素|蔬食|vegan"),
]


def group_of(s):
    text = s["cat"] + s["n"]
    if s.get("drink"):
        return "drink"
    if re.search(r"咖啡|cafe|café|coffee", text, re.I):
        return "cafe"
    if re.search(r"甜品|甜點|冰|豆花|雪糕|蛋糕|糕餅|餅店|烘焙|麵包|鬆餅|布丁|仙草|芋圓|甜湯|雪花|波士頓派", text):
        return "dessert"
    return "meal"


def late_night(hours):
    """有任何一天營業到 23:00 以後（含跨午夜）就標「宵夜」。"""
    for day in hours:
        for seg in day:
            a, b = seg.split("-")
            if b <= a or b >= "23:00":
                return True
    return False


def budget(price, group):
    m = re.match(r"\$([\d,]+)", price or "")
    if m:
        low = int(m.group(1).replace(",", ""))
        return 1 if low < 200 else 2 if low < 400 else 3
    return {"drink": 1, "dessert": 1, "cafe": 2, "meal": 2}[group]


def short(name, src):
    if name in SHORT:
        return SHORT[name]
    if src == "v1":
        return name
    s = re.split(r"[｜|（(\-－–—/]", name)[0].strip() or name
    return s if len(s) <= 16 else s[:15] + "…"


shops = []
for s in sorted(by_name.values(), key=lambda x: x["walk"]):
    if s["walk"] > WALK_MAX and s["ride"] > RIDE_MAX:
        dropped["超過 5 km"] += 1
        continue
    if s["src"] == "v1":
        group, tags = TAGS[s["n"]]
        b = budget(s["price"], group) if s["price"] else PRICE_GUESS[s["n"]]
        cat = CAT_FIX.get(s["n"], s["cat"])
    else:
        group = group_of(s)
        tags = [] if group != "meal" else [t for t, pat in RULES if re.search(pat, s["cat"] + s["n"], re.I)]
        if group == "meal" and late_night(s["h"]):
            tags.append("宵夜")
        b = budget(s["price"], group)
        cat = s["cat"]
    shops.append({
        "id": ("g" if s["src"] == "v1" else "n") + f"{len(shops):03d}",
        "name": short(s["n"], s["src"]), "full": s["n"], "group": group, "tags": tags, "budget": b,
        "price": s["price"] or "（估計）", "rating": s["r"], "reviews": s["c"], "hot": s["c"] >= 2000,
        "walk": s["walk"], "ride": s["ride"], "lat": s["lat"], "lng": s["lng"],
        "cat": cat, "addr": s.get("addr", ""), "hours": s["h"],
    })

# 分店縮短後同名（例如兩家「八木茶飲」）就改用完整店名
dup = Counter(s["name"] for s in shops)
for s in shops:
    if dup[s["name"]] > 1:
        s["name"] = s["full"] if len(s["full"]) <= 18 else s["full"][:17] + "…"

(ROOT / "data" / "shops_raw.json").write_text(json.dumps(shops, ensure_ascii=False, indent=0), encoding="utf-8")
html_path = ROOT / "index.html"
html = html_path.read_text(encoding="utf-8")
blob = json.dumps(shops, ensure_ascii=False, separators=(",", ":"))
html = re.sub(r"/\*SHOPS\*/.*?/\*END\*/", lambda _: "/*SHOPS*/" + blob + "/*END*/", html, flags=re.S)
html_path.write_text(html, encoding="utf-8")

walkers = [s for s in shops if s["walk"] <= WALK_MAX]
print("total", len(shops), "| walk ≤1.2km", len(walkers), "| ride-only", len(shops) - len(walkers))
print("groups", Counter(s["group"] for s in shops), "| walk groups", Counter(s["group"] for s in walkers))
print("v1 now beyond walking:", [s["name"] for s in shops if s["id"].startswith("g") and s["walk"] > WALK_MAX])
print("dropped", dict(dropped), "| untagged meals", sum(1 for s in shops if s["group"] == "meal" and not s["tags"]))
