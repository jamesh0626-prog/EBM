"""
AI 출력(마크다운)을 HWP 양식과 동일한 구조의 DOCX 파일로 변환
"""
import io
import re
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── 헬퍼 ─────────────────────────────────────────────────────

def _strip_latex(text: str) -> str:
    """LaTeX 수식을 읽기 쉬운 텍스트로 변환"""
    # $$...$$ 블록
    text = re.sub(r'\$\$(.+?)\$\$', lambda m: _latex_to_plain(m.group(1)), text, flags=re.DOTALL)
    # $...$ 인라인
    text = re.sub(r'\$(.+?)\$', lambda m: _latex_to_plain(m.group(1)), text)
    return text


def _latex_to_plain(expr: str) -> str:
    """간단한 LaTeX → 일반 텍스트 변환"""
    expr = expr.strip()
    expr = re.sub(r'\\frac\{(.+?)\}\{(.+?)\}', r'(\1)/(\2)', expr)
    expr = re.sub(r'\\sqrt\{(.+?)\}', r'√(\1)', expr)
    expr = re.sub(r'\\text\{(.+?)\}', r'\1', expr)
    expr = re.sub(r'\\times', '×', expr)
    expr = re.sub(r'\\pm', '±', expr)
    expr = re.sub(r'\\geq', '≥', expr)
    expr = re.sub(r'\\leq', '≤', expr)
    expr = re.sub(r'\\neq', '≠', expr)
    expr = re.sub(r'\\alpha', 'α', expr)
    expr = re.sub(r'\\beta', 'β', expr)
    expr = re.sub(r'\\_\{(.+?)\}', r'_\1', expr)
    expr = re.sub(r'\\\w+', '', expr)
    expr = re.sub(r'[{}]', '', expr)
    return expr.strip()


