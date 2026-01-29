import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from .logger import log

class RAGRetriever:
    def __init__(self):
        # 定义模型在服务器上的绝对路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(base_dir, "models", "text2vec-base-chinese")
        
        # 优先检查本地路径，如果本地没找到，才回退到在线 ID
        if os.path.exists(self.model_path):
            log(f"[RAG] 使用本地模型路径: {self.model_path}")
            self.model_name_or_path = self.model_path
        else:
            log(f"[RAG] 警告: 本地模型路径不存在 {self.model_path}，尝试使用在线 ID", level="WARNING")
            self.model_name_or_path = 'shibing624/text2vec-base-chinese'
            
        self.model = None
        self.index = None
        self.templates = []
        self.template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag", "templates.json")

    def load_resources(self):
        """延迟加载模型和构建索引"""
        if self.model:
            return

        log(f"[RAG] 正在加载嵌入模型: {self.model_name_or_path}...")
        self.model = SentenceTransformer(self.model_name_or_path)
        
        if not os.path.exists(self.template_path):
            log(f"[RAG] 警告: 模板文件不存在 {self.template_path}", level="WARNING")
            return

        with open(self.template_path, "r", encoding="utf-8") as f:
            self.templates = json.load(f)

        if not self.templates:
            log("[RAG] 警告: 模板库为空", level="WARNING")
            return

        # 提取 intent 字段进行编码
        intent_texts = [t["intent"] for f in [self.templates] for t in f]
        embeddings = self.model.encode(intent_texts)
        
        # 构建 FAISS 索引
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        log(f"[RAG] 索引构建完成，加载了 {len(self.templates)} 个模板✓")

    def retrieve(self, query, top_k=1):
        """检索最匹配的模板"""
        if not self.model:
            self.load_resources()
        
        if not self.index:
            return None

        # 编码查询
        query_vec = self.model.encode([query])
        
        # 搜索
        distances, indices = self.index.search(query_vec.astype('float32'), top_k)
        
        # 返回结果
        best_match_idx = indices[0][0]
        if best_match_idx != -1:
            return self.templates[best_match_idx]
        return None

# 全局单例
rag_retriever = RAGRetriever()
