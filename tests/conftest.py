from __future__ import annotations

import pytest


LIVE_QUOTES = {
    "NVDA": {
        "shortName": "NVIDIA",
        "longName": "NVIDIA Corporation",
        "currency": "USD",
        "region": "United States",
        "regularMarketPrice": 910.0,
        "forwardPE": 31.0,
        "trailingPE": 34.0,
        "beta": 1.7,
    },
    "TSM": {
        "shortName": "Taiwan Semiconductor Manufacturing",
        "longName": "Taiwan Semiconductor Manufacturing",
        "currency": "TWD",
        "region": "Taiwan",
        "regularMarketPrice": 145.0,
        "forwardPE": 19.0,
        "trailingPE": 21.0,
        "beta": 1.1,
    },
    "AMD": {
        "shortName": "Advanced Micro Devices",
        "longName": "Advanced Micro Devices",
        "currency": "USD",
        "region": "United States",
        "regularMarketPrice": 175.0,
        "forwardPE": 32.0,
        "trailingPE": 35.0,
        "beta": 1.6,
    },
    "AVGO": {
        "shortName": "Broadcom",
        "longName": "Broadcom Inc.",
        "currency": "USD",
        "region": "United States",
        "regularMarketPrice": 1280.0,
        "forwardPE": 26.0,
        "trailingPE": 28.0,
        "beta": 1.1,
    },
    "ASML": {
        "shortName": "ASML",
        "longName": "ASML Holding N.V.",
        "currency": "EUR",
        "region": "Netherlands",
        "regularMarketPrice": 940.0,
        "forwardPE": 29.0,
        "trailingPE": 31.0,
        "beta": 1.0,
    },
    "005930.KS": {
        "shortName": "Samsung Electronics",
        "longName": "Samsung Electronics",
        "currency": "KRW",
        "region": "South Korea",
        "regularMarketPrice": 78000.0,
        "forwardPE": 15.0,
        "trailingPE": 17.0,
        "beta": 1.0,
    },
    "INTC": {
        "shortName": "Intel",
        "longName": "Intel Corporation",
        "currency": "USD",
        "region": "United States",
        "regularMarketPrice": 42.0,
        "forwardPE": 18.0,
        "trailingPE": 21.0,
        "beta": 0.9,
    },
    "AAPL": {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "currency": "USD",
        "region": "United States",
        "regularMarketPrice": 190.0,
        "forwardPE": 28.0,
        "trailingPE": 30.0,
        "beta": 1.2,
    },
    "JPY=X": {"regularMarketPrice": 149.5},
    "CNH=X": {"regularMarketPrice": 7.22},
    "HKD=X": {"regularMarketPrice": 7.81},
    "TWD=X": {"regularMarketPrice": 31.8},
    "KRW=X": {"regularMarketPrice": 1335.0},
    "SGD=X": {"regularMarketPrice": 1.34},
}


LIVE_SUMMARIES = {
    "NVDA": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "longBusinessSummary": "NVIDIA designs accelerated computing platforms for AI and data center workloads.",
        },
        "financialData": {
            "revenueGrowth": 0.64,
            "grossMargins": 0.76,
            "operatingMargins": 0.53,
            "freeCashflow": 27000000000,
            "operatingCashflow": 32000000000,
            "returnOnEquity": 0.48,
        },
        "defaultKeyStatistics": {"forwardPE": 31.0, "enterpriseToEbitda": 24.0, "beta": 1.7},
    },
    "TSM": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductor Manufacturing",
            "country": "Taiwan",
            "longBusinessSummary": "TSMC manufactures advanced semiconductor wafers for fabless chip customers globally.",
        },
        "financialData": {
            "revenueGrowth": 0.28,
            "grossMargins": 0.54,
            "operatingMargins": 0.42,
            "freeCashflow": 18000000000,
            "operatingCashflow": 24000000000,
            "returnOnEquity": 0.27,
        },
        "defaultKeyStatistics": {"forwardPE": 19.0, "enterpriseToEbitda": 12.0, "beta": 1.1},
    },
    "AMD": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "longBusinessSummary": "AMD develops CPUs and GPUs for data center, PC, and embedded markets.",
        },
        "financialData": {
            "revenueGrowth": 0.12,
            "grossMargins": 0.51,
            "operatingMargins": 0.18,
            "freeCashflow": 2500000000,
            "operatingCashflow": 3800000000,
            "returnOnEquity": 0.11,
        },
        "defaultKeyStatistics": {"forwardPE": 32.0, "enterpriseToEbitda": 21.0, "beta": 1.6},
    },
    "AVGO": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "longBusinessSummary": "Broadcom supplies semiconductor and infrastructure software products.",
        },
        "financialData": {"revenueGrowth": 0.18, "grossMargins": 0.67, "operatingMargins": 0.31, "returnOnEquity": 0.22},
        "defaultKeyStatistics": {"forwardPE": 26.0, "enterpriseToEbitda": 18.0, "beta": 1.1},
    },
    "ASML": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductor Equipment",
            "country": "Netherlands",
            "longBusinessSummary": "ASML provides lithography systems used in advanced chip manufacturing.",
        },
        "financialData": {"revenueGrowth": 0.16, "grossMargins": 0.51, "operatingMargins": 0.33, "returnOnEquity": 0.45},
        "defaultKeyStatistics": {"forwardPE": 29.0, "enterpriseToEbitda": 20.0, "beta": 1.0},
    },
    "005930.KS": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "South Korea",
            "longBusinessSummary": "Samsung Electronics produces memory, foundry, and consumer electronics products.",
        },
        "financialData": {"revenueGrowth": 0.09, "grossMargins": 0.39, "operatingMargins": 0.15, "returnOnEquity": 0.09},
        "defaultKeyStatistics": {"forwardPE": 15.0, "enterpriseToEbitda": 9.0, "beta": 1.0},
    },
    "INTC": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Semiconductors",
            "country": "United States",
            "longBusinessSummary": "Intel designs and manufactures processors and related platform products.",
        },
        "financialData": {"revenueGrowth": 0.03, "grossMargins": 0.42, "operatingMargins": 0.12, "returnOnEquity": 0.05},
        "defaultKeyStatistics": {"forwardPE": 18.0, "enterpriseToEbitda": 11.0, "beta": 0.9},
    },
    "AAPL": {
        "summaryProfile": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "longBusinessSummary": "Apple designs smartphones, personal computers, wearables, and services.",
        },
        "financialData": {"revenueGrowth": 0.08, "grossMargins": 0.46, "operatingMargins": 0.31, "returnOnEquity": 1.4},
        "defaultKeyStatistics": {"forwardPE": 28.0, "enterpriseToEbitda": 20.0, "beta": 1.2},
    },
}


