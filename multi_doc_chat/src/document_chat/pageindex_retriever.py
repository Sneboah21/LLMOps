import os
import time
from typing import Any, Dict, Iterable, List

from pageindex import PageIndexClient 
from multi_doc_chat.logger.custom_logger import CustomLogger


log = CustomLogger().get_logger(__name__)


class PageIndexNotReadyError(Exception):
    pass


_PREFERRED_TEXT_KEYS = (
    "text",
    "content",
    "page_content",
    "markdown",
    "content_markdown",
    "content_md",
    "value",
    "chunk",
    "passage",
    "snippet",
    "raw_text",
)

_STRUCTURAL_KEYS = {
    "id",
    "doc_id",
    "document_id",
    "node_id",
    "metadata",
    "title",
}


def _extract_text_field(value: Any, skip_keys: Iterable[str] = ()) -> List[str]:
    skip_keys = set(skip_keys)

    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

    if isinstance(value, list):
        snippets: List[str] = []
        for item in value:
            snippets.extend(_extract_text_field(item, skip_keys=skip_keys))
        return snippets

    if isinstance(value, dict):
        snippets: List[str] = []

        for key in _PREFERRED_TEXT_KEYS:
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                snippets.append(nested.strip())
            if isinstance(nested, (dict, list)):
                snippets.extend(_extract_text_field(nested, skip_keys=skip_keys))

        for key, nested in value.items():
            if key in skip_keys or key in _PREFERRED_TEXT_KEYS or key in _STRUCTURAL_KEYS:
                continue
            if isinstance(nested, str) and nested.strip():
                snippets.append(nested.strip())
            elif isinstance(nested, (dict, list)):
                snippets.extend(_extract_text_field(nested, skip_keys=skip_keys))

        return snippets

    return []


def _extract_text_from_node(node: Any) -> List[str]:
    """
    Normalize a retrieval payload node into one or more text snippets.

    The PageIndex API may return slightly different shapes depending on the
    retrieval mode or SDK version, so we accept several common keys.
    """
    if isinstance(node, str):
        text = node.strip()
        return [text] if text else []

    if isinstance(node, list):
        snippets: List[str] = []
        for item in node:
            snippets.extend(_extract_text_from_node(item))
        return snippets

    if not isinstance(node, dict):
        return []

    # PageIndex retrieval nodes commonly return:
    # {"title": "...", "relevant_contents": [...], "metadata": [...]}
    # Prefer the matched content snippets over generic fallback traversal.
    relevant_contents = node.get("relevant_contents")
    if relevant_contents:
        snippets = _extract_text_field(relevant_contents, skip_keys={"title", "metadata"})
        deduped_snippets: List[str] = []
        seen = set()
        for snippet in snippets:
            normalized = " ".join(snippet.split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped_snippets.append(snippet)
        snippets = deduped_snippets
        if snippets:
            return ["\n".join(snippets)]

    direct_keys = (
        "content",
        "text",
        "page_content",
        "markdown",
        "content_markdown",
        "content_md",
        "value",
        "chunk",
        "passage",
        "snippet",
        "raw_text",
        "title",
    )
    for key in direct_keys:
        if relevant_contents and key == "title":
            continue
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, (dict, list)):
            nested = _extract_text_from_node(value)
            if nested:
                return nested

    nested_keys = (
        "node",
        "document",
        "result",
        "results",
        "data",
        "items",
        "chunks",
        "passages",
        "contexts",
        "relevant_contents",
        "metadata",
        "retrieved_nodes",
    )
    snippets: List[str] = []
    for key in nested_keys:
        value = node.get(key)
        if value:
            snippets.extend(_extract_text_from_node(value))

    return snippets


def _describe_node(node: Any) -> Dict[str, Any]:
    if isinstance(node, dict):
        description = {
            "type": "dict",
            "keys": sorted(node.keys()),
            "value_types": {
                key: type(value).__name__
                for key, value in node.items()
            },
        }
        relevant_contents = node.get("relevant_contents")
        if isinstance(relevant_contents, list) and relevant_contents:
            description["relevant_contents_length"] = len(relevant_contents)
            sample_text = " ".join(_extract_text_field(relevant_contents[0], skip_keys={"title", "metadata"}))
            description["relevant_contents_sample"] = sample_text[:120]
        metadata = node.get("metadata")
        if isinstance(metadata, list) and metadata:
            description["metadata_length"] = len(metadata)
            description["metadata_sample"] = _describe_node(metadata[0])
        return description
    if isinstance(node, list):
        return {
            "type": "list",
            "length": len(node),
        }
    return {
        "type": type(node).__name__,
        "value_preview": str(node)[:200],
    }


