

from __future__ import annotations

import json
import re
from typing import List, Optional, Literal, Dict, Any
from app.core.config import settings
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

router = APIRouter(prefix="")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

TaskType = Literal[
    "qa_fact",
    "coding",
    "debugging",
    "data_analysis",
    "summarization",
    "translation_localization",
    "brainstorming",
    "planning",
    "creative_writing",
    "other",
]

class InputPrompt(BaseModel):
    prompt: str = Field(..., description="사용자가 LLM에 보낼 원본 질문/요청")
    language: Literal["ko", "en"] = Field("ko", description="개선 프롬프트와 보조출력을 생성할 언어")
    domain: Optional[str] = Field(None, description="도메인(예: ecommerce, fintech, education 등)")
    user_context: Optional[str] = Field(None, description="사용자/조직/프로젝트 맥락, 요약문")
    style_guide: Optional[str] = Field(None, description="톤/브랜드 보이스/용어집 등")
    desired_output_format: Optional[str] = Field(
        None, description="최종 LLM 답변 형식 요구(예: Markdown 표, JSON 스키마 등)"
    )
    enable_rag: bool = Field(False, description="내부 RAG(조직 지식) 사용 의향만 신호로 전달")
    enable_web: bool = Field(False, description="웹검색/최신성 보강 필요 신호")
    mask_pii: bool = Field(False, description="원문 내 PII(이메일/전화) 마스킹 후 모델에 전송")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=2.0, description="모델 디코딩 온도")
    max_tokens: Optional[int] = Field(900, description="모델 최대 토큰 출력 값")
    # 고급 옵션(필요시 확장):
    additional_constraints: Optional[str] = Field(None, description="특별한 제약 또는 금지사항")
    examples: Optional[str] = Field(None, description="좋은/나쁜 예시가 있다면 텍스트로 제공")
    # RAG/외부 지식 스니펫(이미 확보되어 있다면 전달)
    knowledge_snippets: Optional[List[str]] = Field(
        default=None, description="도메인 지식 스니펫 텍스트 배열(200~400토큰 권장)"
    )

class ImprovedPromptPayload(BaseModel):
    improved_prompt: str
    task_type: TaskType
    missing_info_questions: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None
    rubric_for_answer: Optional[List[str]] = None
    safety_flags: Optional[List[str]] = None
    notes: Optional[str] = None

class AnalyzePromptResponse(BaseModel):
    result: ImprovedPromptPayload
    model: str
    usage: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None  # 디버깅용(필요시 프런트에서 숨김)


# -----------------------------
# Utilities
# -----------------------------
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4})")

def mask_pii_text(text: str) -> str:
    # Simple masking for emails and phone numbers
    masked = EMAIL_RE.sub(lambda m: f"{m.group(1)[0]}***@***.{m.group(2).split('.')[-1]}", text)
    masked = PHONE_RE.sub(lambda _: "XXX-XXXX-XXXX", masked)
    return masked

def coerce_json_from_text(text: str) -> dict:
    """
    Try to coerce a JSON object from model text output.
    1) direct json.loads
    2) trim to outermost {...} block
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    # try to locate the first '{' and last '}'
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            return json.loads(snippet)
    except Exception:
        pass
    raise ValueError("Failed to parse JSON from model output.")

# -----------------------------
# Templates/Guides injected to System Prompt
# -----------------------------
TASK_TYPES_DESC = """
[Task Types]
- qa_fact: 사실 질의응답(날짜/단위/출처/최신성 중요)
- coding: 코드 생성
- debugging: 오류 진단/수정
- data_analysis: 데이터 가설검정/시각화/리포팅
- summarization: 요약/보고서
- translation_localization: 번역/현지화
- brainstorming: 아이데이션/브레인스토밍
- planning: 계획/체크리스트/우선순위
- creative_writing: 창작(에세이/스토리/슬로건)
- other: 상기 이외
"""

SLOT_TEMPLATES = """
[Slot Templates (condensed)]
- qa_fact:
  * 목적/범위/시점/정의/단위
  * 최신성 요구치(날짜), 허용불확실성
  * 출력형식(표/불릿/JSON), 출처 2개 이상
- coding/debugging:
  * 언어/버전/환경/의존성, 입출력 명세
  * 성능/보안 제약, 테스트케이스 3개
  * 코딩규칙(스타일/린트), 오류/가정 명시
- data_analysis:
  * 데이터 스키마/예시/지표/가설
  * 전처리 규칙, 시각화 요구, 해석 5줄
- summarization:
  * 독자/목표/톤/길이/포맷, TL;DR
  * 반대의견/리스크 3개
- translation_localization:
  * 독자/레지스터, 용어집/금칙어
  * 형식/문자수 제한, 브랜드 보이스
- brainstorming/planning/creative_writing:
  * 제약(예산/기간/채널), 타깃/벤치마크
  * 다양성 보장 규칙, 평가 기준
