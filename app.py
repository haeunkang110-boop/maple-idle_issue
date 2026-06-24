import streamlit as st
from google import genai
import re, json

st.set_page_config(page_title="메키 DC 동향 분석기", page_icon="🍁", layout="centered")

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
.post-item { background: #12151f; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.3rem 0; color: #bbb; font-size: 0.88rem; border-left: 3px solid #ff6b6b; }
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

def analyze(issue_text, dc_text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
당신은 게임 커뮤니티 동향 분석 전문가입니다.
아래 이슈와 DC인사이드 메키 갤러리 반응을 분석해서 JSON으로만 답하세요. 백틱 없이 순수 JSON만 반환하세요.

[분석할 이슈]
{issue_text}

[DC인사이드 갤러리 글/반응]
{dc_text if dc_text.strip() else "없음 - 이슈 내용만으로 분석"}

반환 JSON:
{{
  "주요_동향": "납득 | 긍정 | 부정 | 혼재 중 하나",
  "동향_요약": "전체 분위기 2~3문장 요약",
  "긍정_반응": "긍정적 반응 요약 (없으면 없음)",
  "부정_반응": "부정적 반응 요약 (없으면 없음)",
  "주요_키워드": ["키워드1", "키워드2", "키워드3"],
  "대표_반응": ["핵심 반응 문장 3개"],
  "분석_근거": "판단 근거 한 문장"
}}
"""
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = re.sub(r"^```json\s*|```$", "", resp.text.strip(), flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Gemini 분석 실패: {e}")
        return None

# ── 입력 ──
st.markdown("#### 이슈 내용")
issue_input = st.text_input("", placeholder="예: 아레나/콜로세움 수치 적용 오류로 보상 대량 지급", label_visibility="collapsed")

st.markdown("#### DC 갤러리 반응")
st.caption("갤러리에서 글 제목이나 댓글을 복사해서 붙여넣으세요. 많을수록 정확해요.")
dc_input = st.text_area("", placeholder="예:\n- 아레나 수치 오류 넥슨 또 사고쳤네\n- 보상이 너무 적다 환불각\n- 이 정도면 납득함 빠른 대응이었음\n...", height=200, label_visibility="collapsed")

run_btn = st.button("동향 분석", use_container_width=True, type="primary")

if run_btn:
    if not issue_input:
        st.warning("이슈 내용을 입력해주세요.")
    else:
        with st.spinner("Gemini 분석 중..."):
            result = analyze(issue_input, dc_input)

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

            reps = result.get("대표_반응", [])
            if reps:
                st.markdown("<div class='section-label' style='margin-top:1.2rem'>대표 반응</div>", unsafe_allow_html=True)
                for r in reps:
                    st.markdown(f"<div class='post-item'>💬 {r}</div>", unsafe_allow_html=True)
