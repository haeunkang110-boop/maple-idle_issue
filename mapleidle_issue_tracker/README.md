# 메키 이슈 히스토리 자동 수집기

넥슨 커뮤니티 공지 + DC인사이드 반응을 매일 자동 수집해서 엑셀로 저장합니다.

## 세팅 방법 (최초 1회)

### 1. 이 레포 Fork 또는 Use this template

### 2. Gemini API 키 등록
1. [Google AI Studio](https://aistudio.google.com/app/apikey) → **Get API Key** → 키 복사
2. GitHub 레포 → **Settings → Secrets and variables → Actions**
3. **New repository secret** 클릭
   - Name: `GEMINI_API_KEY`
   - Secret: 복사한 키 붙여넣기

### 3. Actions 권한 설정
GitHub 레포 → **Settings → Actions → General**
→ **Workflow permissions** → **Read and write permissions** 선택 → Save

---

## 실행

| 방법 | 설명 |
|---|---|
| 자동 | 매일 오전 9시 KST 자동 실행 |
| 수동 | Actions 탭 → **메키 이슈 히스토리 수집** → **Run workflow** |

실행 후 레포 루트에 `meki_이슈_히스토리.xlsx` 파일이 생성/업데이트됩니다.

---

## 수집 항목

| 컬럼 | 출처 |
|---|---|
| 발생일, 이슈 상세, 대응/보상 내용 | 넥슨 커뮤니티 공지 |
| 이슈 구분, 핵심 요약 | Gemini 자동 분류 |
| 주요 동향 (납득/긍정/부정/혼재) | DC인사이드 반응 → Gemini 분석 |
| 비고 | 동향 판단 근거 |
