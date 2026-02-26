#!/usr/bin/env python3
"""
LLM client wrapper for LM Studio using LangChain's OpenAI-compatible ChatOpenAI.
Provides structured operations (title improvement, tags, summary, classification, entities)
with robust error handling and optional logging to EnhancedCrawlerDatabase.
"""
from __future__ import annotations

import json
import time
import os
from typing import Dict, List, Optional, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import CrawlerConfig
try:
    # Optional: only used if provided by caller
    from database_enhanced import EnhancedCrawlerDatabase  # type: ignore
except Exception:  # pragma: no cover
    EnhancedCrawlerDatabase = None  # type: ignore


class LLMClient:
    """Typed LM Studio client built on LangChain ChatOpenAI."""

    def __init__(
        self,
        config: CrawlerConfig,
        db: Optional["EnhancedCrawlerDatabase"] = None,
    ) -> None:
        self.config = config
        self.db = db
        # LM Studio exposes an OpenAI-compatible endpoint
        base_url = getattr(config, "LMSTUDIO_BASE_URL", None) or "http://localhost:1234/v1"
        model = getattr(config, "LMSTUDIO_MODEL", None) or "Llama-3.1-8B-Instruct"
        temperature = float(getattr(config, "LLM_TEMPERATURE", 0.2))
        timeout = int(getattr(config, "LLM_TIMEOUT", 60))
        max_retries = int(getattr(config, "LLM_MAX_RETRIES", 2))

        # Fallback models from env (comma-separated)
        fb_env = os.getenv("LMSTUDIO_FALLBACK_MODELS", "")
        self.fallback_models: List[str] = [m.strip() for m in fb_env.split(",") if m.strip()]

        self.base_url = base_url
        self.model_id = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        # No API key required by LM Studio
        self.llm = ChatOpenAI(
            model=self.model_id,
            base_url=self.base_url,
            api_key="lm-studio",  # dummy key; LM Studio ignores it
            temperature=self.temperature,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def _invoke_json(self, messages: list, op_type: str) -> Dict:
        start = time.time()
        err: Optional[str] = None
        out: Dict = {}
        try:
            response = self.llm.invoke(messages)
            text = getattr(response, "content", str(response)).strip()
            # best-effort JSON extraction
            if text.startswith("{"):
                out = json.loads(text)
            else:
                import re
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    out = json.loads(m.group(0))
                else:
                    out = {}
        except Exception as e:  # pragma: no cover
            err = str(e)
            # Fallback: try alternate model IDs if LM Studio reports not loaded
            tried: List[str] = []
            for alt in self.fallback_models:
                tried.append(alt)
                try:
                    self.llm = ChatOpenAI(
                        model=alt,
                        base_url=self.base_url,
                        api_key="lm-studio",
                        temperature=self.temperature,
                        timeout=self.timeout,
                        max_retries=self.max_retries,
                    )
                    response = self.llm.invoke(messages)
                    text = getattr(response, "content", str(response)).strip()
                    if text.startswith("{"):
                        out = json.loads(text)
                    else:
                        import re
                        m = re.search(r"\{[\s\S]*\}", text)
                        out = json.loads(m.group(0)) if m else {}
                    err = None
                    break
                except Exception as e2:  # continue to next fallback
                    err = f"fallback({alt}) failed: {e2}"
                    continue
            if err:
                out = {}
        finally:
            self._log(op_type, messages, out, int((time.time() - start) * 1000), err)
        return out

    def _log(self, op_type: str, messages: list, output: Dict, duration_ms: int, error: Optional[str]) -> None:
        if not self.db:
            return
        try:
            # Ensure input_data is JSON-serializable
            try:
                template_repr = [getattr(m, 'content', str(m)) for m in messages]
            except Exception:
                template_repr = ["<unserializable message>"]
            self.db.log_llm_operation(
                operation_type=op_type,
                input_data={"messages": template_repr},
                output_data=output,
                tokens=0,
                duration_ms=duration_ms,
                model=getattr(self.llm, "model_name", "lm-studio"),
                status="failure" if error else "success",
                error=error,
            )
        except Exception:
            pass

    # ------------------------ Operations ------------------------

    def improve_title(self, title: str, content_preview: str) -> str:
        messages = [
            SystemMessage(content="You improve web page titles. Return JSON: {\"title\": \"improved\"}. Max 80 chars."),
            HumanMessage(content=f"Original: {title}\n\nPreview: {content_preview[:500]}")
        ]
        data = self._invoke_json(messages, op_type="title_improve")
        candidate = (data.get("title") or title).strip()
        return candidate[:80] if candidate else title

    def extract_tags(self, title: str, content: str) -> List[str]:
        messages = [
            SystemMessage(content="Extract 3-7 lowercase tags. Return JSON: {\"tags\": [..]}.")
            ,HumanMessage(content=f"Title: {title}\n\nContent: {content[:1000]}")
        ]
        data = self._invoke_json(messages, op_type="tag_extract")
        tags = data.get("tags") or []
        result: List[str] = []
        for t in tags[:7]:
            if isinstance(t, str):
                t = t.strip().lower()
                if 2 <= len(t) <= 24:
                    result.append(t)
        return result or [CrawlerConfig.TAG_PREFIX]

    def summarize(self, title: str, content: str) -> str:
        messages = [
            SystemMessage(content="Write a concise 1-2 sentence summary (<= 280 chars). Return JSON: {\"summary\": \"...\"}."),
            HumanMessage(content=f"Title: {title}\n\nContent: {content[:1500]}")
        ]
        data = self._invoke_json(messages, op_type="summarize")
        return (data.get("summary") or "").strip()[:280]

    def classify_page(self, title: str, content: str) -> Tuple[str, str]:
        """Returns (page_type, lang)."""
        messages = [
            SystemMessage(content=(
                "Classify page type (docs, blog, guide, api, reference, article, other) and language (BCP47). "
                "Return JSON: {\"page_type\":\"docs\", \"lang\":\"en\"}."
            )),
            HumanMessage(content=f"Title: {title}\n\nContent: {content[:1200]}")
        ]
        data = self._invoke_json(messages, op_type="classify")
        page_type = (data.get("page_type") or "other").strip().lower()
        lang = (data.get("lang") or "en").strip().lower()
        return page_type, lang

    def extract_entities(self, title: str, content: str) -> List[Dict]:
        messages = [
            SystemMessage(content="Extract up to 10 entities (kind,label). Return JSON: {\"entities\":[{\"kind\":\"concept\",\"label\":\"...\"}]}.")
            ,HumanMessage(content=f"Title: {title}\n\nContent: {content[:1500]}")
        ]
        data = self._invoke_json(messages, op_type="entities")
        entities = data.get("entities") or []
        cleaned: List[Dict] = []
        for e in entities[:10]:
            if isinstance(e, dict) and e.get("kind") and e.get("label"):
                cleaned.append({"kind": str(e["kind"]).lower(), "label": str(e["label"]).strip()})
        return cleaned
