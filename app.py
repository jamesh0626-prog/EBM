import streamlit as st
import os
import tempfile
from pathlib import Path

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="EBM Worksheet 자동 생성기",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── EBM 시스템 프롬프트 ───────────────────────────────────────
SYSTEM_PROMPT = """# Role: 근거중심의학(EBM) 다중 파일 분석 및 오답 예방 전문가

# Purpose:
사용자가 업로드한 [새로운 블록 논문 파일]과 [이전 블록의 채점 피드백 파일(PDF 또는 캡처 이미지)]을 동시에 분석한다. 이전 피드백 파일에서 감점 요인과 지적 사항을 스스로 추출하여 '새 과제 작성 지침'으로 삼고, 고정된 EBM 워크시트 양식에 맞춰 무결점 한국어 답안을 생성한다.

# Input Guide:
1. **새 논문 파일**: 이번 블록에 배정된 의학 RCT 논문 (PDF)
2. **이전 피드백 파일**: 과거 블록에서 감점당한 과제 PDF 또는 조교/교수님의 코멘트가 적힌 화면 캡처 이미지 (PNG/JPG/PDF)
   - 지침: 피드백 이미지나 PDF에 적힌 빨간 펜 글씨, 감점 점수, 텍스트 코멘트를 시각적으로 정확히 분석하여 무엇이 잘못되었었는지 파악할 것.

# Strict Constraints:
1. **오답 노트를 기반으로 한 자기 검열**: 이전 피드백 파일에서 지적된 오류가 이번 새 과제에서 절대 재발하지 않도록 철저히 검증하십시오.
2. **언어 규칙**: 모든 본문 문장은 한국어로 작성. 약물 이름 및 핵심 의학 고유 명사는 영어 원어로 표기.
3. **수식 및 계산**: 통계학적 수치(ARR, NNT, NNH, 95% CI)는 정확하게 계산하고 LaTeX 포맷($inline$ 또는 $$display$$)을 사용하여 표현.
4. **근거 명시**: '예/아니오' 판단 문항에는 논문의 구체적인 수치나 방법론을 근거로 제시.

# Output Format (반드시 아래 양식 그대로 출력):

## 🚨 업로드된 피드백 파일 분석 결과 (AI 오답 체크리스트)
* **이전 파일에서 감지된 감점 요인**: [업로드된 피드백 PDF/이미지에서 찾아낸 구체적인 지적 사항 요약]
* **이번 과제 적용 방향**: [위의 실수를 방지하기 위해 이번 논문 분석 시 강화한 점]

## 과제 1. 답변 가능한 임상질문 만들기 (PICO)
* **P (Patient & Problem):** [대상 환자군 및 질병적 특성]
* **I (Intervention):** [시험군 치료법/약물명 및 용량]
* **C (Comparison):** [대조군 치료법 또는 Placebo]
* **O (Outcome):** [최종 평가 결과 및 지표]

## 과제 2. 검색어 선정
* **Keywords:** [PICO에 기반한 핵심 영어 검색어 5개를 쉼표로 구분]

## 과제 3. 문헌 비평과 적용

### 1. 임상시험의 결과는 타당한가? (Internal Validity)
* **치료에 대한 환자 배정은 무작위적인가?** [예/아니오] - 근거:
* **환자에 대한 추적관찰은 충분히 완전한가?** [예/아니오] - 근거: [중도 탈락율 및 Complete rate 수치 포함]
* **환자에 대한 추적관찰은 질병결과를 관찰하기에 충분히 긴가?** [예/아니오] - 근거: [치료 및 관찰 기간 명시]
* **환자는 모두 애초에 무작위 배정된 군에 따라 분석되었는가? (Intention to treat analysis)** [예/아니오] - 근거: [FAS 또는 ITT 분석 적용 여부]
* **이중 맹검법이 시행되는가?** [예/아니오] - 근거:
* **각 군은 시험의 대상이 되는 치료법 외에는 모든 측면에서 동일하게 취급되었는가?** [예/아니오] - 근거:
* **각 군은 임상시험의 시작단계에서 유사하였는가?** [예/아니오] - 근거: [Baseline characteristics 유사성 언급]

### 2. 해당 연구의 결과가 임상적으로 중요한가?
(주요 효과 지표인 Primary Outcome을 기준으로 산출 과정을 명시할 것)
* **Outcome 항목:** [Primary Outcome 명칭]
* **CER (Control Event Rate):**
* **EER (Experimental Event Rate):**
* **RRR (Relative Risk Reduction):** $$\\frac{CER - EER}{CER} = \\text{결과값}$$
* **ARR (Absolute Risk Reduction):** $$CER - EER = \\text{결과값}$$
* **NNT (Number Needed to Treat):** $$\\frac{1}{ARR} = \\text{결과값}$$
* **치료효과에 대한 추정의 정밀도 (95% CI of ARR):**
  - $S.E = \\sqrt{\\frac{CER(1-CER)}{N_1} + \\frac{EER(1-EER)}{N_2}} = \\text{수치}$
  - $95\\% \\text{ CI of ARR} = ARR \\pm 1.96 \\times S.E. = [\\text{하한값}, \\text{상한값}]$

### 3. 치료에 따른 부작용은 어느 정도인가?
(가장 빈번하거나 임상적으로 중대한 주요 부작용 지표를 선정)
* **주요 부작용 항목:**
* **CER:** | **EER:**
* **RRI (Relative Risk Increase):** $$\\frac{EER - CER}{CER} = \\text{결과값}$$
* **ARI (Absolute Risk Increase):** $$|EER - CER| = \\text{결과값}$$
* **NNH (Number Needed to Harm):** $$\\frac{1}{ARI} = \\text{결과값}$$

### 4. 해당 연구의 결과를 실제 환자에게 적용할 수 있는가?
* **제시된 연구결과를 적용하지 못할 정도로 실제환자와 연구대상 간에 차이가 존재하는가?** [예/아니오] - 이유:
* **다른 치료법은 없는가?** [예/아니오] - 이유:
* **해당 치료법 적용 시 실제 환자에서 기대되는 잠재적인 편익과 손실 (f-factor 평가):**
  - $f_{\\text{treatment}}$ (치료 반응 가중치) = [이유와 수치]
  - $f_{\\text{adverse effect}}$ (부작용 가중치) = [이유와 수치]
  - 실제환자의 $NNT_{\\text{patient}} = \\frac{NNT}{f_{\\text{treatment}}} = \\text{결과값}$
  - 실제환자의 $NNH_{\\text{patient}} = \\frac{NNH}{f_{\\text{adverse effect}}} = \\text{결과값}$
* **치료법 자체와 질병치료결과가 실제 환자에게 가지는 가치와 기대 (s-factor 및 LHH 구하기):**
  - **Rating scale 1) 값** (치료 없을 때 질병결과 심각도, 0=사망/완전장애~1.0=완치): [0~1.0 사이 수치] — 이유: [근거]
  - **Rating scale 2) 값** (치료 부작용 수용도, 0=전혀 수용 못함~1.0=완전 수용): [0~1.0 사이 수치] — 이유: [근거]
  - $s = \\frac{2)\\text{값}}{1)\\text{값}} = [계산 결과]$
  - $LHH = [(\\frac{1}{NNT}) \\times f \\times s] \\text{ vs } [(\\frac{1}{NNH}) \\times f] = \\text{비교 결과}$
* **결론:** 위의 분석에 근거하여 환자에게 위의 치료를 하도록 권고할 것인가? [예/아니오 및 종합 소견]

## DISCUSSION
1. **앞에서 분석한 논문이 가지고 있는 문제점이나 제한점:** [심도 있게 기술]
2. **이러한 제한점을 보완하기 위하여 어떤 근거가 더 필요하겠는가:**"""

