import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time

st.set_page_config(
    page_title="메키 DC 동향 분석기",
    page_icon="🍁",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.title-area { text-align: center; padding: 2rem 0 1rem; }
.title-area h1 { font-size: 2rem; font-weight: 700; color: #ffffff; }
.title-area p { color: #888; font-size: 0.95rem; margin-top: 0.3rem; }
.result-card { background: #1a1d27; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #2a2d3a; }
.trend-badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 20px; font-weight: 700; font-size: 1.1rem; margin-bottom: 1rem; }
.badge-부정 { background: #3d1a1a; color: #ff6b6b; border: 1px solid #ff6b6b44; }
.badge-납득 { background: #1a2d3d; color: #4dabf7; border: 1px solid #4dabf744; }
.badge-긍정 { background: #1a3d2a; color: #51cf66; border: 1px solid #51cf6644; }
.badge-혼재 { background: #2d2a1a; color: #fcc419; border: 1px solid #fcc41944; }
.section-label { color: #888; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 1rem 0 0.4rem; }
.section-content { color: #ddd; font-size: 0.95rem; line-height: 1.7; }
.post-item { background: #12151f; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.3rem 0; color: #bbb; font-size: 0.88rem; border-left: 3px solid #2a2d3a; }
.post-item.hot { border-left-color: #ff6b6b; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="title-area">
    <h1>🍁 메키 DC 동향 분석기</h1>
    <p>DC인사이드 메키 갤러리 반응을 AI로 분석합니다</p>
</div>
""", unsafe_allow_html=True)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

DC_URL    = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg"
DC_SEARCH = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg&s_type=search_subject_memo&s_keyword={kw}"

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://gall.dcinside.com",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Referer": "https://gall.dcinside.com",
        "Accept-Language": "ko-KR,ko;q=0.9",
    },
]

def fetch_dc(keyword="", max_posts=100):
    url = DC_SEARCH.format(kw=requests.utils.quote(keyword)) if keyword else DC_URL
    posts = []
    for headers in HEADERS_LIST:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("tr.ub-content")
            if not rows:
                continue
            for row in rows[:max_posts]:
                title_el = row.select_one("td.gall_tit a:not(.reply_num)")
                date_el  = row.select_one("td.gall_date")
                rec_el   = row.select_one("td.gall_recommend")
                view_el  = row.select_one("td.gall_count")
                if not title_el:
                    continue
                try:
                    rec = int(rec_el.get_text(strip=True) or 0) if rec_el else 0
                except:
                    rec = 0
                try:
                    views = int(view_el.get_text(strip=True).replace(",","") or 0) if view_el else 0
                except:
                    views = 0
                posts.append({
                    "title":  title_el.get_text(strip=True),
                    "date":   date_el.get_text(strip=True) if date_el else "",
                    "recomm": rec,
                    "views":  views,
                })
            if posts:
                break
        except Exception as e:
            continue
    return posts

def analyze(issue_text, posts):
    client = genai.Client(api_key=GEMINI_API_KEY)
    post_lines = "\n".join([
        f"- [추천{p['recomm']} / 조회{p['views']}] {p['title']}"
        for p in posts[:80]
    ]) if posts else "수집된 글 없음"

    prompt = f"""
당신은 게임 커뮤니티 동향 분석 전문가입니다.
아래 이슈와 DC인사이드 메키 갤러리 반응을 분석해서 JSON으로만 답하세요. 백틱 없이 순수 JSON만 반환하세요.
DC 수집 글이 없으면 이슈 내용만으로 분석하세요.

[분석할 이슈]
{issue_text}

[DC인사이드 갤러리 글 목록]
{post_lines}

반환 JSON:
{{
  "주요_동향": "납득 | 긍정 | 부정 | 혼재 중 하나",
  "동향_요약": "전체 분위기 2~3문장 요약",
  "긍정_반응": "긍정적 반응 요약 (없으면 없음)",
  "부정_반응": "부정적 반응 요약 (없으면 없음)",
  "주요_키워드": ["키워드1", "키워드2", "키워드3"],
  "대표_반응_제목": ["가장 반응 큰 글 제목 3개"],
  "분석_근거": "판단 근거 한 문장"
}}
"""
    import json, re
    try:
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        text = re.sub(r"^```json\s*|```$", "", resp.text.strip(), flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Gemini 분석 실패: {e}")
        return None

# ── UI ──
col1, col2 = st.columns([4, 1])
with col1:
    issue_input = st.text_input("", placeholder="이슈 내용 입력 (예: 아레나 콜로세움 수치 오류)", label_visibility="collapsed")
with col2:
    run_btn = st.button("분석", use_container_width=True, type="primary")

also_search_dc = st.checkbox("DC 갤러리 최신 글도 함께 분석", value=True)

if run_btn and issue_input:
    with st.spinner("DC 갤러리 수집 중..."):
        keywords = issue_input.split()[:3]
        posts = []
        for kw in keywords:
            posts += fetch_dc(keyword=kw, max_posts=30)
            time.sleep(0.3)
        if also_search_dc:
            posts += fetch_dc(max_posts=100)
        seen = set()
        unique_posts = []
        for p in posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique_posts.append(p)

    st.markdown(f"<div style='color:#666;font-size:0.85rem;margin-bottom:1rem'>수집된 글: {len(unique_posts)}건</div>", unsafe_allow_html=True)

    if len(unique_posts) == 0:
        st.warning("DC 갤러리 수집이 안 됐어요. 이슈 내용만으로 분석합니다.")

    with st.spinner("Gemini 분석 중..."):
        result = analyze(issue_input, unique_posts)

    if result:
        trend = result.get("주요_동향", "")
        badge_class = f"badge-{trend}" if trend in ["부정","납득","긍정","혼재"] else "badge-혼재"

        st.markdown(f"""
        <div class="result-card">
            <span class="trend-badge {badge_class}">{trend}</span>
            <div class="section-label">동향 요약</div>
            <div class="section-content">{result.get("동향_요약","")}</div>
            <div class="section-label">긍정 반응</div>
            <div class="section-content">{result.get("긍정_반응","")}</div>
            <div class="section-label">부정 반응</div>
            <div class="section-content">{result.get("부정_반응","")}</div>
            <div class="section-label">분석 근거</div>
            <div class="section-content" style="color:#888;font-style:italic">{result.get("분석_근거","")}</div>
        </div>
        """, unsafe_allow_html=True)

        kws = result.get("주요_키워드", [])
        if kws:
            kw_html = " ".join([f"<span style='background:#1e2130;border:1px solid #333;border-radius:20px;padding:0.2rem 0.7rem;color:#aaa;font-size:0.85rem'>{k}</span>" for k in kws])
            st.markdown(f"<div style='margin:0.5rem 0'>{kw_html}</div>", unsafe_allow_html=True)

        rep = result.get("대표_반응_제목", [])
        if rep:
            st.markdown("<div class='section-label' style='margin-top:1.2rem'>대표 반응 글</div>", unsafe_allow_html=True)
            for title in rep:
                st.markdown(f"<div class='post-item hot'>💬 {title}</div>", unsafe_allow_html=True)

        top_posts = sorted(unique_posts, key=lambda x: x["recomm"], reverse=True)[:5]
        if any(p["recomm"] > 0 for p in top_posts):
            st.markdown("<div class='section-label' style='margin-top:1.2rem'>추천 TOP 5</div>", unsafe_allow_html=True)
            for p in top_posts:
                if p["recomm"] > 0:
                    st.markdown(f"<div class='post-item'>👍 {p['recomm']} · {p['title']}</div>", unsafe_allow_html=True)

elif run_btn and not issue_input:
    st.warning("이슈 내용을 입력해주세요.")
