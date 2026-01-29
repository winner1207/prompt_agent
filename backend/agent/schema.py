from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    original_prompt: str    # 用户输入的原始提示词
    improved_prompt: str    # 优化后的提示词
    critique: str           # 自我批评/审查意见
    iteration_count: int    # 迭代次数 (防止死循环)
    user_intent: str        # 分析出的用户意图 (比如：是写代码，还是写文案)
    # 可以在这里增加一个状态来记录当前执行的步骤，方便前端展示
    current_step: str       
    session_id: str         # 会话标识
    is_perfect: bool        # 是否达到完美状态
    rag_match: str          # RAG 匹配到的模板类型