USER_PROMPT = """위의 양식에 맞춰 업로드된 파일들을 분석하여 EBM 워크시트를 완성해주세요.

- 첫 번째 파일: 이번 블록의 새 논문입니다.
- 두 번째 파일 이후: 이전 블록의 채점 피드백입니다. 이 파일에서 감점 요인을 추출하여 오답 체크리스트에 반영하고, 같은 실수가 반복되지 않도록 하십시오.

모든 계산 과정을 명시적으로 보여주고, LaTeX 수식을 사용하여 표현하십시오.
Rating scale 1)값과 2)값은 반드시 0~1.0 사이의 구체적인 수치로 제시하고, 그 근거를 명시하십시오."""

MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

CHAT_SYSTEM = """당신은 EBM(근거중심의학) 전문가입니다.
아래는 방금 생성된 EBM 워크시트입니다. 사용자의 질문에 답하거나 수정 요청을 처리합니다.

**응답 규칙:**
1. 질문에는 간결하게 답하세요 (3~5문장, 핵심만).
2. 수정 요청이면, 변경된 섹션만 출력하되 반드시 앞에 "### ✏️ 수정됨: [섹션명]" 을 붙이세요.
3. 전체 워크시트를 재출력하지 마세요 — 변경된 부분만 표시하세요.
4. 한국어로 답하되 약물명·의학 고유명사는 영어로.

--- 생성된 워크시트 ---
{worksheet}
--- 워크시트 끝 ---"""


