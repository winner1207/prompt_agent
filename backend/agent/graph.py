from langgraph.graph import StateGraph, END
from .schema import AgentState
from .nodes import analyzer_node, generator_node, reflector_node

def should_continue(state: AgentState):
    """根据执行步数和反思结果决定是否继续"""
    # 每轮优化包含 Generator 和 Reflector 两步，3 轮优化对应 6 步（加上 Analyzer 共 7 步）
    if state.get("iteration_count", 0) >= 6:
        return END
    if state.get("is_perfect"):
        return END
    return "generator"

def create_graph():
    # 1. 初始化图
    workflow = StateGraph(AgentState)

    # 2. 添加节点
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("reflector", reflector_node)

    # 3. 设置入口
    workflow.set_entry_point("analyzer")

    # 4. 构建边
    workflow.add_edge("analyzer", "generator")
    workflow.add_edge("generator", "reflector")
    
    # 5. 条件边 (Router)
    workflow.add_conditional_edges(
        "reflector",
        should_continue,
        {
            "generator": "generator",
            END: END
        }
    )

    # 6. 编译
    return workflow.compile()

# 实例化图
app_graph = create_graph()
