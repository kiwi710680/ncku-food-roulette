"""把 shops_raw.json 加上分類、預算等級，嵌進 index.html 的 /*SHOPS*/ 位置。"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
raw = json.loads((ROOT / "data" / "shops_raw.json").read_text(encoding="utf-8"))

# 大類：meal 正餐 / drink 飲料 / dessert 甜點冰品 / cafe 咖啡廳；正餐再加細分標籤
TAGS = {
    "優氧食光": ("meal", ["早午餐", "素食友善"]),
    "ChillVibe": ("cafe", []),
    "鯤島 Khuntor": ("meal", ["異國料理", "宵夜"]),
    "饗義廚房": ("meal", ["西式義式"]),
    "健康燒肉屋 貴一郎": ("meal", ["燒肉", "日式"]),
    "麥雅印度咖喱 Maiya Indian Curry Halal": ("meal", ["異國料理"]),
    "八木茶飲-成大店": ("drink", []),
    "早安勝利美": ("meal", ["早午餐"]),
    "娟姐牛肉湯": ("meal", ["牛肉湯", "台式小吃"]),
    "得意吉義式冰淇淋": ("dessert", []),
    "洄游丼飯所": ("meal", ["日式"]),
    "牛A炒牛肉": ("meal", ["台式小吃"]),
    "尼法": ("meal", ["西式義式"]),
    "郭鍋食堂": ("meal", ["便當簡餐"]),
    "裊淡咖啡": ("cafe", []),
    "Las Adelitas": ("meal", ["異國料理"]),
    "小董牛肉湯爐": ("meal", ["火鍋", "牛肉湯", "宵夜"]),
    "백년토종삼계탕 百年土種蔘雞湯 台南成大店": ("meal", ["韓式"]),
    "焼肉スマイル（燒肉Smile）台南成大店": ("meal", ["燒肉", "日式"]),
    "築間幸福鍋物 台南成大店": ("meal", ["火鍋"]),
    "雷克斯咖啡吧": ("cafe", []),
    "加依軒小籠湯包成大店": ("meal", ["台式小吃", "麵食"]),
    "泊飲茶館CHÂTEAU BLANC 長榮店": ("drink", []),
    "BG韓式炸雞-台南成大店": ("meal", ["韓式"]),
    "米楠印度料理 Milan Indian Cuisine": ("meal", ["異國料理"]),
    "便當翔 Bento Xiang 光明店": ("meal", ["便當簡餐"]),
    "念念Table": ("meal", ["早午餐", "便當簡餐"]),
    "賦于咖啡": ("cafe", []),
    "大廳茶軒": ("cafe", []),
    "動感滷味-東興店（台南創始總店）": ("meal", ["台式小吃"]),
    "公園口八寶冰正宗老店": ("dessert", []),
    "Panorama caffe": ("cafe", []),
    "龍鳳同心億麵攤": ("meal", ["麵食", "台式小吃"]),
    "有時候-慢烤杏仁豆腐冰": ("dessert", []),
    "路咖啡Road Café/外帶咖啡吧": ("cafe", []),
    "京正拉麵(育樂店)": ("meal", ["日式", "麵食"]),
    "昆布食堂": ("meal", ["日式"]),
    "藝鍋物北門店": ("meal", ["火鍋"]),
    "鮨瑀壽司": ("meal", ["日式"]),
    "熟鍋": ("meal", ["火鍋"]),
    "KOEMON": ("cafe", []),
    "榕樹下璞味綿綿冰": ("dessert", []),
    "甜在心咖啡館": ("cafe", []),
    "NOTHING but coffee": ("cafe", []),
    "莘咖哩 Veganers World": ("meal", ["異國料理", "素食友善"]),
    "東安豆花": ("dessert", []),
    "MAO WANG 貓王龍貓餐廳": ("meal", ["西式義式", "宵夜"]),
    "91 Brunch": ("meal", ["早午餐"]),
    "艾麥全日早午餐": ("meal", ["早午餐"]),
    "QQ田甜品工坊(台南東安店)": ("dessert", []),
    "春禾日式鍋物": ("meal", ["火鍋", "日式"]),
    "啾醬 韓式炸雞 쮸짱치킨": ("meal", ["韓式", "宵夜"]),
    "洁茂牛肉麵館": ("meal", ["麵食"]),
    "賀也拉麵（育樂街）": ("meal", ["日式", "麵食"]),
    "邁滋味早午餐": ("meal", ["早午餐"]),
    "Pasta Now 鬧義麵 勝利店": ("meal", ["西式義式"]),
    "狐獴先生早午餐": ("meal", ["早午餐"]),
    "我們工作室": ("dessert", []),
    "路迷Lumi pasta&tea": ("meal", ["西式義式"]),
    "綿綿土司": ("meal", ["早午餐"]),
    "吉米THAI": ("meal", ["異國料理"]),
    "北園義法小館": ("meal", ["西式義式"]),
    "雄雄食社": ("dessert", []),
}
# Google 沒有提供每人消費金額的店，依類型估計
PRICE_GUESS = {"健康燒肉屋 貴一郎": 3, "得意吉義式冰淇淋": 1, "尼法": 3,
               "東安豆花": 1, "我們工作室": 1, "雄雄食社": 1}
SHORT = {"백년토종삼계탕 百年土種蔘雞湯 台南成大店": "百年土種蔘雞湯 成大店",
         "焼肉スマイル（燒肉Smile）台南成大店": "燒肉Smile 成大店",
         "麥雅印度咖喱 Maiya Indian Curry Halal": "麥雅印度咖喱",
         "米楠印度料理 Milan Indian Cuisine": "米楠印度料理",
         "動感滷味-東興店（台南創始總店）": "動感滷味 東興店",
         "啾醬 韓式炸雞 쮸짱치킨": "啾醬韓式炸雞",
         "泊飲茶館CHÂTEAU BLANC 長榮店": "泊飲茶館 長榮店",
         "路咖啡Road Café/外帶咖啡吧": "路咖啡 Road Café",
         "QQ田甜品工坊(台南東安店)": "QQ田甜品工坊",
         "便當翔 Bento Xiang 光明店": "便當翔 光明店"}
CAT_FIX = {"Pasta Now 鬧義麵 勝利店": "義大利麵餐廳", "路迷Lumi pasta&tea": "義大利麵餐廳",
           "北園義法小館": "義法料理"}


def budget(price):
    m = re.match(r"\$([\d,]+)", price)
    if not m:
        return None
    low = int(m.group(1).replace(",", ""))
    return 1 if low < 200 else 2 if low < 400 else 3


shops = []
for i, s in enumerate(raw):
    group, tags = TAGS[s["n"]]
    b = budget(s["price"]) or PRICE_GUESS[s["n"]]
    shops.append({
        "id": f"g{i:02d}", "name": SHORT.get(s["n"], s["n"]), "full": s["n"],
        "group": group, "tags": tags, "budget": b,
        "price": s["price"] or "（估計）", "rating": s["r"], "reviews": s["c"],
        "hot": s["c"] >= 2000, "dist": s["d"], "lat": s["lat"], "lng": s["lng"],
        "cat": CAT_FIX.get(s["n"], s["cat"]), "addr": s["addr"], "hours": s["h"],
    })

assert len(shops) == len(TAGS) == 63
html_path = ROOT / "index.html"
html = html_path.read_text(encoding="utf-8")
blob = json.dumps(shops, ensure_ascii=False, separators=(",", ":"))
html = re.sub(r"/\*SHOPS\*/.*?/\*END\*/", lambda _: "/*SHOPS*/" + blob + "/*END*/", html, flags=re.S)
html_path.write_text(html, encoding="utf-8")
from collections import Counter
print(len(shops), Counter(s["group"] for s in shops), Counter(s["budget"] for s in shops),
      sum(s["hot"] for s in shops), "hot")
