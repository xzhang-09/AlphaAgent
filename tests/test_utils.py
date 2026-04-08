import os
from pathlib import Path

from data.clients import _fmp_symbol_candidates
from config.env import load_dotenv
from utils.source_summary import build_data_status, citation_source_counts, describe_filings_source, describe_fundamentals_source
from utils.ticker import is_valid_ticker_format, normalize_ticker, suggest_ticker_correction


def test_ticker_helpers_normalize_and_correct_common_typos():
    assert normalize_ticker(" appl ") == "APPL"
    assert suggest_ticker_correction("appl") == "AAPL"
    assert is_valid_ticker_format("0700.HK") is True
    assert is_valid_ticker_format("bad ticker") is False


def test_source_summary_builds_status_and_counts():
    result = {
        "market_snapshot": {"current_price": 190.0},
        "fundamentals_snapshot": {
            "source": "financial_modeling_prep",
            "source_detail": "Core profile and statement fields came from FMP free-compatible endpoints.",
            "revenue_growth_yoy": 12.0,
        },
        "rag_context": {
            "filing_docs": [{"id": "f1", "url": "https://www.sec.gov/Archives/example.htm"}],
            "transcript_docs": [],
            "news_docs": [{"id": "n1"}, {"id": "n2"}],
            "asia_news_docs": [],
        },
        "fx_snapshot": {"reference_pairs": {"USDJPY": 149.5}},
        "peer_snapshot": [{"ticker": "MSFT"}],
        "citations": [
            {"source_type": "filing"},
            {"source_type": "news"},
            {"source_type": "news"},
        ],
    }

    counts = citation_source_counts(result["citations"])
    statuses = build_data_status(result)

    assert counts == {"filing": 1, "news": 2}
    assert any(row["section"] == "Filings" and row["status"] == "available" for row in statuses)
    assert any(row["section"] == "Transcripts" and row["status"] == "missing" for row in statuses)
    assert any(row["section"] == "Fundamentals" and row["source"] == "FMP Stable" for row in statuses)
    assert any(row["section"] == "Filings" and row["source"] == "SEC Fallback" for row in statuses)


def test_fmp_symbol_candidates_include_known_aliases():
    assert _fmp_symbol_candidates("GOOG") == ["GOOG", "GOOGL"]
    assert _fmp_symbol_candidates("BRK.B") == ["BRK.B", "BRK-B"]


def test_source_descriptions_map_fallback_labels():
    assert describe_fundamentals_source({"source": "yahoo_finance_fallback"}) == "Yahoo Fallback"
    assert describe_filings_source([{"url": "https://example.com/fmp-filing"}]) == "FMP Stable"


def test_load_dotenv_overrides_empty_env_value(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("FMP_API_KEY=from-dotenv\n")
    monkeypatch.setenv("FMP_API_KEY", "")

    load_dotenv(env_path)

    assert os.getenv("FMP_API_KEY") == "from-dotenv"