def _clean(text) -> str:
    """마크다운 기호 제거 후 LaTeX 변환. None-safe."""
    if not text:
        return ""
    text = str(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = _strip_latex(text)
    return text.strip()


def _set_font(run, size_pt=11, bold=False, color=None):
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = '맑은 고딕'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
    if color:
        run.font.color.rgb = RGBColor(*color)


def _add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    run = p.add_run(text)
    size = {1: 14, 2: 13, 3: 12}.get(level, 11)
    _set_font(run, size_pt=size, bold=True)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p


def _add_body(doc, text, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(0.7)
    run = p.add_run(_clean(text or ""))
    _set_font(run, size_pt=11)
    p.paragraph_format.space_after = Pt(2)
    return p


def _add_label_value(doc, label, value, indent_cm=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent_cm)
    r1 = p.add_run(str(label) + " ")
    _set_font(r1, size_pt=11, bold=True)
    r2 = p.add_run(_clean(value or ""))
    _set_font(r2, size_pt=11)
    p.paragraph_format.space_after = Pt(2)
    return p


# ── 섹션 파서 ─────────────────────────────────────────────────

def _extract_bullet_value(text: str, key_pattern: str) -> str:
    """마크다운 불릿에서 특정 키의 값 추출. None-safe."""
    if not text:
        return ""
    pattern = rf'\*\s*\*\*{key_pattern}[:\*]*\*\*\s*(.+?)(?=\n\*|\n##|\n###|$)'
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if m and m.group(1):
        return m.group(1).strip()
    pattern2 = rf'\*\s*{key_pattern}[:\s]+(.+?)(?=\n\*|\n##|\n###|$)'
    m2 = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)
    if m2 and m2.group(1):
        return m2.group(1).strip()
    return ""


def _get_section(text: str, header: str) -> str:
    """## 또는 ### 헤더 이후 다음 헤더까지 내용 추출"""
    pattern = rf'#{1,3}\s*{re.escape(header)}.*?\n(.*?)(?=\n#{1,3}\s|\Z)'
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _get_section_by_number(text: str, number: str) -> str:
    """### 1. / ### 2. 형태 섹션 추출"""
    pattern = rf'###\s*{re.escape(number)}[.\s].*?\n(.*?)(?=\n###\s|\n##\s|\Z)'
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


# ── 메인 생성 함수 ─────────────────────────────────────────────

def generate_docx(ai_text: str) -> bytes:
    doc = Document()

    # 기본 여백 설정
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(3)

    # ── 제목 ──────────────────────────────────────────────────
    title = doc.add_paragraph()
    title.alignment = 1  # center
    r = title.add_run("치료문헌비평 Worksheet")
    _set_font(r, size_pt=16, bold=True)
    doc.add_paragraph()

    # ── 피드백 분석 결과 ───────────────────────────────────────
    feedback_sec = _get_section(ai_text, "업로드된 피드백 파일 분석 결과")
    if feedback_sec:
        _add_heading(doc, "🚨 피드백 분석 결과 (AI 오답 체크리스트)", level=1)
        감점 = _extract_bullet_value(feedback_sec, "이전 파일에서 감지된 감점 요인")
        적용 = _extract_bullet_value(feedback_sec, "이번 과제 적용 방향")
        if 감점:
            _add_label_value(doc, "• 감점 요인:", 감점)
        if 적용:
            _add_label_value(doc, "• 적용 방향:", 적용)
        doc.add_paragraph()

    # ── 과제 1: PICO ──────────────────────────────────────────
    _add_heading(doc, "과제 1. 답변 가능한 임상질문 만들기 (PICO)", level=1)
    pico_sec = _get_section(ai_text, "과제 1")
    _add_label_value(doc, "P (Patient & Problem):", _extract_bullet_value(pico_sec, r"P\s*\(Patient.*?\)"), indent_cm=0.5)
    _add_label_value(doc, "I (Intervention):", _extract_bullet_value(pico_sec, r"I\s*\(Intervention\)"), indent_cm=0.5)
    _add_label_value(doc, "C (Comparison):", _extract_bullet_value(pico_sec, r"C\s*\(Comparison\)"), indent_cm=0.5)
    _add_label_value(doc, "O (Outcome):", _extract_bullet_value(pico_sec, r"O\s*\(Outcome\)"), indent_cm=0.5)
    doc.add_paragraph()

    # ── 과제 2: 검색어 ────────────────────────────────────────
    _add_heading(doc, "과제 2. 검색어 선정", level=1)
    kw_sec = _get_section(ai_text, "과제 2")
    kw = _extract_bullet_value(kw_sec, "Keywords")
    if not kw:
        kw = _extract_bullet_value(ai_text, "Keywords")
    # 키워드를 번호 리스트로 표시
    keywords = [k.strip() for k in re.split(r'[,;，]', kw) if k.strip()]
    for i, kw_item in enumerate(keywords, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        r = p.add_run(f"{i}. {_clean(kw_item)}")
        _set_font(r, size_pt=11)
        p.paragraph_format.space_after = Pt(2)
    doc.add_paragraph()

    # ── 과제 3 ────────────────────────────────────────────────
    _add_heading(doc, "과제 3. 문헌 비평과 적용", level=1)

    # 3-1: Internal Validity
    _add_heading(doc, "1. 임상시험의 결과는 타당한가? (Internal Validity)", level=2)
    iv_sec = _get_section_by_number(ai_text, "1")

    iv_questions = [
        ("치료에 대한 환자 배정은 무작위적인가?", r"치료에 대한 환자 배정"),
        ("환자에 대한 추적관찰은 충분히 완전한가?", r"추적관찰은 충분히 완전"),
        ("환자에 대한 추적관찰은 질병결과를 관찰하기에 충분히 긴가?", r"충분히 긴가"),
        ("환자는 모두 무작위 배정된 군에 따라 분석되었는가? (ITT analysis)", r"Intention to treat|ITT"),
        ("이중 맹검법이 시행되는가?", r"이중 맹검"),
        ("각 군은 시험 치료법 외에는 동일하게 취급되었는가?", r"동일하게 취급"),
        ("각 군은 임상시험 시작단계에서 유사하였는가?", r"시작단계에서 유사"),
    ]

    for q_label, q_pattern in iv_questions:
        # 전체 텍스트에서 해당 질문 답변 찾기
        m = re.search(
            rf'\*\s*\*\*{q_pattern}.*?\*\*\s*(\[예\]|\[아니오\]|예|아니오).*?-\s*근거:\s*(.+?)(?=\n\*|\n##|\n###|$)',
            ai_text, re.DOTALL | re.IGNORECASE
        )
        answer = m.group(1) if m else ""
        evidence = _clean(m.group(2) or "") if m else ""

        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        r1 = p.add_run(f"• {q_label} ")
        _set_font(r1, size_pt=11)
        r2 = p.add_run(answer)
        _set_font(r2, size_pt=11, bold=True,
                  color=(0, 112, 192) if "예" in answer else (192, 0, 0))
        p.paragraph_format.space_after = Pt(1)

        if evidence:
            p2 = doc.add_paragraph()
            p2.paragraph_format.left_indent = Cm(1.2)
            r = p2.add_run(f"근거: {evidence}")
            _set_font(r, size_pt=10)
            r.font.color.rgb = RGBColor(80, 80, 80)
            p2.paragraph_format.space_after = Pt(3)

    doc.add_paragraph()

    # 3-2: 임상적 중요성
    _add_heading(doc, "2. 해당 연구의 결과가 임상적으로 중요한가?", level=2)
    imp_sec = _get_section_by_number(ai_text, "2")

    stat_fields = [
        ("Outcome 항목", r"Outcome\s*항목"),
        ("CER (Control Event Rate)", r"CER.*?(?:Control Event Rate)?"),
        ("EER (Experimental Event Rate)", r"EER.*?(?:Experimental Event Rate)?"),
        ("RRR (Relative Risk Reduction)", r"RRR"),
        ("ARR (Absolute Risk Reduction)", r"ARR"),
        ("NNT (Number Needed to Treat)", r"NNT.*?(?:Number Needed to Treat)?"),
    ]

    for label, pattern in stat_fields:
        val = _extract_bullet_value(imp_sec or ai_text, pattern)
        if not val:
            val = _extract_bullet_value(ai_text, pattern)
        _add_label_value(doc, f"• {label}:", val, indent_cm=0.5)

    # 95% CI
    ci_m = re.search(r'95.*?CI.*?=\s*[\[\(]?(.+?)[\]\)]?\s*(?:\n|\*)', ai_text, re.DOTALL)
    ci_val = _clean(ci_m.group(1)) if ci_m else ""
    _add_label_value(doc, "• 95% CI of ARR:", ci_val, indent_cm=0.5)
    doc.add_paragraph()

    # 3-3: 부작용
    _add_heading(doc, "3. 치료에 따른 부작용은 어느 정도인가?", level=2)
    adv_sec = _get_section_by_number(ai_text, "3")

    adv_fields = [
        ("주요 부작용 항목", r"주요 부작용 항목"),
        ("CER", r"CER"),
        ("EER", r"EER"),
        ("RRI (Relative Risk Increase)", r"RRI"),
        ("ARI (Absolute Risk Increase)", r"ARI"),
        ("NNH (Number Needed to Harm)", r"NNH"),
    ]

    for label, pattern in adv_fields:
        val = _extract_bullet_value(adv_sec or ai_text, pattern)
        _add_label_value(doc, f"• {label}:", val, indent_cm=0.5)
    doc.add_paragraph()

    # 3-4: 적용 가능성
    _add_heading(doc, "4. 해당 연구의 결과를 실제 환자에게 적용할 수 있는가?", level=2)
    app_sec = _get_section_by_number(ai_text, "4")

    # 두 예/아니오 질문
    app_q1_m = re.search(r'실제환자와 연구대상.+?(\[예\]|\[아니오\]|예|아니오).+?이유:\s*(.+?)(?=\n\*|\n##|\n###|$)', ai_text, re.DOTALL)
    if app_q1_m:
        _add_label_value(doc, "• 실제환자와 연구대상 간 차이가 존재하는가?",
                         f"{app_q1_m.group(1)} — {_clean(app_q1_m.group(2))}", indent_cm=0.5)

    app_q2_m = re.search(r'다른 치료법은 없는가.+?(\[예\]|\[아니오\]|예|아니오).+?이유:\s*(.+?)(?=\n\*|\n##|\n###|$)', ai_text, re.DOTALL)
    if app_q2_m:
        _add_label_value(doc, "• 다른 치료법은 없는가?",
                         f"{app_q2_m.group(1)} — {_clean(app_q2_m.group(2))}", indent_cm=0.5)

    # f-factor, NNT_patient, NNH_patient, s-factor, LHH
    factor_patterns = [
        ("f_treatment (치료 반응 가중치)", r"f_\{?\\?text\{?treatment\}?\}?|f.*?치료 반응"),
        ("f_adverse (부작용 가중치)", r"f_\{?\\?text\{?adverse\}?\}?|f.*?부작용 가중"),
        ("NNT_patient", r"NNT.*?patient"),
        ("NNH_patient", r"NNH.*?patient"),
        ("s factor", r"s\s*factor|s\s*="),
        ("LHH", r"LHH"),
    ]
    for label, pattern in factor_patterns:
        m = re.search(rf'[•\*]\s*.*?{pattern}.*?=\s*(.+?)(?=\n[•\*]|\n##|\n###|$)', ai_text, re.DOTALL | re.IGNORECASE)
        val = _clean(m.group(1)) if m else ""
        _add_label_value(doc, f"• {label}:", val, indent_cm=0.5)

    # 결론
    conclusion_m = re.search(r'결론[:\s]*(.+?)(?=\n##|\n###|\Z)', ai_text, re.DOTALL)
    if conclusion_m:
        doc.add_paragraph()
        _add_label_value(doc, "결론:", _clean(conclusion_m.group(1)))
    doc.add_paragraph()

    # ── DISCUSSION ────────────────────────────────────────────
    _add_heading(doc, "DISCUSSION", level=1)
    disc_sec = _get_section(ai_text, "DISCUSSION")

    disc1_m = re.search(r'1[.\s]+(앞에서.*?제한점.*?|문제점.*?):\s*(.+?)(?=\n2[.\s]|\Z)', disc_sec, re.DOTALL | re.IGNORECASE)
    disc2_m = re.search(r'2[.\s]+(.+?):\s*(.+?)(?=\n3[.\s]|\Z)', disc_sec, re.DOTALL | re.IGNORECASE)

    if not disc1_m:
        # 섹션에서 직접 분리
        parts = re.split(r'\n\s*\d+[.\s]', disc_sec)
        disc_parts = [p.strip() for p in parts if p.strip()]
    else:
        disc_parts = []

    _add_heading(doc, "1. 논문의 문제점 및 제한점", level=2)
    disc1_content = (disc1_m.group(2) or "") if disc1_m else (disc_parts[0] if disc_parts else disc_sec[:500])
    _add_body(doc, disc1_content or "", indent=True)
    doc.add_paragraph()

    _add_heading(doc, "2. 추가로 필요한 근거", level=2)
    disc2_content = (disc2_m.group(2) or "") if disc2_m else (disc_parts[1] if len(disc_parts) > 1 else "")
    _add_body(doc, disc2_content or "", indent=True)

    # ── 저장 ─────────────────────────────────────────────────
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
