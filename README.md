# 成醫美食輪盤

今天吃什麼？成大醫學院 1.2 公里內、Google 評分 ≥ 4.6、評論超過 200 則的 63 家店，**只抽現在有開的店**。

- 規格書：[SPEC.md](SPEC.md)
- 單一 `index.html`，HTML／CSS／JavaScript 全部寫在同一個檔案；輪盤用 canvas 手刻，不使用任何函式庫。
- 店家資料（2026-10-18 整理自 Google 地圖）：`data/shops_raw.json`；`data/build.py` 會加上分類並嵌入 index.html。

![screenshot](screenshot.png)
