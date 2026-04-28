"""
RAG Search 工具 - 知识库检索

使用混合检索 (BM25 + Vector) + Reranker
- Embedding: BAAI/bge-base-zh-v1.5 (本地模型)
- Reranker: BAAI/bge-reranker-base (本地模型)
- BM25: 关键词检索
"""

import os
from pathlib import Path
from typing import Optional, List, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import BACKEND_DIR, get_config


MODELS_DIR = BACKEND_DIR / "models"

EMBEDDING_MODEL_PATH = str(MODELS_DIR / "bge-base-zh-v1.5")
RERANKER_MODEL_PATH = str(MODELS_DIR / "bge-reranker-base")

# 缓存
_index_cache: Optional[Any] = None
_index_loaded: bool = False
_embedding_model_cache: Optional[Any] = None
_reranker_model_cache: Optional[Any] = None
_nodes_cache: Optional[List[Any]] = None


class RAGSearchInput(BaseModel):
    """RAG Search 工具输入参数"""
    query: str = Field(
        ...,
        description="搜索查询内容",
        examples=["如何使用飞书", "API 配置方法"]
    )


def get_embedding_model():
    """获取 Embedding 模型"""
    global _embedding_model_cache
    
    if _embedding_model_cache is not None:
        return _embedding_model_cache
    
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
        from llama_index.core.embeddings import BaseEmbedding
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_PATH)
        model = AutoModel.from_pretrained(EMBEDDING_MODEL_PATH)
        model.to(device)
        model.eval()
        
        class BERTEmbedding(BaseEmbedding):
            def __init__(self, model, tokenizer, device):
                super().__init__()
                self._model = model
                self._tokenizer = tokenizer
                self._device = device
            
            def _encode(self, texts: List[str]) -> List[List[float]]:
                """编码文本为向量"""
                with torch.no_grad():
                    if isinstance(texts, str):
                        texts = [texts]
                    
                    encoded = self._tokenizer(
                        texts,
                        padding=True,
                        truncation=True,
                        max_length=512,
                        return_tensors="pt"
                    ).to(self._device)
                    
                    outputs = self._model(**encoded)
                    embeddings = outputs.last_hidden_state[:, 0, :]
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                    
                    return embeddings.cpu().numpy().tolist()
            
            def _get_query_embedding(self, query: str):
                return self._encode([query])[0]
            
            def _get_text_embedding(self, text: str):
                return self._encode([text])[0]
            
            def _get_text_embeddings(self, texts: List[str]):
                return self._encode(texts)
            
            async def _aget_query_embedding(self, query: str):
                return self._get_query_embedding(query)
            
            async def _aget_text_embedding(self, text: str):
                return self._get_text_embedding(text)
        
        _embedding_model_cache = BERTEmbedding(model, tokenizer, device)
        
        print(f"✓ Embedding 模型已加载: {EMBEDDING_MODEL_PATH} (设备: {device})")
        return _embedding_model_cache
        
    except Exception as e:
        print(f"加载 Embedding 模型失败: {str(e)}")
        raise


def get_reranker():
    """获取 Reranker 模型"""
    global _reranker_model_cache
    
    if _reranker_model_cache is not None:
        return _reranker_model_cache
    
    try:
        from sentence_transformers import CrossEncoder
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        _reranker_model_cache = CrossEncoder(
            RERANKER_MODEL_PATH,
            max_length=512,
            device=device,
        )
        
        print(f"✓ Reranker 模型已加载: {RERANKER_MODEL_PATH} (设备: {device})")
        return _reranker_model_cache
        
    except Exception as e:
        print(f"加载 Reranker 模型失败: {str(e)}")
        return None


