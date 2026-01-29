import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .schema import AgentState
from tools.pg_saver import pg_saver
from tools.rag_tool import rag_retriever
from tools.logger import log

load_dotenv()

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                texts.append(item['text'])
            else:
                texts.append(str(item))
        return ''.join(texts)
    return str(content)
def load_prompt(filename):
    path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

ANALYZER_PROMPT = load_prompt("analyzer.txt")
GENERATOR_PROMPT = load_prompt("generator.txt")
REFLECTOR_PROMPT = load_prompt("reflector.txt")

# 定义评审节点的结构化输出
class ReflectorResponse(BaseModel):
    critique: str = Field(description="对提示词的评审意见和改进建议")
    is_perfect: bool = Field(description="提示词是否已经达到行业天花板级别，无需进一步修改")

# 初始化不同角色的 LLM 实例
def _check_gemini_available():
    """检查 Gemini API 是否可用"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            log("[LLM] GOOGLE_API_KEY 未配置，使用 DeepSeek", level="WARNING")
            return False
        
        # 设置代理
        proxies = {}
        if os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY"):
            proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
            proxies = {"http": proxy_url, "https": proxy_url}
        
        # 发送简单的测试请求
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": "test"}]}]}
        
        response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=5)
        
        if response.status_code == 200:
            log("[LLM] Gemini API 可用 ✓", level="INFO")
            return True
        else:
            log(f"[LLM] Gemini API 检查失败 (状态码: {response.status_code})，使用 DeepSeek", level="WARNING")
            return False
    except Exception as e:
        log(f"[LLM] Gemini API 连接异常: {e}，使用 DeepSeek", level="WARNING")
        return False

# 全局标志：是否使用 Gemini
_use_gemini = _check_gemini_available()

def get_llm(temperature=0.7):
    """获取 LLM 实例，支持 Gemini 优先、DeepSeek 回退"""
    # 确保 Python 进程能读到代理配置
    if not os.environ.get("HTTPS_PROXY"):
        os.environ["HTTPS_PROXY"] = "http://10.100.2.21:7897"
        os.environ["HTTP_PROXY"] = "http://10.100.2.21:7897"
    
    if _use_gemini:
        return ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL", "gemini-3-flash-preview"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=float(temperature)
        )
    else:
        # 回退到 DeepSeek
        return ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=float(temperature)
        )

analyzer_llm = get_llm(os.getenv("ANALYZER_TEMPERATURE", 0.3))
generator_llm = get_llm(os.getenv("GENERATOR_TEMPERATURE", 0.7))
reflector_llm = get_llm(os.getenv("REFLECTOR_TEMPERATURE", 0.0))

async def analyzer_node(state: AgentState, config: RunnableConfig):
    """分析用户意图"""
    session_id = config.get("configurable", {}).get("thread_id", state.get("session_id", "unknown"))
    current_idx = state.get("iteration_count", 0)
    log(f"[{session_id}] [Node: Analyzer] 分析用户意图...")
    prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYZER_PROMPT),
        ("user", "{original_prompt}")
    ])
    chain = prompt | analyzer_llm
    response = await chain.ainvoke({"original_prompt": state["original_prompt"]})
    
    # 提取文本（处理 Gemini 返回的列表格式）
    text_content = extract_text(response.content)
    
    # 保存进度到数据库
    await pg_saver.save_step(
        session_id=session_id,
        original_prompt=state["original_prompt"],
        user_intent=text_content,
        iteration_count=current_idx
    )
    
    return {
        "user_intent": text_content,
        "current_step": "Analyzer",
        "iteration_count": current_idx + 1
    }

async def generator_node(state: AgentState, config: RunnableConfig):
    """生成/优化 Prompt"""
    session_id = config.get("configurable", {}).get("thread_id", state.get("session_id", "unknown"))
    current_idx = state.get("iteration_count", 0)
    # 计算当前是第几轮优化
    round_idx = (current_idx + 1) // 2
    log(f"[{session_id}] [Node: Generator] 正在进行第 {round_idx} 轮优化...")
    
    # 将 user_intent 转换为字符串（处理 Gemini 返回的列表格式）
    user_intent_str = state["user_intent"]
    if isinstance(user_intent_str, list):
        user_intent_str = extract_text(user_intent_str)
    
    # 1. 执行 RAG 检索：根据用户意图匹配模板
    matched_template = "无匹配的企业级参考模板"
    match = None
    try:
        match = rag_retriever.retrieve(user_intent_str)
        if match:
            matched_template = f"【参考行业/企业标准模板】:\n{match['template']}"
            log(f"[{session_id}] [RAG] 已匹配模板: {match['intent']}")
    except Exception as e:
        log(f"[{session_id}] [RAG] 检索失败: {e}", level="ERROR")

    # 构造上下文：如果有之前的反思意见，则加入
    critique_context = f"\n【参考反思意见进行改进】：\n{state.get('critique', '')}" if state.get('critique') else ""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERATOR_PROMPT),
        ("user", "原始意图：{user_intent}\n原始提示词：{original_prompt}\n{matched_template}")
    ])
    
    chain = prompt | generator_llm
    response = await chain.ainvoke({
        "user_intent": user_intent_str,
        "original_prompt": state["original_prompt"],
        "critique_context": critique_context,
        "matched_template": matched_template
    })
    
    # 提取文本内容
    improved_text = extract_text(response.content)
    
    # 保存进度到数据库
    await pg_saver.save_step(
        session_id=session_id,
        original_prompt=state["original_prompt"],
        user_intent=state["user_intent"],
        improved_prompt=improved_text,
        iteration_count=current_idx
    )
        
    return {
        "improved_prompt": improved_text,
        "current_step": "Generator",
        "iteration_count": current_idx + 1,
        "rag_match": match['intent'] if match else None
    }

async def reflector_node(state: AgentState, config: RunnableConfig):
    """反思/模拟"""
    session_id = config.get("configurable", {}).get("thread_id", state.get("session_id", "unknown"))
    current_idx = state.get("iteration_count", 0)
    log(f"[{session_id}] [Node: Reflector] 正在评审优化后的提示词...")
    
    # 使用 JsonOutputParser 替代 with_structured_output，以提高对不同 LLM 供应商的兼容性
    parser = JsonOutputParser(pydantic_object=ReflectorResponse)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", REFLECTOR_PROMPT + "\n\n{format_instructions}"),
        ("user", "{improved_prompt}")
    ])
    
    chain = prompt | reflector_llm | parser
    
    try:
        result_dict = await chain.ainvoke({
            "improved_prompt": state["improved_prompt"],
            "format_instructions": parser.get_format_instructions()
        })
        print(f"[DEBUG-Reflector] result_dict type: {type(result_dict)}")
        print(f"[DEBUG-Reflector] result_dict: {result_dict}")
        # 转换为 Pydantic 对象
        result = ReflectorResponse(**result_dict)
        log(f"[{session_id}] [Node: Reflector] 评审完成✓ (Perfect: {result.is_perfect})")
    except Exception as e:
        log(f"[{session_id}] [Node: Reflector] 结构化输出解析失败: {e}", level="ERROR")
        # 降级处理：如果解析失败，默认不完美
        result = ReflectorResponse(critique="评审服务暂时不可用，正在自动进入下一轮优化。", is_perfect=False)
    
    # 保存进度到数据库
    await pg_saver.save_step(
        session_id=session_id,
        original_prompt=state["original_prompt"],
        user_intent=state["user_intent"],
        improved_prompt=state["improved_prompt"],
        critique=result.critique,
        iteration_count=current_idx
    )
    
    return {
        "critique": result.critique,
        "is_perfect": result.is_perfect,
        "current_step": "Reflector",
        "iteration_count": current_idx + 1
    }