LIVE_CHARTS = {
    "NVDA": {"close": [760.0, 800.0, 850.0, 910.0], "volume": [100.0, 110.0, 120.0, 190.0]},
    "TSM": {"close": [132.0, 136.0, 141.0, 145.0], "volume": [90.0, 88.0, 92.0, 105.0]},
    "AMD": {"close": [160.0, 165.0, 171.0, 175.0], "volume": [95.0, 97.0, 102.0, 170.0]},
    "AVGO": {"close": [1180.0, 1200.0, 1240.0, 1280.0], "volume": [60.0, 62.0, 66.0, 70.0]},
    "ASML": {"close": [880.0, 900.0, 920.0, 940.0], "volume": [55.0, 56.0, 57.0, 60.0]},
    "005930.KS": {"close": [71000.0, 73000.0, 75500.0, 78000.0], "volume": [80.0, 83.0, 85.0, 88.0]},
    "INTC": {"close": [39.0, 40.0, 41.0, 42.0], "volume": [100.0, 101.0, 103.0, 104.0]},
    "AAPL": {"close": [176.0, 181.0, 187.0, 190.0], "volume": [100.0, 102.0, 106.0, 120.0]},
}


LIVE_FUNDAMENTALS = {
    "NVDA": {
        "business_overview": "NVIDIA designs accelerated computing platforms for AI and data center workloads.",
        "revenue_growth_yoy": 64.0,
        "prior_revenue_growth_yoy": 38.0,
        "gross_margin": 76.0,
        "ebit_margin": 52.5,
        "prior_ebit_margin": 46.4,
        "fcf_margin": 28.0,
        "cash_conversion": 118.0,
        "cash_flow_commentary": "Cash generation looks healthy relative to revenue and earnings.",
        "earnings_surprise_pct": 8.5,
        "management_change": "",
        "regulatory_event": "US export controls remain a live overhang for China shipments.",
        "key_business_drivers": [
            "Demand trends across Technology",
            "Competitive position within Semiconductors",
            "Management execution versus guidance",
        ],
        "risk_factors": {
            "competition": "Competitive intensity in Technology could pressure pricing or market share.",
            "regulation": "Regulatory and policy developments in United States may affect sentiment and operations.",
            "execution": "Execution risk remains tied to guidance delivery, costs, and capital allocation.",
        },
        "source": "stubbed_live_data",
    },
    "TSM": {
        "business_overview": "TSMC manufactures advanced semiconductor wafers for fabless chip customers globally.",
        "revenue_growth_yoy": 28.0,
        "prior_revenue_growth_yoy": 12.0,
        "gross_margin": 54.0,
        "ebit_margin": 42.0,
        "prior_ebit_margin": 39.0,
        "fcf_margin": 22.0,
        "cash_conversion": 111.0,
        "cash_flow_commentary": "Cash generation looks healthy relative to revenue and earnings.",
        "earnings_surprise_pct": 6.0,
        "management_change": "",
        "regulatory_event": "",
        "key_business_drivers": [
            "Demand trends across Technology",
            "Competitive position within Semiconductor Manufacturing",
            "Management execution versus guidance",
        ],
        "risk_factors": {
            "competition": "Competitive intensity in Technology could pressure pricing or market share.",
            "regulation": "Regulatory and policy developments in Taiwan may affect sentiment and operations.",
            "execution": "Execution risk remains tied to guidance delivery, costs, and capital allocation.",
        },
        "source": "stubbed_live_data",
    },
}


