import unittest

from multi_doc_chat.src.document_chat.pageindex_retriever import _extract_contexts


class PageIndexRetrieverTests(unittest.TestCase):
    def test_extracts_retrieved_nodes_content(self):
        payload = {
            "status": "completed",
            "retrieved_nodes": [
                {"content": "alpha"},
                {"content": "beta"},
            ],
        }

        self.assertEqual(_extract_contexts(payload, top_k=5), ["alpha", "beta"])

    def test_extracts_nested_results_text(self):
        payload = {
            "status": "completed",
            "results": [
                {"node": {"text": "section one"}},
                {"node": {"text": "section two"}},
            ],
        }

        self.assertEqual(
            _extract_contexts(payload, top_k=5),
            ["section one", "section two"],
        )

    def test_falls_back_to_single_answer_text(self):
        payload = {
            "status": "completed",
            "answer": "fallback synthesized context",
        }

        self.assertEqual(
            _extract_contexts(payload, top_k=5),
            ["fallback synthesized context"],
        )

    def test_extracts_nested_content_dict(self):
        payload = {
            "status": "completed",
            "retrieved_nodes": [
                {"content": {"text": "nested node text"}},
            ],
        }

        self.assertEqual(
            _extract_contexts(payload, top_k=5),
            ["nested node text"],
        )

    def test_extracts_pageindex_relevant_contents(self):
        payload = {
            "status": "completed",
            "retrieved_nodes": [
                {
                    "id": "node-1",
                    "title": "KubeLLM",
                    "metadata": [{"page": 2}],
                    "relevant_contents": [
                        {"text": "KubeLLM is a Kubernetes-native LLM gateway."},
                        {"text": "It provides context-aware diagnostic synthesis for MetaKube."},
                    ],
                }
            ],
        }

        self.assertEqual(
            _extract_contexts(payload, top_k=5),
            [
                "KubeLLM is a Kubernetes-native LLM gateway.\nIt provides context-aware diagnostic synthesis for MetaKube."
            ],
        )

    def test_prefers_relevant_contents_over_title(self):
        payload = {
            "status": "completed",
            "retrieved_nodes": [
                {
                    "id": "node-2",
                    "title": "C.1 Kubernetes Fault Resolution Dataset Construction",
                    "relevant_contents": [
                        {
                            "title": "C.1 Kubernetes Fault Resolution Dataset Construction",
                            "sections": [
                                {
                                    "text": "The KFRD dataset is built by collecting fault cases from Kubernetes incidents.",
                                },
                                {
                                    "text": "Each case is annotated with the fault type, symptoms, root cause, and remediation steps.",
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        self.assertEqual(
            _extract_contexts(payload, top_k=5),
            [
                "The KFRD dataset is built by collecting fault cases from Kubernetes incidents.\nEach case is annotated with the fault type, symptoms, root cause, and remediation steps."
            ],
        )


if __name__ == "__main__":
    unittest.main()
