import unittest

from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG


class PageIndexQueryNormalizationTests(unittest.TestCase):
    def test_extracts_question_from_explanatory_wrapper(self):
        rewritten = (
            "The original query is already a standalone question that makes sense "
            "without relying on any previous context. Therefore, I will leave it unchanged:\n\n"
            "\"When did World War 2 begin?\""
        )

        self.assertEqual(
            ConversationalRAG._normalize_pageindex_query(
                original_input="When did World War 2 begin?",
                rewritten_question=rewritten,
            ),
            "When did World War 2 begin?",
        )

    def test_falls_back_to_original_for_narrative_text(self):
        self.assertEqual(
            ConversationalRAG._normalize_pageindex_query(
                original_input="Who started the war?",
                rewritten_question="The original query is already a standalone question.",
            ),
            "Who started the war?",
        )

    def test_preserves_clean_rewritten_question(self):
        self.assertEqual(
            ConversationalRAG._normalize_pageindex_query(
                original_input="When did it begin?",
                rewritten_question="When did World War 2 begin?",
            ),
            "When did World War 2 begin?",
        )


if __name__ == "__main__":
    unittest.main()
