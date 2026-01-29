import os
import asyncpg
from datetime import datetime
from dotenv import load_dotenv
from .logger import log

load_dotenv()

class PostgresSaver:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_URL")
        self.pool = None

    async def connect(self):
        if not self.pool:
            if not self.dsn:
                log("[ERROR] POSTGRES_URL 未在 .env 中配置", level="ERROR")
                return
            
            try:
                self.pool = await asyncpg.create_pool(dsn=self.dsn)
                # 初始化表结构
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS prompt_history (
                            id SERIAL PRIMARY KEY,
                            session_id VARCHAR(50) NOT NULL,
                            original_prompt TEXT NOT NULL,
                            user_intent TEXT,
                            improved_prompt TEXT,
                            critique TEXT,
                            iteration_count INTEGER DEFAULT 0,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_session_id ON prompt_history(session_id);
                                        
                        COMMENT ON TABLE prompt_history IS '提示词优化历史记录表';
                        COMMENT ON COLUMN prompt_history.session_id IS '会话唯一标识';
                        COMMENT ON COLUMN prompt_history.original_prompt IS '用户输入的原始提示词';
                        COMMENT ON COLUMN prompt_history.user_intent IS '意图分析结果';
                        COMMENT ON COLUMN prompt_history.improved_prompt IS '优化后的提示词';
                        COMMENT ON COLUMN prompt_history.critique IS '评审反馈意见';
                        COMMENT ON COLUMN prompt_history.iteration_count IS '优化迭代轮次';
                        COMMENT ON COLUMN prompt_history.created_at IS '创建时间';

                        CREATE TABLE IF NOT EXISTS user_prompts (
                            id SERIAL PRIMARY KEY,
                            session_id VARCHAR(50),
                            title VARCHAR(255) NOT NULL,
                            content TEXT NOT NULL,
                            tags VARCHAR(255),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        COMMENT ON TABLE user_prompts IS '用户收藏的提示词库';
                        COMMENT ON COLUMN user_prompts.session_id IS '产生该提示词的会话标识';
                        COMMENT ON COLUMN user_prompts.title IS '提示词标题';
                        COMMENT ON COLUMN user_prompts.content IS '提示词正文内容';
                        COMMENT ON COLUMN user_prompts.tags IS '标签(逗号分隔)';
                    """)
                log("[DB] 数据库连接池已初始化，表结构检查完成✓")
            except Exception as e:
                log(f"[ERROR] 数据库连接失败: {e}", level="ERROR")
                self.pool = None

    async def save_step(self, session_id, original_prompt, user_intent=None, improved_prompt=None, critique=None, iteration_count=0):
        if not self.pool:
            await self.connect()
        
        if not self.pool:
            return

        # 转换内容为字符串（处理 Gemini 返回的列表格式）
        def _to_string(content):
            if content is None:
                return None
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # 如果是列表，提取 text 字段
                texts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
                    else:
                        texts.append(str(item))
                return ''.join(texts)
            return str(content)
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO prompt_history 
                    (session_id, original_prompt, user_intent, improved_prompt, critique, iteration_count)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, session_id, original_prompt, _to_string(user_intent), _to_string(improved_prompt), _to_string(critique), iteration_count)
                log(f"[DB] 记录已保存 (Session: {session_id})")
        except Exception as e:
            log(f"[ERROR] 记录保存失败: {e}", level="ERROR")

    async def save_to_library(self, title, content, session_id=None, tags=""):
        if not self.pool:
            await self.connect()
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_prompts (title, content, session_id, tags)
                    VALUES ($1, $2, $3, $4)
                """, title, content, session_id, tags)
                log(f"[DB] 提示词已存入个人库: {title} (Session: {session_id})")
                return True
        except Exception as e:
            log(f"[ERROR] 存入个人库失败: {e}", level="ERROR")
            return False

    async def close(self):
        if self.pool:
            await self.pool.close()

# 全局单例
pg_saver = PostgresSaver()