def _extract_contexts(retrieval_result: Dict[str, Any], top_k: int) -> List[str]:
    """
    Extract context snippets from a PageIndex retrieval response.
    """
    candidate_keys: Iterable[str] = (
        "retrieved_nodes",
        "nodes",
        "results",
        "data",
        "contexts",
        "chunks",
        "passages",
        "items",
    )

    contexts: List[str] = []
    for key in candidate_keys:
        value = retrieval_result.get(key)
        if value:
            contexts.extend(_extract_text_from_node(value))
        if len(contexts) >= top_k:
            break

    if not contexts:
        # Last-resort support for APIs that return a single synthesized snippet.
        for key in ("content", "text", "answer", "response"):
            value = retrieval_result.get(key)
            if isinstance(value, str) and value.strip():
                contexts.append(value.strip())
                break

    deduped: List[str] = []
    seen = set()
    for text in contexts:
        normalized = " ".join(text.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(text)
        if len(deduped) >= top_k:
            break

    return deduped


def _resolve_api_key(raw: str) -> str:
    """
    Supports values like:
      - "env:PAGEINDEX_API_KEY"
      - plain literal "sk-xxx"
    """
    if raw.startswith("env:"):
        env_name = raw.split("env:", 1)[1].strip()
        value = os.getenv(env_name)
        if not value:
            raise RuntimeError(f"Environment variable {env_name} is not set")
        return value
    return raw


def get_pageindex_client(cfg: dict) -> PageIndexClient:
    """
    Create and return a PageIndexClient from config.
    """
    pi_cfg = cfg.get("pageindex", {})
    raw_key = pi_cfg.get("api_key")
    if not raw_key:
        raise RuntimeError("pageindex.api_key is not configured in config.yaml")

    api_key = _resolve_api_key(raw_key)
    base_url = pi_cfg.get("base_url", "https://api.pageindex.ai")

    client = PageIndexClient(api_key=api_key)  # base_url is defaulted in SDK for now 
    # If future SDK supports base_url, you can pass it here.
    return client


def submit_document(file_path: str, session_id: str, client: PageIndexClient) -> str:
    """
    Uploads a document to PageIndex and returns doc_id.

    Uses the official submit_document API which takes a file path. 
    """
    result = client.submit_document(file_path)
    doc_id = result["doc_id"]
    return doc_id
#-------------------------------------------------
def delete_pageindex_document(
    doc_id: str,
    client: PageIndexClient,
) -> bool:
    """
    Delete a PageIndex document by doc_id.

    Returns:
        True  -> document deleted remotely
        False -> document was already missing / not found

    Raises:
        RuntimeError or SDK exception for non-idempotent failures
    """
    if not doc_id:
        return False

    try:
        delete_fn = getattr(client, "delete_document", None)
        if delete_fn is None:
            raise RuntimeError(
                "PageIndex client does not expose delete_document(doc_id)"
            )

        delete_fn(doc_id)

        log.info(
            "PageIndex document deleted",
            doc_id=doc_id,
        )
        return True

    except Exception as e:
        message = str(e).lower()

        if any(token in message for token in ("not found", "404", "does not exist", "missing")):
            log.warning(
                "PageIndex document already absent",
                doc_id=doc_id,
                error=str(e),
            )
            return False

        log.error(
            "Failed to delete PageIndex document",
            doc_id=doc_id,
            error=str(e),
        )
        raise
#-------------------------------------------------

def wait_until_retrieval_ready(
    doc_id: str,
    client: PageIndexClient,
    timeout_seconds: int = 300,
    poll_interval_seconds: int = 5,
) -> None:
    """
    Poll PageIndex until the document is ready for retrieval,
    or raise PageIndexNotReadyError on timeout. 
    """
    deadline = time.time() + timeout_seconds
    last_status = None
    while time.time() < deadline:
        retrieval_ready = client.is_retrieval_ready(doc_id)
        meta = client.get_document(doc_id)
        status = meta.get("status")
        last_status = status
        log.info(
            "PageIndex retrieval readiness polled",
            doc_id=doc_id,
            status=status,
            retrieval_ready=retrieval_ready,
        )
        if retrieval_ready:
            return
        if status == "failed":
            raise PageIndexNotReadyError(f"PageIndex processing failed for doc_id={doc_id}")
        time.sleep(poll_interval_seconds)

    raise PageIndexNotReadyError(
        f"Timed out waiting for PageIndex retrieval readiness for doc_id={doc_id} (last_status={last_status})"
    )


def retrieve_with_pageindex(
    query: str,
    session_doc_ids: List[str],
    client: PageIndexClient,
    top_k: int,
    thinking: bool = False,
) -> List[str]:
    """
    Retrieve relevant content from PageIndex for the given query.

    This uses the Retrieval SDK:
      - is_retrieval_ready(doc_id)
      - submit_query(doc_id, query)
      - get_retrieval(retrieval_id)

    We return a list of text segments (strings) suitable as RAG context. 
    """
    if not session_doc_ids:
        return []

    # For now, handle one doc_id at a time; you can extend to multi-doc later.
    contexts: List[str] = []

    for doc_id in session_doc_ids:
        log.info(
            "Starting PageIndex retrieval",
            doc_id=doc_id,
            query_preview=query[:200],
            top_k=top_k,
        )

        # Ensure document is ready for retrieval before submit_query
        if not client.is_retrieval_ready(doc_id):
            wait_until_retrieval_ready(doc_id, client, timeout_seconds=300, poll_interval_seconds=5)

        if not client.is_retrieval_ready(doc_id):
            raise PageIndexNotReadyError(
                f"Document is not retrieval-ready after waiting for doc_id={doc_id}"
            )

        # Submit retrieval query
        retrieval = client.submit_query(
            doc_id=doc_id,
            query=query,
            thinking=thinking,
        )
        retrieval_id = retrieval["retrieval_id"]
        log.info(
            "PageIndex retrieval submitted",
            doc_id=doc_id,
            retrieval_id=retrieval_id,
        )

        # Poll until retrieval is complete
        while True:
            retrieval_result = client.get_retrieval(retrieval_id)
            status = retrieval_result.get("status")
            retrieved_nodes = retrieval_result.get("retrieved_nodes", [])
            retrieved_nodes_length = (
                len(retrieved_nodes)
                if isinstance(retrieved_nodes, list)
                else None
            )
            log.info(
                "PageIndex retrieval polled",
                doc_id=doc_id,
                retrieval_id=retrieval_id,
                status=status,
                retrieved_nodes_type=type(retrieved_nodes).__name__,
                retrieved_nodes_length=retrieved_nodes_length,
                retrieval_result_keys=sorted(retrieval_result.keys()),
            )
            if status == "completed":
                break
            elif status == "failed":
                raise PageIndexNotReadyError(
                    f"Retrieval failed for doc_id={doc_id}, retrieval_id={retrieval_id}"
                )
            time.sleep(2)

        if isinstance(retrieved_nodes, list):
            node_summaries = [
                _describe_node(node)
                for node in retrieved_nodes[: min(len(retrieved_nodes), top_k)]
            ]
        else:
            node_summaries = [_describe_node(retrieved_nodes)]

        log.info(
            "PageIndex retrieved_nodes inspected",
            doc_id=doc_id,
            retrieval_id=retrieval_id,
            retrieved_nodes_type=type(retrieved_nodes).__name__,
            retrieved_nodes_length=retrieved_nodes_length,
            retrieved_nodes_sample=node_summaries,
        )

        extracted_contexts = _extract_contexts(retrieval_result, top_k)
        log.info(
            "PageIndex contexts extracted",
            doc_id=doc_id,
            retrieval_id=retrieval_id,
            extracted_context_count=len(extracted_contexts),
            extracted_context_previews=[text[:120] for text in extracted_contexts[:top_k]],
        )
        contexts.extend(extracted_contexts)

    # If more contexts than top_k across docs, truncate
    if len(contexts) > top_k:
        contexts = contexts[:top_k]

    return contexts
