#!/usr/bin/env python3
"""
Embeddings and semantic search manager using ChromaDB and sentence-transformers.
Persists embeddings to a local directory and provides batch upsert/query.
"""
from __future__ import annotations

from typing import Iterable, List, Dict, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from config import CrawlerConfig


class EmbeddingsManager:
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.client = chromadb.PersistentClient(
            path=str(config.CHROMA_PERSIST_DIR),
            settings=Settings(allow_reset=False),
        )
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDINGS_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name=config.CHROMA_COLLECTION, embedding_function=self.embed_fn
        )

    def upsert_pages(self, items: Iterable[Tuple[str, str, Dict]]):
        """
        Upsert pages into the vector store.
        items: iterable of (doc_id, content, metadata)
        """
        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict] = []
        for i, c, m in items:
            ids.append(i)
            docs.append(c)
            metas.append(m)
        if ids:
            self.collection.upsert(ids=ids, documents=docs, metadatas=metas)

    def upsert_page(self, doc_id: str, content: str, metadata: Optional[Dict] = None):
        self.collection.upsert(ids=[doc_id], documents=[content], metadatas=[metadata or {}])

    def query_similar(self, content: str, top_k: int, threshold: float = 0.75, exclude_ids: Optional[List[str]] = None) -> List[Dict]:
        res = self.collection.query(
            query_texts=[content],
            n_results=top_k + (len(exclude_ids) if exclude_ids else 0),
        )
        results: List[Dict] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        dists = res.get("distances", [[]]) or res.get("embeddings", [[]])  # distances present when similarity function used
        dlist = (dists[0] if dists else [])
        for idx, doc_id in enumerate(ids):
            if exclude_ids and doc_id in exclude_ids:
                continue
            score = 1.0 - float(dlist[idx]) if dlist else 0.0  # Chroma returns distance; convert to similarity if available
            if score >= threshold:
                results.append({"id": doc_id, "score": score, "preview": docs[idx]})
            if len(results) >= top_k:
                break
        return results
