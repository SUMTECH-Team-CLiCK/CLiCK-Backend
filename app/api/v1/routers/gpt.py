from app.schemas.gpt import inputPrompt
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from openai import OpenAI
from app.core.config import OPENAI_API_KEY
import re
from app.services import user_service, event_service
from app.db.session import get_db
router = APIRouter(prefix="/gpt", tags=["gpt"])

client = OpenAI(api_key=OPENAI_API_KEY)

@router.post("", summary="프롬프트 교정")
async def fix_prompt(in_: inputPrompt, db:Session = Depends(get_db)):
    if user_service.is_exist_user(in_.user_id, db) is False:
        user_service.create_user(in_.user_id, db)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """당신은 전문 프롬프트 엔지니어(Prompt Engineer)입니다.
                                사용자가 입력한 GPT용 프롬프트(질문/지시/요청 등)를 더 명확하고 효과적인 형태로 '개선된 프롬프트'로 변환하세요.
                        
                                [역할]
                                - 목적: 모델이 더 정확하고 유용한 답변을 생성하도록 프롬프트를 최적화
                                - 출력: 반드시 두 블록 모두 포함
                                  1) [개선된 프롬프트]
                                  2) [수정 이유]
                        
                                [작업 규칙]
                                1) 의도 유지: 사용자의 원래 목적을 보존
                                2) 명료화: 모호한 표현을 구체화하고 불필요한 말은 제거
                                3) 구조화: 복잡한 요청은 단계/번호/섹션/예시/출력 포맷(JSON/표/코드) 제안
                                4) 모델 지시 강화: 톤(격식/친근), 분량(짧게/자세히), 형식(코드/표/문단), 제약조건 명시
                                5) 맥락 활용: 주어진 배경/대상/사용 사례를 반영하며, 부족하면 가정 범위를 명확히 표기
                                6) 안전성: 불법/유해/개인정보 유도 요소는 제거·완화하고 대체 요청 제안
                                7) 간결성: 과장·군더더기·중복을 제거하되 정보 손실 없이 유지
                        
                                [언어]
                                - 사용자의 입력 언어를 따르되, 한국어 입력이면 한국어로 출력
                        
                                [출력 형식]  ※반드시 두 블록 모두 출력
                                [개선된 프롬프트]
                                (여기에 GPT에 보낼 최종 프롬프트만 명확히 작성)
                        
                                [수정 이유]
                                - (핵심 이유를 항목으로 간단히)
                                - (구체화/구조화/안전성 보완 등 변경 포인트)
                                """
                },
                {"role": "user", "content": in_.input_prompt}
            ],
            max_tokens=300,
            # 필요 시 파라미터: temperature=0.3, max_tokens=800 등
        )

        raw = response.choices[0].message.content or ""

        # [개선된 프롬프트] ... [수정 이유] ... 구조 파싱
        m = re.search(
            r"\[개선된\s*프롬프트]\s*(.*?)\s*\[수정\s*이유]\s*(.*)\s*\Z",
            raw,
            re.DOTALL | re.IGNORECASE
        )

        if m:
            improved = m.group(1).strip()
            reasons = m.group(2).strip()
        else:
            # 폴백: 태그가 일부 누락되었을 때 첫 블록/나머지로 추론
            # 1) [개선된 프롬프트]만 있는 경우
            m2 = re.search(r"\[개선된\s*프롬프트]\s*(.*)", raw, re.DOTALL | re.IGNORECASE)
            if m2:
                improved = m2.group(1).strip()
                reasons = "출력 형식이 지켜지지 않아 자동 보완됨: 수정 이유 블록을 찾을 수 없습니다."
            else:
                # 2) 전부 누락: 통째로 개선 프롬프트로 간주
                improved = raw.strip()
                reasons = "출력 형식이 지켜지지 않아 자동 보완됨: 태그를 찾을 수 없습니다."

        new_event = event_service.create_event(in_.user_id, in_.input_prompt, improved, reasons, db)

        return {
            "fixed_prompt": new_event.fixed_prompt,
            "reasons": new_event.reason
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))