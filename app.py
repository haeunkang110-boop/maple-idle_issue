import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time

# ── 페이지 설정 ──
st.set_page_config(
    page_title="메키 DC 동향 분석기",
    page_icon="🍁",
    layout="centered"
)

# ── 스타일 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.main { background-color: #0f1117; }

.title-area {
    text-align: center;
    padding: 2rem 0 1rem;
}
.title-area h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}
.title-area p {
    color: #888;
    font-size: 0.95rem;
    margin-top: 0.3rem;
}

.result-card {
    background: #1a1d27;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    border: 1px solid #2a2d3a;
}

.trend-badge {
    display: inline-block;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-weight: 700;
    font-size: 1.1rem;
    margin-bottom: 1rem;
}
.badge-부정 { background: #3d1a1a; color: #ff6b6b; border: 1px solid #ff6b6b44; }
.badge-납득 { background: #1a2d3d; color: #4dabf7; border: 1px solid #4dabf744; }
.badge-긍정 { background: #1a3d2a; color: #51cf66; border: 1px solid #51cf6644; }
.badge-혼재 { background: #2d2a1a; color: #fcc419; border: 1px solid #fcc41944; }

.section-label {
    color: #888;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 1rem 0 0.4rem;
}
.section-content {
    color: #ddd;
    font-size: 0.95rem;
    line-height: 1.7;
}

.post-item {
    background: #12151f;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    margin: 0.3rem 0;
    color: #bbb;
    font-size: 0.88rem;
    border-left: 3px solid #2a2d3a;
}
.post-item.hot { border-left-color: #ff6b6b; }

.stat-row {
    display: flex;
    gap: 1rem;
    margin: 0.5rem 0 1rem;
}
.stat-box {
    flex: 1;
    background: #12151f;
    border-radius: 8px;
    padding: 0.7rem;
    text-align: center;
}
.stat-num { font-size: 1.4rem; font-weight: 700; color: #fff; }
.stat-label { font-size: 0.75rem; color: #666; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ── 타이틀 ──
st.markdown("""
<div class="title-area">
    <h1>🍁 메키 DC 동향 분석기</h1>
    <p>DC인사이드 메키 갤러리 반응을 AI로 분석합니다</p>
</div>
""", unsafe_allow_html=True)

# ── Gemini API 키 ──
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다. Streamlit Secrets에 추가해주세요.")
    st.stop()

DC_URL    = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg"
DC_SEARCH = "https://gall.dcinside.com/mgallery/board/lists?id=maplerpg&s_type=search_subject_memo&s_keyword={kw}"
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://gall.dcinside.com",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── DC 수집 ──
def fetch_dc(keyword="", max_posts=100):
    url = DC_SEARCH.format(kw=requests.utils.quote(keyword)) if keyword else DC_URL
    posts = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("tr.ub-content")[:max_posts]:
            title_el = row.select_one("td.gall_tit a:not(.reply_num)")
            date_el  = row.select_one("td.gall_date")
            rec_el   = row.select_one("td.gall_recommend")
            view_el  = row.select_one("td.gall_count")
            if not title_el:
                continue
            posts.append({
                "title":  title_el.get_text(strip=True),
                "date":   date_el.get_text(strip=True) if date_el else "",
                "recomm": int(rec_el.get_text(strip=True) or 0) if rec_el else 0,
                "views":  int(view_el.get_text(strip=True).replace(",","") or 0) if view_el else 0,
            })
    except Exception as e:
        st.warning(f"DC 수집 실패: {e}")
    return posts

# ── Gemini 분석 ──
def analyze(issue_text, posts):
    client = genai.Client(api_key=GEMINI_API_KEY)
    post_lines = "\n".join([
        f"- [추천{p['recomm']} / 조회{p['views']}] {p['title']}"
        for p in posts[:80]
    ])
    prompt = f"""
당신은 게임 커뮤니티 동향 분석 전문가입니다.
아래 이슈와 DC인사이드 메키 갤러리 반응을 분석해서 JSON으로만 답하세요. 백틱 없이 순수 JSON만 반환하세요.

[분석할 이슈]
{issue_text}

[DC인사이드 갤러리 글 목록 (추천수/조회수 포함)]
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
    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        import json, re
        text = re.sub(r"^```json\s*|```$", "", resp.text.strip(), flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Gemini 분석 실패: {e}")
        return None

# ── UI ──
col1, col2 = st.columns([4, 1])
with col1:
    issue_input = st.text_input(
        "",
        placeholder="이슈 내용 입력 (예: 아레나 수치 오류 보상 지급)",
        label_visibility="collapsed"
    )
with col2:
    run_btn = st.button("분석", use_container_width=True, type="primary")

also_search_dc = st.checkbox("DC 갤러리 최신 글도 함께 분석", value=True)

if run_btn and issue_input:
    with st.spinner("DC 갤러리 수집 중..."):
        # 키워드 검색
        keywords = issue_input.split()[:3]
        posts = []
        for kw in keywords:
            posts += fetch_dc(keyword=kw, max_posts=30)
            time.sleep(0.3)

        # 최신 글도 수집
        if also_search_dc:
            posts += fetch_dc(max_posts=100)

        # 중복 제거
        seen = set()
        unique_posts = []
        for p in posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique_posts.append(p)

    st.markdown(f"<div style='color:#666; font-size:0.85rem; margin-bottom:1rem'>수집된 글: {len(unique_posts)}건</div>", unsafe_allow_html=True)

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
            <div class="section-content" style="color:#888; font-style:italic">{result.get("분석_근거","")}</div>
        </div>
        """, unsafe_allow_html=True)

        # 키워드
        keywords_result = result.get("주요_키워드", [])
        if keywords_result:
            kw_html = " ".join([f"<span style='background:#1e2130;border:1px solid #333;border-radius:20px;padding:0.2rem 0.7rem;color:#aaa;font-size:0.85rem'>{k}</span>" for k in keywords_result])
            st.markdown(f"<div style='margin:0.5rem 0'>{kw_html}</div>", unsafe_allow_html=True)

        # 대표 반응
        rep = result.get("대표_반응_제목", [])
        if rep:
            st.markdown("<div class='section-label' style='margin-top:1.2rem'>대표 반응 글</div>", unsafe_allow_html=True)
            for title in rep:
                st.markdown(f"<div class='post-item hot'>💬 {title}</div>", unsafe_allow_html=True)

        # 추천 많은 글 TOP5
        top_posts = sorted(unique_posts, key=lambda x: x["recomm"], reverse=True)[:5]
        if any(p["recomm"] > 0 for p in top_posts):
            st.markdown("<div class='section-label' style='margin-top:1.2rem'>추천 TOP 5</div>", unsafe_allow_html=True)
            for p in top_posts:
                if p["recomm"] > 0:
                    st.markdown(f"<div class='post-item'>👍 {p['recomm']} · {p['title']}</div>", unsafe_allow_html=True)

elif run_btn and not issue_input:
    st.warning("이슈 내용을 입력해주세요.")
