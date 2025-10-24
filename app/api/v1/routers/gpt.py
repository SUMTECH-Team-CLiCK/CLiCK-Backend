from app.schemas.gpt import inputPrompt
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from openai import OpenAI
from app.core.config import OPENAI_API_KEY
import re
from app.services import user_service, event_service
from app.db.session import get_db
router = APIRouter(prefix="")

client = OpenAI(api_key=OPENAI_API_KEY)

@router.post("/generate-prompt", summary="템플릿에 맞는 프롬프트 생성")
async def generate_prompt(in_: inputPrompt, db:Session = Depends(get_db)):
    # if user_service.is_exist_user(in_.user_id, db) is False:
    #     user_service.create_user(in_.user_id, db)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """너는 프롬프트 구조화 전문가다.  
                                사용자가 입력한 질문 프롬프트를 분석하여 아래의 **RTF 템플릿** 형식으로 변환하라.  
                                출력은 반드시 이 구조만 포함해야 하며, 불필요한 문장·설명·코멘트·마크다운·따옴표는 절대 포함하지 않는다.  
                                (즉, 모델이 이 출력을 그대로 다음 GPT 호출 input으로 사용할 수 있어야 한다.)
                                
                                ✅ 출력 템플릿
                                Role : <역할 정의>
                                Task : <수행해야 할 작업>
                                Format : <결과물 형식>
                                
                                ### 규칙
                                1. 출력은 반드시 Role / Task / Format 세 줄만 포함한다.  
                                   - Role, Task, Format 이외의 어떠한 문장, 설명, 서두, 문단도 출력 금지.
                                2. 입력 프롬프트의 의도에 따라 가장 자연스럽고 구체적인 역할(Role)을 추론하라.  
                                   예: "코드를 짜줘" → "당신은 숙련된 소프트웨어 엔지니어입니다."
                                3. Task는 사용자의 요청을 명확하고 실행 가능한 문장으로 구체화하라.  
                                   - 명령형(“~해주세요”) 형태로 작성  
                                   - 불필요한 수사어, 애매한 표현 제거 (“좀”, “가능한 한” 등)  
                                   - 하나의 핵심 목적만 포함
                                4. Format은 결과물의 출력 형태를 명확히 지정하라.  
                                   - 예: “코드 블록과 간단한 주석 포함”, “표 형식으로 정리”, “JSON 형태로 반환” 등  
                                   - 입력에 형식 관련 언급이 없으면 기본적으로 “간결하고 명확한 서술문 형식으로 작성”으로 둔다.
                                5. 입력 언어를 유지한다. (한국어 입력이면 한국어, 영어 입력이면 영어)
                                6. 안전·정책 위반 가능성이 있을 경우 안전한 학습/분석적 표현으로 재구성한다.  
                                   (예: “해킹 방법” → “보안 침해 탐지 원리 설명”)
                                
                                ### 예시
                                
                                입력:
                                “파이썬으로 로그인 기능 코드 짜줘”
                                
                                출력:
                                Role : 당신은 숙련된 백엔드 개발자입니다.
                                Task : Python으로 사용자 로그인 기능을 구현하는 예시 코드를 작성해주세요.
                                Format : 코드 블록과 간단한 주석 설명을 포함해주세요.
                                
                                ---
                                
                                입력:
                                “AI 기술이 의료 분야에 미치는 영향을 알려줘”
                                
                                출력:
                                Role : 당신은 인공지능과 의료 산업에 정통한 기술 분석가입니다.
                                Task : AI 기술이 의료 분야에 미치는 주요 영향과 사례를 분석하여 설명해주세요.
                                Format : 항목별 요약과 함께 간결한 문단 형식으로 작성해주세요.
                                
                                ---
                                
                                입력:
                                “React에서 상태관리 방법 좀 설명해줄래?”
                                
                                출력:
                                Role : 당신은 프런트엔드 전문가입니다.
                                Task : React에서 상태 관리를 구현하는 주요 방법들을 비교하여 설명해주세요.
                                Format : 각 방법의 특징을 표 형식으로 정리하고 간단한 코드 예시를 포함해주세요.
                                
                                ---
                                
                                위 지침을 따르며, 다음 사용자 입력을 받아 정확히 **Role / Task / Format** 세 줄로만 출력하라."""
                },
                {"role": "user", "content": in_.input_prompt}
            ],
            max_tokens=500,
            # 필요 시 파라미터: temperature=0.3, max_tokens=800 등
        )

        return {
            "generated_prompt": response.choices[0].message.content
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(path="/analyze-prompt", summary="사용자가 입력한 프롬프트를 분석하여 개선안을 제안")
async def analyze_prompt(in_: inputPrompt, db:Session = Depends(get_db)):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """너는 프롬프트 에디터다. 사용자가 준 입력 프롬프트를 분석해 다음 스키마의 JSON **한 객체만** 반환하라.

                                ### 출력 스키마
                                {
                                  "tags": string[],                       // 개선한 순서대로
                                  "patches": {                            // 각 tag와 동일한 키
                                    "<tag>": { "from": string, "to": string }
                                  },
                                  "full_suggestion": string               // 전체 개선 제안
                                }
                                
                                ### 공통 규칙
                                - 출력은 오직 JSON 객체 1개. 설명/문장/코드블록/주석/마크다운 금지.
                                - 입력 언어를 유지하여 작성하라(한국어 입력→한국어 출력, 영어→영어).
                                - "tags"의 각 항목은 아래 **표준 태그 집합**에서만 선택한다. 필요한 경우에만 사용하고, 중복 금지.
                                - "tags"의 순서는 실제 개선 적용 순서와 동일해야 하며, "patches"의 키 순서도 이에 일치해야 한다.
                                - "patches[<tag>].from"에는 **원문에 실제 존재하는 연속된 구절**을 넣는다(가능한 한 최소 범위). 정확 일치 구절이 없으면 입력에서 가장 근접한 문제 구절을 발췌하여 넣는다.
                                - "patches[<tag>].to"에는 해당 구절을 대체하는 간결하고 명령형의 제안 구절을 넣는다.
                                - "full_suggestion"는 전체 프롬프트를 자연스럽게 재작성한 완전한 문장/지시문이어야 하며, 각 patch의 변경 사항을 모두 반영한다.
                                - 안전/정책 이슈가 감지되면 안전한 대안으로 재구성하고, 해당 이유를 반영하는 태그를 포함하라(예: "안전/정책 위반 가능").
                                
                                ### 표준 태그 집합(일관 표기)
                                - "모호성/지시 불명확"          // 목표·역할·행동이 흐림
                                - "범위/요구사항 과다 또는 부족"  // 과도한 범위/과소 지정
                                - "구조/길이 중복"              // 장황함·반복·군더더기
                                - "출력형식/스키마 미정"        // JSON, 표, 코드 등 형식 요구 부재
                                - "평가기준/제약 미흡"          // 길이, 수준, 정확도 등 품질 기준이 부족한 경우
                                - "데이터/맥락 누락"            // 대상·도메인·예시 부족 -> gpt가 무의미하게 일반화할 가능성이 높은 경우
                                - "형태/문체 개선"              // 문장 흐름, 어조, 자연스러움 등 표현상의 개선 필요
                                
                                ### 작성 지침
                                - 가능하면 "출력형식/스키마 미정"을 우선 해결하여, 기계가 파싱 가능한 **JSON 출력 요구**를 명시하라.
                                - 지나치게 광범위한 요구는 상위 N개 등으로 구체화하라.
                                - 필요 시 간단한 필수 필드(예: keys, 타입, 길이 제한)를 "full_suggestion"에 포함하라.
                                - 숫자·단위·시간 등은 명확히(예: "3문장", "최대 150자").
                                - 모델 자유도(temperature 등)는 언급만 하고 값은 강제하지 말라.
                                
                                ### 예시(설명용)
                                입력: "React에 대해 요약해 줘"
                                출력:
                                {
                                  "tags": ["출력형식/스키마 미정", "모호성/지시 불명확"],
                                  "patches": {
                                    "모호성/지시 불명확": { "from": "요약해 줘", "to": "핵심 포인트 3가지를 포함해 5문장이내로 요약해 줘" }
                                  },
                                  "full_suggestion": "아래 텍스트를 핵심 포인트 3가지를 포함해 3문장으로 요약해 줘. 출력은 반드시 다음 JSON 스키마를 따를 것: {\"summary\": string}"
                                }
                                
                                위 지침을 따르며, 다음 사용자 입력을 분석해 규격의 JSON **한 객체만** 반환하라.
                                """
                },
                {"role": "user", "content": in_.input_prompt}
            ],
            max_tokens=500,
            # 필요 시 파라미터: temperature=0.3, max_tokens=800 등
        )

        return response.choices[0].message.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
