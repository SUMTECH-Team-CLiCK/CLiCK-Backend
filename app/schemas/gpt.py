from typing import List, Tuple
import re
from pydantic import model_validator, BaseModel, constr, Field, ConfigDict, ValidationInfo
from pydantic.types import conlist, UUID
class inputPrompt(BaseModel):
    user_id: UUID
    input_prompt: str

class Patch(BaseModel):
    tag: constr(strip_whitespace=True, min_length=1)
    # "from"는 파이썬 예약어 충돌을 피하려고 from_로 받고 alias를 "from"으로 둡니다.
    from_: constr(strip_whitespace=True, min_length=1) = Field(alias="from")
    to:    constr(strip_whitespace=True, min_length=1)

    model_config = ConfigDict(populate_by_name=True)

class outputPrompt(BaseModel):
    topic: constr(strip_whitespace=True, min_length=1, max_length=30)
    patches: conlist(Patch, min_length=1, max_length=30)
    full_suggestion: constr(strip_whitespace=True, min_length=1)

    @model_validator(mode="after")
    def corss_checks(self, info: ValidationInfo):
        original: str = (info.context or {}).get("original","")
        if not original:
            raise ValueError("원문 프롬프트가 누락되어 교차 검증을 수행할 수 없습니다.")

        search_from = 0
        # 모든 from_이 원문에 실제 존재 + 원문 내 매칭 구간 비중첩 검사
        for i, p in enumerate(self.patches):
            # 1) 모든 from_이 원문에 실제 존재
            frag= p.from_
            if frag not in original:
                raise ValueError(f'patches[{i}].from("{frag}")가 원문에 존재하지 않습니다.')

            # 2) 원문 내 매칭 구간 비중첩 검사
            # 왼→오 순서 및 비중첩 강제: 이전 매칭 끝 이후에서만 탐색
            idx = original.find(frag, search_from)
            if idx == -1:
                # 원문엔 존재하지만, 이전 점유 이후엔 더 이상 같은 구절이 없음 → 순서/비중첩 위반
                raise ValueError(
                    f'순서/비중첩 위반: "{frag}"를 이전 패치 이후 위치에서 비중첩으로 배치할 수 없습니다.'
                )

            # 다음 탐색 시작점을 현재 매칭의 끝으로 이동 (비중첩 보장)
            search_from = idx + len(frag)

        return self

class RecommendedPrompt(BaseModel):
    id: UUID
    title: str
    content: str

RecommendedPromptList = conlist(RecommendedPrompt, min_length=1, max_length=3)