from agent.graph import app_graph
import sys
import asyncio

async def run_test(prompt: str):
    # 初始化状态
    initial_state = {
        "original_prompt": prompt,
        "iteration_count": 0,
        "improved_prompt": "",
        "critique": "",
        "user_intent": "",
        "current_step": "Start"
    }

    print("="*50)
    print(f"原始提示词: {prompt}")
    print("="*50)

    # 运行图
    final_prompt = ""
    async for output in app_graph.astream(initial_state):
        for node_name, state_update in output.items():
            print(f"\n>>> 节点 [{node_name}] 执行完毕")
            # 打印关键更新
            if "user_intent" in state_update:
                print(f"分析出的意图: {state_update['user_intent'][:100]}...")
            if "improved_prompt" in state_update:
                final_prompt = state_update['improved_prompt']
                print(f"优化后的提示词预览: {final_prompt[:100]}...")
            if "critique" in state_update:
                print(f"反思建议: {state_update['critique'][:100]}...")

    print("\n" + "="*50)
    print("最终优化结果:")
    print("-" * 30)
    print(final_prompt if final_prompt else "未生成结果")
    print("="*50)

if __name__ == "__main__":
    test_prompt = "帮我写一个 vue 表格，带分页功能"
    if len(sys.argv) > 1:
        test_prompt = sys.argv[1]
    
    try:
        asyncio.run(run_test(test_prompt))
    except Exception as e:
        print(f"\n[ERROR] 运行失败: {e}")
        print("提示：请确保 d:/Python/agent/prompt_agent/backend/.env 中配置了正确的 DEEPSEEK_API_KEY")