def rerank_results(query: str, results: List[dict], top_k: int = 5) -> List[dict]:
    """使用 Reranker 重排序结果"""
    if not results:
        return results
    
    reranker = get_reranker()
    if reranker is None:
        return results[:top_k]
    
    try:
        pairs = [[query, r["text"]] for r in results]
        scores = reranker.predict(pairs)
        
        scored_results = list(zip(results, scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        reranked = []
        for result, score in scored_results[:top_k]:
            reranked.append({
                **result,
                "rerank_score": float(score),
            })
        
        return reranked
        
    except Exception as e:
        print(f"Rerank 失败: {str(e)}")
        return results[:top_k]


def get_knowledge_dir() -> Path:
    """获取知识库目录"""
    config = get_config().config
    knowledge_dir = config.rag.knowledge_dir
    
    if Path(knowledge_dir).is_absolute():
        return Path(knowledge_dir)
    
    return BACKEND_DIR / knowledge_dir


def get_storage_dir() -> Path:
    """获取存储目录"""
    config = get_config().config
    storage_dir = config.rag.storage_dir
    
    if Path(storage_dir).is_absolute():
        return Path(storage_dir)
    
    return BACKEND_DIR / storage_dir


def _create_hybrid_retriever(index, nodes, top_k: int = 15):
    """创建混合检索器 (BM25 + Vector)"""
    try:
        from llama_index.retrievers.bm25 import BM25Retriever
        from llama_index.core.retrievers import QueryFusionRetriever
        
        # 向量检索器
        vector_retriever = index.as_retriever(similarity_top_k=top_k)
        
        # BM25 检索器
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=nodes,
            similarity_top_k=top_k,
        )
        
        # 混合检索器（使用 RRF 融合）
        hybrid_retriever = QueryFusionRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            similarity_top_k=top_k,
            num_queries=1,  # 不生成额外查询
            mode="reciprocal_rerank",  # RRF 融合算法
        )
        
        return hybrid_retriever
        
    except ImportError:
        # 如果 BM25 不可用，回退到纯向量检索
        print("⚠ BM25 不可用，使用纯向量检索")
        return index.as_retriever(similarity_top_k=top_k)
    except Exception as e:
        print(f"创建混合检索器失败: {e}，回退到纯向量检索")
        return index.as_retriever(similarity_top_k=top_k)


def build_or_load_index():
    """构建或加载索引（支持混合检索）"""
    global _index_cache, _index_loaded, _nodes_cache
    
    if _index_loaded and _index_cache is not None:
        return _index_cache
    
    try:
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        from llama_index.core.storage.docstore import SimpleDocumentStore
        from llama_index.core.storage.index_store import SimpleIndexStore
        from llama_index.core.vector_stores import SimpleVectorStore
        
        knowledge_dir = get_knowledge_dir()
        storage_dir = get_storage_dir()
        
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        if not knowledge_dir.exists() or not list(knowledge_dir.glob("*")):
            _index_loaded = True
            _index_cache = None
            _nodes_cache = None
            return None
        
        persist_file = storage_dir / "index.json"
        
        # 尝试加载已存在的索引
        if persist_file.exists():
            try:
                storage_context = StorageContext.from_defaults(
                    docstore=SimpleDocumentStore.from_persist_dir(persist_dir=str(storage_dir)),
                    index_store=SimpleIndexStore.from_persist_dir(persist_dir=str(storage_dir)),
                    vector_store=SimpleVectorStore.from_persist_dir(persist_dir=str(storage_dir)),
                )
                
                _index_cache = VectorStoreIndex.from_storage_context(storage_context)
                
                # 从 docstore 获取节点
                _nodes_cache = list(storage_context.docstore.docs.values())
                
                _index_loaded = True
                return _index_cache
            except Exception as e:
                print(f"加载索引失败: {e}，将重新构建")
        
        # 构建新索引
        documents = SimpleDirectoryReader(
            str(knowledge_dir),
            recursive=True,
            required_exts=[
                ".md", ".txt", ".pdf",  # 文档
                ".csv", ".xlsx", ".xls", ".xlsb",  # 数据
                ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",  # 代码
                ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg",  # 配置
                ".html", ".htm", ".css", ".scss", ".sql", ".sh", ".bash", ".mdx",  # 标记语言
            ]
        ).load_data()
        
        if not documents:
            _index_loaded = True
            _index_cache = None
            _nodes_cache = None
            return None
        
        embed_model = get_embedding_model()
        
        # 创建存储上下文（BM25 需要 docstore）
        storage_context = StorageContext.from_defaults(
            docstore=SimpleDocumentStore(),
            index_store=SimpleIndexStore(),
            vector_store=SimpleVectorStore(),
        )
        
        _index_cache = VectorStoreIndex.from_documents(
            documents,
            embed_model=embed_model,
            storage_context=storage_context,
        )
        
        # 缓存节点（用于 BM25）
        _nodes_cache = list(storage_context.docstore.docs.values())
        
        # 持久化存储
        _index_cache.storage_context.persist(persist_dir=str(storage_dir))
        
        _index_loaded = True
        print(f"✓ 知识库索引已构建，共 {len(documents)} 个文档")
        return _index_cache
        
    except Exception as e:
        print(f"构建/加载索引时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        _index_loaded = True
        _index_cache = None
        _nodes_cache = None
        return None


@tool("search_knowledge_base", args_schema=RAGSearchInput)
def search_knowledge_base_tool(query: str) -> str:
    """在知识库中搜索相关内容
    
    使用三阶段检索：
    1. 混合检索 (BM25 + Vector)
    2. RRF 融合
    3. Reranker 重排序
    """
    config = get_config().config
    
    if not config.rag.enabled:
        return "提示：RAG 功能已被禁用。可在设置中启用。"
    
    index = build_or_load_index()
    
    if index is None:
        knowledge_dir = get_knowledge_dir()
        return f"提示：知识库为空或未初始化。请将文档放入 {knowledge_dir} 目录后重试。"
    
    try:
        # 创建混合检索器
        retriever = _create_hybrid_retriever(
            index,
            _nodes_cache,
            top_k=15  # 召回更多候选
        )
        
        # 检索
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.node.text,
                "score": node.score if node.score else 0.0,
                "source": node.node.metadata.get('file_name', '未知'),
            })
        
        # Rerank 重排序
        results = rerank_results(query, results, top_k=5)
        
        output = f"查询: {query}\n"
        output += f"{'─' * 40}\n\n"
        
        if results:
            output += "相关结果:\n\n"
            for i, result in enumerate(results, 1):
                score_info = f"相似度: {result['score']:.2f}"
                if "rerank_score" in result:
                    score_info += f" | 重排序: {result['rerank_score']:.3f}"
                
                output += f"### 结果 {i} ({score_info})\n"
                output += f"来源: {result['source']}\n"
                output += f"{result['text'][:500]}...\n\n"
        
        return output
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"错误：搜索知识库时发生异常 - {str(e)}"