def get_api_key() -> str:
    try:
        key = st.secrets.get("GOOGLE_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        key = os.environ.get("GOOGLE_API_KEY", "")
    return key


def stream_analysis(api_key: str, paper_file, feedback_files: list):
    """파일 업로드 후 Gemini 스트리밍 응답을 yield하는 제너레이터"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    uploaded = []
    tmp_paths = []

    def upload(file_obj):
        ext = Path(file_obj.name).suffix.lower()
        mime = MIME_MAP.get(ext, "application/octet-stream")
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_obj.read())
            tmp_path = tmp.name
        tmp_paths.append(tmp_path)
        return client.files.upload(
            file=tmp_path,
            config={"mime_type": mime, "display_name": file_obj.name},
        )

    try:
        paper_upload = upload(paper_file)
        uploaded.append(("새 논문", paper_upload))

        for i, fb in enumerate(feedback_files, 1):
            fb_upload = upload(fb)
            uploaded.append((f"피드백 {i}", fb_upload))

        contents = []
        for label, f in uploaded:
            contents.append(f"**[{label} 파일]**")
            contents.append(f)
        contents.append(USER_PROMPT)

        for chunk in client.models.generate_content_stream(
            model="gemini-3.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=32000,
                temperature=0.3,
            ),
        ):
            if chunk.text:
                yield chunk.text

    finally:
        for p in tmp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass


def get_chat_response(api_key: str, worksheet: str, chat_history: list) -> str:
    """워크시트 Q&A — 변경 시 변경된 섹션만 반환"""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    system = CHAT_SYSTEM.format(worksheet=worksheet)

    # 대화 이력을 Gemini contents 형식으로 변환
    contents = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg["content"])])
        )

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=4000,
            temperature=0.3,
        ),
    )
    return response.text or "(응답 없음)"


# ── UI ───────────────────────────────────────────────────────
def main():
    with st.sidebar:
        st.title("⚙️ 설정")
        st.markdown("---")

        env_key = get_api_key()
        if env_key:
            st.success("✅ Google API 키가 서버에 설정되어 있습니다.")
            api_key = env_key
        else:
            st.warning("Google AI Studio API 키를 입력해주세요.")
            api_key = st.text_input(
                "Google API Key",
                type="password",
                placeholder="AIza...",
                help="aistudio.google.com 에서 무료로 발급 가능합니다.",
            )

        st.markdown("---")
        st.markdown("### 📖 사용법")
        st.markdown("""
1. 새 논문 PDF 업로드
2. 이전 채점 피드백 파일 업로드
3. **분석 시작** 버튼 클릭
4. 결과 복사 후 제출
""")
        st.markdown("---")
        st.markdown("**모델**: Gemini 3.5 Flash")
        st.markdown("**지원 형식**: PDF, JPG, PNG, WEBP")

    st.title("🩺 EBM Worksheet 자동 생성기")
    st.markdown("논문과 이전 피드백을 업로드하면 AI가 자동으로 EBM 워크시트를 완성해드립니다.")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 새 논문 (필수)")
        paper_file = st.file_uploader(
            "이번 블록 RCT 논문 PDF",
            type=["pdf"],
            key="paper",
        )
        if paper_file:
            st.success(f"✅ {paper_file.name}")

    with col2:
        st.subheader("📝 이전 피드백 (권장)")
        feedback_files = st.file_uploader(
            "채점 피드백 (PDF 또는 이미지, 여러 개 가능)",
            type=["pdf", "jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="feedback",
        )
        if feedback_files:
            st.success(f"✅ {len(feedback_files)}개 파일")
            for f in feedback_files:
                st.caption(f"• {f.name}")

    st.markdown("---")

    can_run = bool(paper_file and api_key)
    if not api_key:
        st.info("💡 사이드바에서 Google API 키를 입력하세요. [무료 발급 →](https://aistudio.google.com/apikey)")
    if not paper_file:
        st.info("📄 새 논문 PDF를 업로드해주세요.")

    if st.button("🔬 분석 시작", type="primary", disabled=not can_run, use_container_width=True):
        # 새 분석 시작 시 이전 채팅 기록 초기화
        st.session_state.pop("chat_history", None)
        st.markdown("---")
        st.subheader("📋 EBM 워크시트 생성 중...")
        st.caption("아래에 실시간으로 작성됩니다. 완료될 때까지 기다려주세요.")

        result_box = st.empty()
        accumulated = []

        try:
            for chunk in stream_analysis(api_key, paper_file, feedback_files or []):
                accumulated.append(chunk)
                result_box.markdown("".join(accumulated))
            st.session_state["result"] = "".join(accumulated)
            st.session_state["api_key"] = api_key  # 채팅에서 재사용
            st.success("✅ 워크시트 생성 완료!")
        except Exception as e:
            err = str(e)
            if "API_KEY" in err.upper() or "INVALID" in err.upper():
                st.error("❌ API 키가 올바르지 않습니다.")
            elif "QUOTA" in err.upper() or "RATE" in err.upper():
                st.error("❌ API 사용 한도 초과. 잠시 후 다시 시도해주세요.")
            else:
                st.error(f"❌ 오류: {err}")

    # ── 결과 표시 ──
    if "result" in st.session_state and st.session_state.get("result"):
        st.markdown("---")
        st.subheader("📥 다운로드")

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            try:
                from docx_export import generate_docx
                docx_bytes = generate_docx(st.session_state["result"])
                st.download_button(
                    label="📄 HWP용 DOCX 다운로드",
                    data=docx_bytes,
                    file_name="EBM_worksheet.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    help="다운로드 후 HWP에서 열어 .hwp로 저장하세요",
                )
            except Exception as e:
                st.error(f"DOCX 생성 오류: {e}")

        with col_dl2:
            st.download_button(
                label="📋 텍스트 다운로드 (.txt)",
                data=st.session_state["result"].encode("utf-8"),
                file_name="EBM_worksheet.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown("---")
        tab_render, tab_raw = st.tabs(["📖 수식 렌더링 보기 (HWP 옮겨쓰기용)", "📋 원문 복사"])
        with tab_render:
            st.info("수식이 렌더링된 형태입니다. 이 화면을 보며 HWP에 옮겨 쓰세요.")
            st.markdown(st.session_state["result"])
        with tab_raw:
            st.caption("Ctrl+A 로 전체 선택 후 복사하세요.")
            st.code(st.session_state["result"], language="markdown")

        # ── Q&A 채팅 ──────────────────────────────────────────
        st.markdown("---")
        st.subheader("💬 질의응답 / 수정 요청")
        st.caption(
            "워크시트에 대해 질문하거나 수정을 요청하세요. "
            "수정 시에는 변경된 부분만 표시됩니다."
        )

        # 채팅 이력 초기화
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # API 키 확인 (채팅용)
        chat_api_key = st.session_state.get("api_key", "") or api_key
        if not chat_api_key:
            st.warning("사이드바에서 API 키를 입력해야 채팅 기능을 사용할 수 있습니다.")
        else:
            # 기존 채팅 이력 표시
            for msg in st.session_state["chat_history"]:
                role_icon = "user" if msg["role"] == "user" else "assistant"
                with st.chat_message(role_icon):
                    st.markdown(msg["content"])

            # 채팅 입력
            user_input = st.chat_input(
                "질문 또는 수정 요청 (예: 'NNT 계산이 맞는지 확인해줘', 'PICO의 P를 더 구체적으로 수정해줘')"
            )

            if user_input:
                # 사용자 메시지 표시 및 이력 추가
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state["chat_history"].append(
                    {"role": "user", "content": user_input}
                )

                # AI 응답 생성
                with st.chat_message("assistant"):
                    with st.spinner("응답 생성 중..."):
                        try:
                            response = get_chat_response(
                                chat_api_key,
                                st.session_state["result"],
                                st.session_state["chat_history"],
                            )
                        except Exception as e:
                            response = f"❌ 오류 발생: {e}"
                    st.markdown(response)

                # AI 응답 이력 추가
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": response}
                )


if __name__ == "__main__":
    main()
