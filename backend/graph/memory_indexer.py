"""
MEMORY.md 专用向量索引器

使用混合检索 (BM25 + Vector) + Reranker
- Embedding: BAAI/bge-base-zh-v1.5 (本地模型)
- Reranker: BAAI/bge-reranker-base (本地模型)
- BM25: 关键词检索
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict

from backend.config import BACKEND_DIR


MEMORY_FILE = BACKEND_DIR / "memory" / "MEMORY.md"
MEMORY_INDEX_DIR = BACKEND_DIR / "storage" / "memory_index"
MODELS_DIR = BACKEND_DIR / "models"

EMBEDDING_MODEL_PATH = str(MODELS_DIR / "bge-base-zh-v1.5")
RERANKER_MODEL_PATH = str(MODELS_DIR / "bge-reranker-base")

# 缓存
_memory_index_cache: Optional[Any] = None
_memory_file_md5: Optional[str] = None
_embedding_model_cache: Optional[Any] = None
_reranker_model_cache: Optional[Any] = None
_nodes_cache: Optional[List[Any]] = None


def _get_file_md5(file_path: Path) -> Optional[str]:
    """计算文件 MD5"""
    if not file_path.exists():
        return None
    try:
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()
    except Exception:
        return None


def _get_embedding_model():
    """获取 Embedding 模型（使用 transformers 直接加载 BERT）"""
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


def _get_reranker():
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


def _rerank_results(query: str, results: List[dict], top_k: int = 3) -> List[dict]:
    """使用 Reranker 重排序结果"""
    if not results:
        return results
    
    reranker = _get_reranker()
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


def rebuild_index() -> bool:
    """重建 MEMORY.md 的向量索引（支持混合检索）"""
    global _memory_index_cache, _memory_file_md5, _nodes_cache
    
    if not MEMORY_FILE.exists():
        _memory_index_cache = None
        _memory_file_md5 = None
        _nodes_cache = None
        return False
    
    try:
        from llama_index.core import VectorStoreIndex, Document, StorageContext
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.storage.docstore import SimpleDocumentStore
        from llama_index.core.storage.index_store import SimpleIndexStore
        from llama_index.core.vector_stores import SimpleVectorStore
        
        embed_model = _get_embedding_model()
        
        MEMORY_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # 创建存储上下文（BM25 需要 docstore）
        storage_context = StorageContext.from_defaults(
            docstore=SimpleDocumentStore(),
            index_store=SimpleIndexStore(),
            vector_store=SimpleVectorStore(),
        )
        
        content = MEMORY_FILE.read_text(encoding="utf-8")
        if not content.strip():
            _memory_index_cache = None
            _memory_file_md5 = None
            _nodes_cache = None
            return False
        
        document = Document(
            text=content,
            metadata={
                "file_name": "MEMORY.md",
                "file_path": str(MEMORY_FILE),
            }
        )
        
        splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=32,
        )
        
        nodes = splitter.get_nodes_from_documents([document])
        
        if not nodes:
            _memory_index_cache = None
            _memory_file_md5 = None
            _nodes_cache = None
            return False
        
        # 添加节点到 docstore（BM25 需要）
        storage_context.docstore.add_documents(nodes)
        
        # 创建索引
        _memory_index_cache = VectorStoreIndex(
            nodes,
            embed_model=embed_model,
            storage_context=storage_context,
        )
        
        # 缓存节点（用于 BM25）
        _nodes_cache = nodes
        
        # 持久化存储
        _memory_index_cache.storage_context.persist(persist_dir=str(MEMORY_INDEX_DIR))
        
        _memory_file_md5 = _get_file_md5(MEMORY_FILE)
        
        print(f"✓ MEMORY.md 索引已重建，共 {len(nodes)} 个切片")
        return True
        
    except Exception as e:
        print(f"重建 MEMORY.md 索引时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        _memory_index_cache = None
        _memory_file_md5 = None
        _nodes_cache = None
        return False


def _maybe_rebuild() -> bool:
    """检查是否需要重建索引"""
    global _memory_index_cache, _memory_file_md5
    
    current_md5 = _get_file_md5(MEMORY_FILE)
    
    if current_md5 is None:
        _memory_index_cache = None
        return False
    
    if current_md5 != _memory_file_md5:
        print("检测到 MEMORY.md 变更，自动重建索引...")
        return rebuild_index()
    
    return _memory_index_cache is not None


def _create_hybrid_retriever(index, nodes, top_k: int = 10):
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


def retrieve(query: str, top_k: int = 3) -> List[dict]:
    """从 MEMORY.md 中检索相关内容
    
    使用三阶段检索：
    1. 混合检索 (BM25 + Vector)
    2. RRF 融合
    3. Reranker 重排序
    """
    global _memory_index_cache, _nodes_cache
    
    if not _maybe_rebuild():
        return []
    
    if _memory_index_cache is None:
        return []
    
    try:
        # 创建混合检索器
        retriever = _create_hybrid_retriever(
            _memory_index_cache,
            _nodes_cache,
            top_k=top_k * 3  # 召回更多候选
        )
        
        # 检索
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.node.text,
                "score": node.score if node.score else 0.0,
                "source": node.node.metadata.get("file_name", "MEMORY.md"),
            })
        
        # Rerank 重排序
        results = _rerank_results(query, results, top_k=top_k)
        
        return results
        
    except Exception as e:
        print(f"检索 MEMORY.md 时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def get_rag_context(query: str, top_k: int = 3) -> str:
    """获取 RAG 上下文文本"""
    results = retrieve(query, top_k)
    
    if not results:
        return ""
    
    context_parts = ["[记忆检索结果]"]
    
    for i, result in enumerate(results, 1):
        score_info = f"相关度: {result['score']:.2f}"
        if "rerank_score" in result:
            score_info += f" | 重排序: {result['rerank_score']:.3f}"
        
        context_parts.append(f"\n### 相关片段 {i} ({score_info})")
        context_parts.append(result['text'])
    
    context_parts.append("\n[/记忆检索结果]")
    
    return "\n".join(context_parts)


def add_memory(content: str, metadata: Optional[Dict] = None) -> bool:
    """增量添加记忆到 MEMORY.md"""
    global _memory_file_md5
    
    try:
        if not MEMORY_FILE.exists():
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            MEMORY_FILE.write_text("# 长期记忆\n\n", encoding="utf-8")
        
        current_content = MEMORY_FILE.read_text(encoding="utf-8")
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"\n---\n\n### [{timestamp}]\n{content}\n"
        
        MEMORY_FILE.write_text(current_content + new_entry, encoding="utf-8")
        
        # 标记需要重建索引
        _memory_file_md5 = None
        
        return True
        
    except Exception as e:
        print(f"添加记忆失败: {str(e)}")
        return False


def check_duplicate(content: str, threshold: float = 0.85) -> bool:
    """检查内容是否与现有记忆重复
    
    Args:
        content: 待检查内容
        threshold: 相似度阈值
    
    Returns:
        True 表示已存在相似内容（重复）
    """
    global _nodes_cache
    
    if _nodes_cache is None or len(_nodes_cache) == 0:
        return False
    
    try:
        # 获取新内容的向量
        embed_model = _get_embedding_model()
        new_embedding = embed_model._get_text_embedding(content)
        
        import numpy as np
        new_vec = np.array(new_embedding)
        
        # 与现有节点比较
        for node in _nodes_cache:
            node_embedding = embed_model._get_text_embedding(node.text)
            node_vec = np.array(node_embedding)
            
            # 余弦相似度
            similarity = np.dot(new_vec, node_vec) / (
                np.linalg.norm(new_vec) * np.linalg.norm(node_vec)
            )
            
            if similarity > threshold:
                return True
        
        return False
        
    except Exception as e:
        print(f"检查重复失败: {str(e)}")
        return False


def add_memory_if_new(content: str, metadata: Optional[Dict] = None) -> bool:
    """添加记忆（如果不存在相似内容）"""
    if check_duplicate(content):
        print("⚠ 检测到相似记忆，跳过添加")
        return False
    
    return add_memory(content, metadata)


def cleanup_memory(
    max_age_days: int = 90,
    min_importance: float = 0.3,
    max_entries: int = 200,
    dry_run: bool = False
) -> Dict[str, Any]:
    """清理过期/低重要性的记忆
    
    清理规则：
    1. 超过 max_age_days 天且重要性 < min_importance 的记忆
    2. 超过 max_entries 条时，删除最旧的低重要性记忆
    
    Args:
        max_age_days: 最大保留天数（默认90天）
        min_importance: 最低重要性阈值（默认0.3）
        max_entries: 最大记忆条数（默认200）
        dry_run: 仅模拟，不实际删除
    
    Returns:
        清理统计 {"removed": int, "kept": int, "reasons": [str]}
    """
    global _memory_file_md5
    
    if not MEMORY_FILE.exists():
        return {"removed": 0, "kept": 0, "reasons": ["记忆文件不存在"]}
    
    try:
        import re
        from datetime import datetime, timedelta
        
        content = MEMORY_FILE.read_text(encoding="utf-8")
        
        # 解析记忆条目（按时间戳分割）
        # 格式: ### [2026-02-23 10:30]
        entry_pattern = r'### \[(\d{4}-\d{2}-\d{2})(?: \d{2}:\d{2})?\]'
        
        # 分割条目
        entries = re.split(r'(### \[\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?\])', content)
        
        # 第部分是头部（标题和说明），保留
        header = entries[0] if entries else ""
        
        # 重组条目
        memory_entries = []
        for i in range(1, len(entries), 2):
            if i + 1 < len(entries):
                timestamp_marker = entries[i]
                entry_content = entries[i + 1]
                
                # 提取日期
                date_match = re.search(r'\[(\d{4}-\d{2}-\d{2})', timestamp_marker)
                if date_match:
                    entry_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                else:
                    entry_date = datetime.now()
                
                # 判断重要性
                importance = 0.5  # 默认中等重要性
                if "[user_profile]" in entry_content or "[important_event]" in entry_content:
                    importance = 0.8
                elif "#important" in entry_content or "#关键" in entry_content:
                    importance = 0.9
                elif "临时" in entry_content or "#temp" in entry_content:
                    importance = 0.2
                
                memory_entries.append({
                    "marker": timestamp_marker,
                    "content": entry_content,
                    "date": entry_date,
                    "importance": importance,
                    "full": timestamp_marker + entry_content
                })
        
        # 清理逻辑
        now = datetime.now()
        cutoff_date = now - timedelta(days=max_age_days)
        
        kept_entries = []
        removed_count = 0
        reasons = []
        
        # 按重要性排序，高重要性的优先保留
        memory_entries.sort(key=lambda x: (-x["importance"], -x["date"].timestamp()))
        
        for entry in memory_entries:
            age_days = (now - entry["date"]).days
            should_remove = False
            reason = ""
            
            # 规则1: 超时且低重要性
            if entry["date"] < cutoff_date and entry["importance"] < min_importance:
                should_remove = True
                reason = f"过期({age_days}天)且低重要性({entry['importance']:.1f})"
            
            # 规则2: 超过数量限制（只删除低重要性的）
            elif len(kept_entries) >= max_entries and entry["importance"] < 0.5:
                should_remove = True
                reason = f"超过数量限制({max_entries})且低重要性"
            
            if should_remove:
                removed_count += 1
                reasons.append(f"- {entry['content'][:30]}... : {reason}")
            else:
                kept_entries.append(entry)
        
        # 按日期重新排序保留的条目
        kept_entries.sort(key=lambda x: x["date"], reverse=True)
        
        if not dry_run and removed_count > 0:
            # 重建记忆文件
            new_content = header.rstrip() + "\n"
            for entry in kept_entries:
                new_content += "\n" + entry["full"].strip() + "\n"
            
            MEMORY_FILE.write_text(new_content, encoding="utf-8")
            
            # 标记需要重建索引
            _memory_file_md5 = None
            
            print(f"✓ 已清理 {removed_count} 条记忆，保留 {len(kept_entries)} 条")
        
        return {
            "removed": removed_count,
            "kept": len(kept_entries),
            "reasons": reasons,
            "dry_run": dry_run
        }
        
    except Exception as e:
        print(f"清理记忆失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"removed": 0, "kept": 0, "reasons": [f"错误: {str(e)}"]}


def get_memory_stats() -> Dict[str, Any]:
    """获取记忆统计信息"""
    if not MEMORY_FILE.exists():
        return {
            "exists": False,
            "entries": 0,
            "size_kb": 0,
            "oldest": None,
            "newest": None
        }
    
    try:
        import re
        from datetime import datetime
        
        content = MEMORY_FILE.read_text(encoding="utf-8")
        size_kb = len(content.encode("utf-8")) / 1024
        
        # 统计条目数
        entry_pattern = r'### \[\d{4}-\d{2}-\d{2}'
        entries = re.findall(entry_pattern, content)
        entry_count = len(entries)
        
        # 提取日期范围
        dates = re.findall(r'\[(\d{4}-\d{2}-\d{2})', content)
        if dates:
            parsed_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
            oldest = min(parsed_dates).strftime("%Y-%m-%d")
            newest = max(parsed_dates).strftime("%Y-%m-%d")
        else:
            oldest = None
            newest = None
        
        return {
            "exists": True,
            "entries": entry_count,
            "size_kb": round(size_kb, 2),
            "oldest": oldest,
            "newest": newest
        }
        
    except Exception as e:
        return {
            "exists": True,
            "entries": 0,
            "size_kb": 0,
            "oldest": None,
            "newest": None,
            "error": str(e)
        }


__all__ = [
    "rebuild_index",
    "retrieve",
    "get_rag_context",
    "add_memory",
    "add_memory_if_new",
    "check_duplicate",
    "cleanup_memory",
    "get_memory_stats",
    "MEMORY_FILE",
    "MEMORY_INDEX_DIR",
]
