import json
import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from agent.graph import app_graph
from agent.nodes import parse_llm_response
from tools.pg_saver import pg_saver
from tools.logger import log

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    await pg_saver.connect()
    yield
    # 关闭时断开连接
    await pg_saver.close()

app = FastAPI(title="Prompt Agent API", lifespan=lifespan)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/optimize")
async def optimize_prompt(request: Request):
    data = await request.json()
    original_prompt = data.get("prompt", "")
    session_id = uuid.uuid4().hex[:8]

    async def event_generator():
        initial_state = {
            "original_prompt": original_prompt,
            "iteration_count": 0,
            "improved_prompt": "",
            "critique": "",
            "user_intent": "",
            "current_step": "Start",
            "session_id": session_id,
            "is_perfect": False
        }

        try:
            # 首先发送初始化信息，透传 session_id
            yield f"data: {json.dumps({'status': 'init', 'session_id': session_id})}\n\n"
            
            config = {"configurable": {"thread_id": session_id}}
            # 使用 astream_events(v2) 捕捉更细粒度的事件
            async for event in app_graph.astream_events(initial_state, config=config, version="v2"):
                kind = event["event"]
                
                # 1. 捕捉节点开始执行的瞬间
                if kind == "on_chain_start" and event.get("name") in ["analyzer", "generator", "reflector"]:
                    node_name = event["name"]
                    yield f"data: {json.dumps({'node': node_name, 'status': 'start'})}\n\n"

                # 2. 捕捉 LLM 吐字的瞬间 (实现流式吐字)
                elif kind == "on_chat_model_stream":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    # 我们只在优化阶段（generator）展示流式吐字，或者全部展示
                    if node_name == "generator":
                        content = event["data"]["chunk"].content
                        # 物理隔离：调用统一解析器
                        token = parse_llm_response(content)
                        if token:
                            yield f"data: {json.dumps({'node': node_name, 'status': 'token', 'token': token})}\n\n"

                # 3. 捕捉节点结束并带回状态更新的瞬间
                elif kind == "on_chain_end" and event.get("name") in ["analyzer", "generator", "reflector"]:
                    node_name = event["name"]
                    # 从输出中提取状态更新
                    output = event.get("data", {}).get("output", {})
                    yield f"data: {json.dumps({'node': node_name, 'status': 'end', 'updates': output})}\n\n"
                
            log(f"[{session_id}] 提示词优化任务执行完成✓")
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
    
@app.post("/api/save_prompt")
async def save_prompt(request: Request):
    data = await request.json()
    title = data.get("title", "未命名提示词")
    content = data.get("content", "")
    session_id = data.get("session_id", "")
    tags = data.get("tags", "AI优化")
    
    if not content:
        return {"success": False, "message": "内容不能为空"}
        
    success = await pg_saver.save_to_library(title, content, session_id, tags)
    return {"success": success, "message": "保存成功" if success else "保存失败"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
