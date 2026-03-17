from pipelines.research_graph import ResearchGraph, run_research


def test_research_graph_nvda_generates_memo():
    result = run_research("NVDA")
    assert result["company_profile"]["ticker"] == "NVDA"
    assert "PM Memo" in result["final_output"]["final_memo_markdown"]
    assert result["signal_output"]["candidate"] is True
    assert len(result["citations"]) >= 3
    assert result["final_output"]["passed_evaluator"] is True


def test_research_graph_tsm_contains_asia_context():
    result = run_research("TSM")
    assert result["company_profile"]["region"] == "Taiwan"
    assert "currency sensitivity" in result["final_output"]["final_memo_markdown"].lower()
    assert result["critic_output"]["needs_refinement"] is False
    assert "finalize complete" in result["status_log"]


def test_research_graph_sets_explicit_recursion_limit():
    captured = {}

    class _GraphStub:
        def invoke(self, state, config=None):
            captured["config"] = config
            return state

    graph = ResearchGraph()
    graph.graph = _GraphStub()

    graph.run("0700.HK")

    assert captured["config"] == {"recursion_limit": 50}
