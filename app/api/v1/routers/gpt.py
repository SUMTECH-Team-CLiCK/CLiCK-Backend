import json
from typing import List
from sqlalchemy.sql import desc
from app.core.prompts.prompt_loader import IMPROVE_SYS_PROMPT, REC_SYS_PROMPT1, REC_SYS_PROMPT2
from app.models.history import History
from app.schemas.gpt import inputPrompt, RecommendedPrompt, RecommendedPromptList, outputPrompt
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from openai import OpenAI
from app.core.config import OPENAI_API_KEY
from pydantic import ValidationError
from app.services import user_service, event_service
from app.db.session import get_db
router = APIRouter(prefix="")

client = OpenAI(api_key=OPENAI_API_KEY)

@router.post(path="/analyze-prompt", summary="사용자가 입력한 프롬프트를 분석하여 개선안을 제안")
async def analyze_prompt(in_: inputPrompt, db:Session = Depends(get_db)):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": IMPROVE_SYS_PROMPT
                },
                {"role": "user", "content": in_.input_prompt}
            ],
            max_tokens=800,
            # 필요 시 파라미터: temperature=0.3, max_tokens=800 등
        )

        raw = response.choices[0].message.content
        print(raw)
        # 1) GPT 응답 파싱
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(status_code=502, detail="GPT 응답 JSON 파싱 실패")

        try:
            validated = outputPrompt.model_validate(parsed, context={"original": in_.input_prompt})
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"스키마/규칙 위반: {e.errors()}")

        # 2) 추후 DB 저장로직추가 (event, topic)

        # 3) 그대로 클라이언트에 반환(topic/patches/full_suggestion 사용)
        return validated.model_dump(by_alias=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recommended-prompts/empty/{user_id}",
    response_model=List[RecommendedPrompt],
    summary="빈 채팅방에서 유저별 관심사 기반 추천 프롬프트 3개 생성"
)
async def get_recommended_prompts_empty(
    user_id: str,
    db: Session = Depends(get_db),
):
    # 1) 최근 5개 히스토리 토픽 조회
    histories: List[History] = (
        db.query(History)
        .filter(History.user_id == user_id)
        .order_by(desc(History.created_at))
        .limit(5)
        .all()
    )
    topics = [h.topic for h in histories]

    # 히스토리가 전혀 없으면 빈 배열 반환(또는 204/404 중 정책 선택)
    if not topics:
        return []

    # 2) GPT 호출
    user_payload = {
        "topics": topics
    }

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REC_SYS_PROMPT1},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        temperature=0.4,
        max_tokens=400,
    )

    raw = resp.choices[0].message.content

    # 3) JSON 파싱 & 유효성 검사
    try:
        data = json.loads(raw)
        # title 30자 규칙을 추가로 보수적으로 보정(너무 길게 오면 자르기)
        for item in data:
            if "title" in item and isinstance(item["title"], str) and len(item["title"]) > 30:
                item["title"] = item["title"][:30]
    except Exception:
        raise HTTPException(status_code=502, detail="추천 프롬프트 응답(JSON) 파싱 실패")

    try:
        validated = RecommendedPromptList.validate(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"추천 프롬프트 응답 스키마 불일치: {e}")

    return validated

# @router.get(
#     "/recommended-prompts/empty/{user_id}",
#     response_model=List[RecommendedPrompt],
#     summary="대화내역이 있는 채팅방에서 유저 관심사 기반 추천 프롬프트 3개 생성"
# )
# async def get_recommended_prompts_not_empty(
#         user_id: str,
#         db: Session = Depends(get_db),
# )