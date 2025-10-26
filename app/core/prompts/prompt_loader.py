from importlib.resources import files

# 패키지 인지용 __init__.py 필요 (app/core/prompts/__init__.py)
from app.core import prompts as prompts_pkg


def load_prompt(name:str)->str:
    return files(prompts_pkg).joinpath(name).read_text(encoding="utf-8")

IMPROVE_SYS_PROMPT = load_prompt("improve_sys_prompt.txt")
REC_SYS_PROMPT1 = load_prompt("recommend_sys_prompt1.txt")
REC_SYS_PROMPT2 = load_prompt("recommend_sys_prompt2.txt")