def rebuild_index() -> str:
    """重建知识库索引"""
    global _index_cache, _index_loaded, _nodes_cache
    
    _index_cache = None
    _index_loaded = False
    _nodes_cache = None
    
    index = build_or_load_index()
    
    if index is not None:
        return "知识库索引重建成功"
    else:
        return "知识库索引重建失败：知识库为空或构建错误"


def retrieve_knowledge(query: str, top_k: int = 3) -> list[dict]:
    """从知识库中检索相关内容（返回结构化结果）
    
    使用三阶段检索：
    1. 混合检索 (BM25 + Vector)
    2. RRF 融合
    3. Reranker 重排序
    """
    config = get_config().config
    
    if not config.rag.enabled:
        return []
    
    index = build_or_load_index()
    
    if index is None:
        return []
    
    try:
        # 创建混合检索器
        retriever = _create_hybrid_retriever(
            index,
            _nodes_cache,
            top_k=top_k * 3
        )
        
        # 检索
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.node.text,
                "score": node.score if node.score else 0.0,
                "source": node.node.metadata.get('file_name', '未知'),
            })
        
        # Rerank 重排序
        results = rerank_results(query, results, top_k=top_k)
        
        return results
        
    except Exception as e:
        print(f"知识库检索失败: {str(e)}")
        return []


def get_knowledge_context(query: str, top_k: int = 3) -> str:
    """获取知识库上下文文本"""
    results = retrieve_knowledge(query, top_k)
    
    if not results:
        return ""
    
    context_parts = ["[知识库检索结果]"]
    
    for i, result in enumerate(results, 1):
        score_info = f"相关度: {result['score']:.2f}"
        if "rerank_score" in result:
            score_info += f" | 重排序: {result['rerank_score']:.3f}"
        
        context_parts.append(f"\n### 相关文档 {i} ({score_info})")
        context_parts.append(f"来源: {result['source']}")
        context_parts.append(result['text'])
    
    context_parts.append("\n[/知识库检索结果]")
    
    return "\n".join(context_parts)


RAG_SEARCH_TOOL = search_knowledge_base_tool
