from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from datetime import datetime
from playwright.sync_api import sync_playwright

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 起動時に一度だけブラウザを立ち上げる
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
context = browser.new_context()

@app.on_event("shutdown")
def shutdown():
    browser.close()
    playwright.stop()

@app.get("/odds", response_class=PlainTextResponse)
def get_odds(venue: str, race: str):
    now = datetime.now()
    current_time = now.hour + now.minute / 60
    if not (8 <= current_time <= 23.5):
        return PlainTextResponse("❌ 利用可能時間は8:00〜23:30です", status_code=403)

    venue_codes = {
        "函館": "11", "青森": "12", "いわき平": "13", "弥彦": "21", "前橋": "22", "取手": "23",
        "宇都宮": "24", "大宮": "25", "西武園": "26", "京王閣": "27", "立川": "28", "松戸": "31",
        "川崎": "34", "平塚": "35", "小田原": "36", "伊東": "37", "伊東温泉": "37", "静岡": "38",
        "名古屋": "42", "岐阜": "43", "大垣": "44", "豊橋": "45", "富山": "46", "松阪": "47",
        "四日市": "48", "福井": "51", "奈良": "53", "向日町": "54", "和歌山": "55", "岸和田": "56",
        "玉野": "61", "広島": "62", "防府": "63", "高松": "71", "小松島": "73", "高知": "74",
        "松山": "75", "小倉": "81", "久留米": "83", "武雄": "84", "佐世保": "85", "別府": "86", "熊本": "87"
    }

    venue_id = venue_codes.get(venue)
    if not venue_id:
        return f"❌ 無効な会場名: {venue}"

    date = now.strftime("%Y%m%d")
    race_id = f"{date}{venue_id}{str(race).zfill(2)}"
    url = f"https://keirin.netkeiba.com/race/odds/?race_id={race_id}&type=odds3tan"

    page = context.new_page()

    def block_resource(route, request):
        if request.resource_type in ["image", "stylesheet", "font"]:
            route.abort()
        else:
            route.continue_()

    page.route("**/*", block_resource)

    try:
        page.goto(url, timeout=10000)
        page.wait_for_selector("table.OddsTable", timeout=5000)
        rows = page.query_selector_all("table.OddsTable tbody tr")
        result_lines = ["順位,組番,オッズ"]
        for i, row in enumerate(rows[:100]):
            cols = row.query_selector_all("td")
            if len(cols) >= 3:
                combo = cols[0].inner_text().strip().replace("-", "")
                odds = cols[2].inner_text().strip().replace("倍", "")
                result_lines.append(f"{i+1},{combo},{odds}")
        page.close()
    except Exception as e:
        page.close()
        return f"❌ オッズ取得エラー: {str(e)}"

    if len(result_lines) == 1:
        return "❌ オッズ情報が見つかりませんでした"

    return "\n".join(result_lines)