def _news_docs(query: str) -> list[dict[str, str]]:
    return [
        {
            "title": f"{query} demand outlook",
            "snippet": f"{query} remains in focus as investors evaluate demand trends, margins, and policy developments.",
            "url": "https://example.com/news-1",
            "published_at": "2026-03-15",
        },
        {
            "title": f"{query} earnings watch",
            "snippet": f"{query} earnings and guidance revisions are shaping near-term expectations.",
            "url": "https://example.com/news-2",
            "published_at": "2026-03-14",
        },
    ]


@pytest.fixture(autouse=True)
def stub_live_data(monkeypatch):
    monkeypatch.setattr(
        "data.clients._yahoo_quote",
        lambda ticker: dict(LIVE_QUOTES.get(ticker.upper(), LIVE_QUOTES.get(ticker, {"regularMarketPrice": 100.0, "currency": "USD", "region": "United States", "shortName": ticker, "longName": ticker, "forwardPE": 20.0, "trailingPE": 20.0, "beta": 1.0}))),
    )
    monkeypatch.setattr(
        "data.clients._yahoo_quote_summary",
        lambda ticker: dict(LIVE_SUMMARIES.get(ticker.upper(), LIVE_SUMMARIES.get(ticker, {
            "summaryProfile": {"sector": "Technology", "industry": "Software", "country": "United States", "longBusinessSummary": f"{ticker} live summary."},
            "financialData": {"revenueGrowth": 0.1, "grossMargins": 0.5, "operatingMargins": 0.2, "returnOnEquity": 0.1},
            "defaultKeyStatistics": {"forwardPE": 20.0, "enterpriseToEbitda": 12.0, "beta": 1.0},
        }))),
    )
    monkeypatch.setattr(
        "data.clients._yahoo_chart",
        lambda ticker: dict(LIVE_CHARTS.get(ticker.upper(), {"close": [95.0, 100.0, 105.0], "volume": [100.0, 110.0, 120.0]})),
    )
    monkeypatch.setattr("data.clients._google_news_rss", _news_docs)
    monkeypatch.setattr(
        "data.clients._sec_filings",
        lambda ticker: [
            {
                "id": f"{ticker.upper()}-filing-1",
                "title": f"{ticker.upper()} annual filing",
                "snippet": f"{ticker.upper()} filing discusses demand, margins, and capital allocation.",
                "url": "https://example.com/filing",
            },
            {
                "id": f"{ticker.upper()}-filing-2",
                "title": f"{ticker.upper()} quarterly filing",
                "snippet": f"{ticker.upper()} filing highlights operating risks and regional exposure.",
                "url": "https://example.com/filing-2",
            },
        ],
    )
    monkeypatch.setattr(
        "data.clients._fmp_transcripts",
        lambda ticker, api_key: [
            {
                "id": f"{ticker.upper()}-transcript-1",
                "title": f"{ticker.upper()} earnings call",
                "snippet": f"Management commentary for {ticker.upper()} emphasized demand, pricing, and execution.",
            }
        ],
    )
    monkeypatch.setattr(
        "data.clients.FundamentalsClient.get_financials",
        lambda self, ticker: dict(
            LIVE_FUNDAMENTALS.get(
                ticker.upper(),
                {
                    "business_overview": f"{ticker.upper()} live business overview.",
                    "revenue_growth_yoy": 10.0,
                    "prior_revenue_growth_yoy": 8.0,
                    "gross_margin": 50.0,
                    "ebit_margin": 20.0,
                    "prior_ebit_margin": 18.0,
                    "fcf_margin": 12.0,
                    "cash_conversion": 90.0,
                    "cash_flow_commentary": "Cash generation is positive but still sensitive to working capital or capex timing.",
                    "earnings_surprise_pct": 0.0,
                    "management_change": "",
                    "regulatory_event": "",
                    "key_business_drivers": [
                        "Demand trends across Technology",
                        "Competitive position within Software",
                        "Management execution versus guidance",
                    ],
                    "risk_factors": {
                        "competition": "Competitive intensity could pressure pricing or market share.",
                        "regulation": "Policy changes may affect sentiment and operations.",
                        "execution": "Execution risk remains tied to guidance delivery, costs, and capital allocation.",
                    },
                    "source": "stubbed_live_data",
                },
            )
        ),
    )