"""

SAFETY_CHECKLIST = """
[Safety & Constraints Checklist]
- 민감정보(PII) 포함 여부 및 마스킹 필요
- 저작권 텍스트 직접 재생성 금지/요약 대체
- 의료/법률/고위험 안내 시 범위 제한 및 경고
- 모델 한계/토큰 길이/금칙어 점검
"""

RUBRIC_HINTS = """
[Auto Rubric Hints]
- 정확성(사실/날짜/정의 명시) 0~2
- 구체성(측정가능 지표/형식) 0~2
- 재현성(예시/테스트/단계) 0~2
- 간결성(불필요 반복/장황함 최소) 0~2
- 출처성(근거/링크/문헌) 0~2
"""

JSON_SCHEMA_DESC = """
[Required JSON Schema]
{
  "improved_prompt": string,
  "task_type": "qa_fact" | "coding" | "debugging" | "data_analysis" | "summarization" | "translation_localization" | "brainstorming" | "planning" | "creative_writing" | "other",
  "missing_info_questions": [string, ...] (<=3, optional),
  "assumptions": [string, ...] (optional),
  "rubric_for_answer": [string, ...] (optional),
  "safety_flags": [string, ...] (optional),
  "notes": string (optional)
}
Return ONLY a single JSON object. No markdown, no prose, no code fences.
"""

_SYS_PROMPT = f"""
You are a "Prompt Improver" that rewrites user prompts into clearer, testable, reusable forms.
Follow this pipeline strictly:
1) Identify the task type from the list.
2) Select a corresponding slot template. Fill known slots from user/context snippets; if unknown, infer with lightweight assumptions and list them in `assumptions`.
3) Rewrite the user's prompt into a concise, specific, constraint-aware improved prompt. Include measurable success criteria and explicit output format if feasible.
4) Add up to three short clarification questions in `missing_info_questions` ONLY if essential blockers remain.
5) Run the Safety & Constraints Checklist and add brief `safety_flags` when relevant (PII, copyright, medical/legal, policy).
6) Provide a compact rubric (3~6 items) in `rubric_for_answer` to help the answering model self-check.
7) Output MUST be valid JSON per the schema below. DO NOT reveal chain-of-thought or internal reasoning; keep `notes` to 3 lines max if used.

Language: Mirror the user's requested language (ko/en). If not specified, use ko.

{TASK_TYPES_DESC}
{SLOT_TEMPLATES}
{SAFETY_CHECKLIST}
{RUBRIC_HINTS}
{JSON_SCHEMA_DESC}
"""

# -----------------------------
# Endpoint
# -----------------------------
@router.post(
    path="/analyze-prompt22",
    summary="사용자가 입력한 프롬프트를 분석하여 개선안을 제안",
    response_model=AnalyzePromptResponse,
)
async def analyze_prompt(in_: InputPrompt):
    # 1) Prepare user content (context bundle)
    user_prompt_text = in_.prompt.strip()
    if not user_prompt_text:
        raise HTTPException(status_code=400, detail="prompt가 비어 있습니다.")

    # Optional simple PII masking for transport (you can disable via in_.mask_pii=False)
    transport_text = mask_pii_text(user_prompt_text) if in_.mask_pii else user_prompt_text

    # Build a compact "context card" for the model (kept short to save tokens)
    context_items = []
    if in_.domain:
        context_items.append(f"domain: {in_.domain}")
    if in_.desired_output_format:
        context_items.append(f"desired_output_format: {in_.desired_output_format}")
    if in_.style_guide:
        context_items.append(f"style_guide: {in_.style_guide}")
    if in_.additional_constraints:
        context_items.append(f"additional_constraints: {in_.additional_constraints}")
    if in_.user_context:
        context_items.append(f"user_context: {in_.user_context}")
    if in_.enable_rag:
        context_items.append("rag: true (if beneficial)")
    if in_.enable_web:
        context_items.append("web_search: true (if recency/ambiguity)")
    if in_.examples:
        # Keep examples short to avoid exceeding token limits
        context_items.append(f"examples: {in_.examples[:1200]}")

    if in_.knowledge_snippets:
        # include only first few snippets to keep brief
        limited_snips = in_.knowledge_snippets[:3]
        snip_join = "\n---\n".join(s[:1200] for s in limited_snips)
        context_items.append(f"knowledge_snippets:\n{snip_join}")

    context_block = "\n".join(context_items) if context_items else "none"

    # 2) Compose messages for Chat Completions (JSON mode)
    messages = [
        {"role": "system", "content": _SYS_PROMPT},
        {
            "role": "user",
            "content": (
                f"[language]: {in_.language}\n"
                f"[context]:\n{context_block}\n"
                f"[original_prompt]:\n{transport_text}"
            ),
        },
    ]

    # 3) Call OpenAI (force JSON object output)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=in_.temperature or 0.3,
            max_tokens=in_.max_tokens or 900,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")

    # 4) Parse response to JSON + validate
    raw_text = completion.choices[0].message.content if completion.choices else ""
    if not raw_text:
        raise HTTPException(status_code=502, detail="모델 응답이 비어 있습니다.")

    try:
        parsed = coerce_json_from_text(raw_text)
    except Exception:
        # Retry once without response_format (fallback) to repair JSON
        try:
            repair_try = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages + [
                    {
                        "role": "system",
                        "content": "The previous output was not valid JSON. Return ONLY a valid JSON object per the schema.",
                    }
                ],
                temperature=in_.temperature or 0.2,
                max_tokens=in_.max_tokens or 900,
            )
            raw_text = repair_try.choices[0].message.content if repair_try.choices else ""
            parsed = coerce_json_from_text(raw_text)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"모델 JSON 파싱 실패: {e}")

    # Validate with Pydantic
    try:
        payload = ImprovedPromptPayload(**parsed)
    except ValidationError as ve:
        # Attach partial raw for debugging
        raise HTTPException(status_code=422, detail=f"스키마 검증 실패: {ve}")

    # 5) Build response
    usage = getattr(completion, "usage", None)
    usage_dict = None
    if usage is not None:
        try:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }
        except Exception:
            usage_dict = None

    return JSONResponse(
        status_code=200,
        content=AnalyzePromptResponse(
            result=payload,
            model=getattr(completion, "model", "gpt-4o-mini"),
            usage=usage_dict,
            raw_text=raw_text,
        ).model_dump()
    )



