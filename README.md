# 易景Prompt智能体 (Prompt Agent)

基于 LangGraph 和 Reflexion 模式的专业提示词优化工程智能体。

## 🚀 项目简介

易景Prompt智能体是一个全栈 AI 应用，旨在通过多智能体协同工作流（Analyzer-Generator-Reflector），将用户的模糊想法转化为结构化、专业且符合 CO-STAR 原则的高质量提示词。

### 核心特性

-   **Reflexion 反思模式**：通过“意图分析 - 提示词生成 - 自我反思”的闭环，确保输出质量。
-   **CO-STAR 原则注入**：自动为提示词补充 Context（上下文）、Objective（目标）、Style（风格）等核心要素。
-   **SSE 全流式响应**：
    -   **过程流**：前端实时感知 Agent 的思考状态和步骤切换。
    -   **Token 流**：优化后的提示词以打字机效果实时呈现。
-   **异步高性能架构**：后端基于 FastAPI + LangGraph astream 事件驱动，不阻塞 Event Loop。
-   **企业知识库 (RAG)**：基于 FAISS + 本地向量模型实现轻量级 RAG，自动匹配行业/企业标准模板，强化特定领域的输出规范。

---

## 🛠️ 技术栈

-   **前端**: Vue 3 + Element Plus + Vite
-   **后端**: Python 3.10+ + FastAPI + LangGraph + LangChain
-   **大模型**: DeepSeek-V3 (通过 OpenAI 兼容接口调用)

---

## 📂 目录结构

```text
prompt_agent/
├── backend/                # Python 后端
│   ├── agent/              # LangGraph 核心逻辑 (State, Nodes, Graph)
│   ├── rag/                # RAG 知识库模板 (templates.json)
│   ├── tools/              # 辅助工具类 (含 pg_saver, rag_tool)
│   ├── main.py             # FastAPI 服务入口
│   ├── test_graph.py       # 命令行测试脚本
│   └── requirements.txt    # 后端依赖
└── frontend/               # Vue 前端
    ├── src/
    │   ├── useSSE.js       # SSE 通信 Hook
    │   └── App.vue         # 主界面
    └── vite.config.js      # Vite 配置 (含内网访问与代理)
```

---

## ⚡ 快速开始

### 1. 环境配置

在 `backend/` 目录下参考 `.env.example` 创建 `.env` 文件，并配置必要参数：
```env
# LLM 配置
DEEPSEEK_API_KEY=你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com

# PostgreSQL 数据库配置
POSTGRES_URL=postgresql://postgres:password@localhost:5432/prompt_agent

# (可选) LLM 角色温度配置
ANALYZER_TEMPERATURE=0.3
GENERATOR_TEMPERATURE=0.7
REFLECTOR_TEMPERATURE=0.0
```

### 2. 数据库与 RAG 初始化
- **数据库**：系统启动时会自动检查并创建 `prompt_history` (历史) 和 `user_prompts` (收藏) 表。
- **RAG 模型 (离线部署)**：
    1. **本地下载**：在有网络/VPN 的开发机上，进入 `backend/` 目录执行 `python download_model.py`。
    2. **上传模型**：下载完成后，将生成的 `backend/models/` 文件夹整体上传到服务器的 `/opt/python/prompt_agent/backend/` 目录下。
    3. **磁盘空间**：请确保服务器至少有 2GB 剩余空间。
    4. **CPU 环境优化**：若服务器无 GPU，建议手动安装 CPU 版 Torch 以节省空间（约减小 2GB）：
      ```bash
      pip install torch --index-url https://download.pytorch.org/whl/cpu
      pip install -r requirements.txt
      ```

### 2. 后端启动

```powershell
cd backend
# 安装依赖
pip install -r requirements.txt
# 启动服务
python main.py
```
*后端运行在：http://localhost:8000*

### 3. 前端启动

```powershell
cd frontend
# 安装依赖
npm install
# 启动服务
npm run dev
```
*前端运行在：http://localhost:3001 (支持局域网内网访问)*

---

## 🌐 Linux 服务器部署 (守护进程)

推荐使用 **PM2** 管理前后端进程，实现后台运行、自动重启及性能监控。

### 1. 安装 PM2
```bash
# 需要先安装 Node.js 和 npm
npm install -g pm2
```

### 2. 后端部署 (FastAPI)
在 `backend/` 目录下：
```bash
# 启动并命名为 prompt-backend
pm2 start main.py --name "prompt-backend" --interpreter ./venv/bin/python3
```

### 3. 前端部署 (Vue)
建议构建生产环境静态文件并托管：
在 `frontend/` 目录下：
```bash
# 1. 编译构建
npm run build
# 2. 使用 PM2 托管静态目录 (映射至 3001 端口)
pm2 serve dist 3001 --name "prompt-frontend" --spa
```

### 4. 常用管理操作
```bash
pm2 list                    # 查看所有服务状态
pm2 logs [name]             # 查看指定服务日志 (如: pm2 logs prompt-backend)
pm2 restart [name]          # 重启指定服务
pm2 delete [name]           # 停止并删除指定服务
pm2 save                    # 保存当前进程列表
pm2 startup                 # 配置服务器开机自动启动 PM2
```

---

## 📖 使用指南

1.  在左侧 **Rough Idea** 框中输入您的原始想法（如：“帮我写个 Vue 表格”）。
2.  点击 **开始优化**。
3.  在中间查看 Agent 的 **思考过程**（意图分析 -> 提示词优化 -> 自我反思）。
4.  在右侧查看实时生成的 **Structured Prompt**，满意后点击一键复制。

---

## 📝 迭代计划
- [ ] 增加更多模型支持（GPT-4, Claude 3.5）。
- [ ] 加入“一键试运行”功能，直接预览优化后的 Prompt 效果。
- [ ] 导出为 JSON/Markdown 格式文件。
