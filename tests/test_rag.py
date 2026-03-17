from engine.rag_processor import RAGProcessor


def test_rag_retrieval_returns_expected_metadata():
    processor = RAGProcessor()
    context = processor.build_context("TSM")
    results = processor.retrieve(context, "currency margin", top_k=2)
    assert results
    assert "metadata" in results[0]
    assert "citation_id" in results[0]["metadata"]
