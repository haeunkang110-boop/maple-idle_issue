"""
GitHub Actions 실행용 DC 수집 + Gemini 분석 스크립트
결과를 docs/index.html로 저장 (GitHub Pages)
"""

import os, re, json, time, datetime
import requests
from bs4 import BeautifulSoup
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ISSUE_INPUT    = os.environ.get("ISSUE_INPUT", "이슈 없음")

DC_URL    = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg"
DC_SEARCH = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg&s_type=search_subject_memo&s_keyword={kw}"
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://gall.dcinside.com",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

def fetch_dc(keyword="", max_posts=100):
    url = DC_SEARCH.format(kw=requests.utils.quote(keyword)) if keyword else DC_URL
    posts = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("tr.ub-content")[:max_posts]:
            title_el = row.select_one("td.gall_tit a:not(.reply_num)")
            date_el  = row.select_one("td.gall_date")
            rec_el   = row.select_one("td.gall_recommend")
            view_el  = row.select_one("td.gall_count")
            if not title_el:
                continue
            try: rec = int(rec_el.get_text(strip=True) or 0)
            except: rec = 0
            try: views = int(view_el.get_text(strip=True).replace(",","") or 0)
            except: views = 0
            posts.append({
                "title": title_el.get_text(strip=True),
                "date":  date_el.get_text(strip=True) if date_el else "",
                "recomm": rec,
                "views": views,
            })
    except Exception as e:
        print(f"[WARN] DC 수집 실패: {e}")
    return posts

def analyze(issue_text, posts):
    client = genai.Client(api_key=GEMINI_API_KEY)
    post_lines = "\n".join([
        f"- [추천{p['recomm']}/조회{p['views']}] {p['title']}"
        for p in posts[:80]
    ]) or "없음"
    prompt = f"""
게임 커뮤니티 동향 분석 전문가로서 아래 이슈와 DC인사이드 메키 갤러리 반응을 분석하세요.
백틱 없이 순수 JSON만 반환하세요.

[이슈]
{issue_text}

[DC 갤러리 글]
{post_lines}

반환 JSON:
{{
  "주요_동향": "납득 | 긍정 | 부정 | 혼재 중 하나",
  "동향_요약": "전체 분위기 2~3문장",
  "긍정_반응": "긍정 반응 요약 (없으면 없음)",
  "부정_반응": "부정 반응 요약 (없으면 없음)",
  "주요_키워드": ["키워드1", "키워드2", "키워드3"],
  "대표_반응": ["핵심 반응 3개"],
  "분석_근거": "판단 근거 한 문장"
}}
"""
    try:
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        text = re.sub(r"^```json\s*|```$", "", resp.text.strip(), flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f"[WARN] Gemini 실패: {e}")
        return None

def load_history():
    try:
        with open("docs/history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    os.makedirs("docs", exist_ok=True)
    with open("docs/history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def trend_color(trend):
    return {"부정": "#ff6b6b", "납득": "#4dabf7", "긍정": "#51cf66", "혼재": "#fcc419"}.get(trend, "#aaa")

def trend_bg(trend):
    return {"부정": "#3d1a1a", "납득": "#1a2d3d", "긍정": "#1a3d2a", "혼재": "#2d2a1a"}.get(trend, "#1a1d27")

def build_html(history):
    cards = ""
    for item in reversed(history):
        trend = item.get("주요_동향", "")
        color = trend_color(trend)
        bg    = trend_bg(trend)
        kws   = " ".join([f'<span style="background:#1e2130;border:1px solid #333;border-radius:20px;padding:2px 10px;color:#aaa;font-size:13px">{k}</span>' for k in item.get("주요_키워드", [])])
        reps  = "".join([f'<div style="background:#0d0f18;border-left:3px solid {color};border-radius:6px;padding:8px 12px;margin:4px 0;color:#bbb;font-size:14px">💬 {r}</div>' for r in item.get("대표_반응", [])])
        cards += f"""
<div style="background:#1a1d27;border-radius:12px;padding:24px;margin:16px 0;border:1px solid #2a2d3a">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
    <span style="background:{bg};color:{color};border:1px solid {color}44;border-radius:20px;padding:4px 14px;font-weight:700;font-size:16px">{trend}</span>
    <span style="color:#555;font-size:13px">{item.get('날짜','')} · {item.get('수집건수',0)}건 수집</span>
  </div>
  <div style="color:#888;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px">이슈</div>
  <div style="color:#fff;font-size:16px;font-weight:600;margin-bottom:16px">{item.get('이슈','')}</div>
  <div style="color:#888;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px">동향 요약</div>
  <div style="color:#ddd;font-size:14px;line-height:1.7;margin-bottom:16px">{item.get('동향_요약','')}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
    <div>
      <div style="color:#888;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px">긍정 반응</div>
      <div style="color:#ddd;font-size:14px;line-height:1.7">{item.get('긍정_반응','')}</div>
    </div>
    <div>
      <div style="color:#888;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px">부정 반응</div>
      <div style="color:#ddd;font-size:14px;line-height:1.7">{item.get('부정_반응','')}</div>
    </div>
  </div>
  <div style="margin-bottom:12px">{kws}</div>
  {reps}
  <div style="color:#555;font-size:12px;font-style:italic;margin-top:12px">{item.get('분석_근거','')}</div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍁 메키 DC 동향 분석</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f1117; color: #ddd; font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; padding: 24px; }}
  .container {{ max-width: 800px; margin: 0 auto; }}
  h1 {{ font-size: 24px; font-weight: 700; color: #fff; text-align: center; padding: 32px 0 8px; }}
  .subtitle {{ color: #555; font-size: 14px; text-align: center; margin-bottom: 32px; }}
  .empty {{ text-align: center; color: #555; padding: 80px 0; font-size: 16px; }}
</style>
</head>
<body>
<div class="container">
  <h1>🍁 메키 DC 동향 분석</h1>
  <p class="subtitle">DC인사이드 메키 마이너 갤러리 반응 AI 분석 · 총 {len(history)}건</p>
  {''.join([cards]) if history else '<div class="empty">아직 분석 결과가 없어요.<br>GitHub Actions에서 Run workflow를 실행해주세요.</div>'}
</div>
</body>
</html>"""

def main():
    print(f"=== 이슈: {ISSUE_INPUT} ===")

    # DC 수집
    print("[1/3] DC 수집 중...")
    keywords = ISSUE_INPUT.split()[:3]
    posts = []
    for kw in keywords:
        posts += fetch_dc(keyword=kw, max_posts=30)
        time.sleep(0.5)
    posts += fetch_dc(max_posts=100)
    seen, unique = set(), []
    for p in posts:
        if p["title"] not in seen:
            seen.add(p["title"])
            unique.append(p)
    print(f"  → {len(unique)}건")

    # Gemini 분석
    print("[2/3] Gemini 분석 중...")
    result = analyze(ISSUE_INPUT, unique)
    if not result:
        print("[ERROR] 분석 실패")
        return

    # 히스토리 저장
    print("[3/3] 결과 저장 중...")
    history = load_history()
    history.append({
        "이슈": ISSUE_INPUT,
        "날짜": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "수집건수": len(unique),
        **result
    })
    save_history(history)

    # HTML 생성
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(build_html(history))

    print(f"=== 완료 ===")

if __name__ == "__main__":
    main()
