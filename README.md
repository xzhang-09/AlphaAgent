# AlphaAgent

AlphaAgent is a multi-agent AI investment research and decision-support platform designed to support buy-side fundamental equities workflows, from idea discovery to PM-ready memo generation.

## What It Does

AlphaAgent runs a research workflow designed to support how an analyst or PM would investigate a stock idea:

`data ingestion -> multi-signal screening -> deep single-name research -> valuation and risk framing -> memo draft -> critique loop -> evaluator checks -> final memo`

At a high level, the system:

- screens for candidate ideas using event, valuation, fundamental, and market signals
- retrieves structured and unstructured evidence from market data, fundamentals, filings, transcripts, and news
- builds company, peer, macro, FX, and Asia-Pacific context
- produces a structured investment memo with bull case, bear case, catalysts, and valuation framing
- runs a critic and evaluator step before finalizing the memo
- lets a human analyst revise bull case, bear case, and catalysts in the UI

## Why It Matters

This project is intentionally not a black-box stock prediction tool and does not execute trades.

It matters because buy-side investing is usually constrained by workflow quality, evidence coverage, and memo discipline rather than by a single “prediction model.” AlphaAgent is designed to help analysts move faster on idea triage, build more structured investment cases, and pressure-test conclusions before they reach a PM or IC discussion.

The system is also built with Asia-Pacific awareness in mind, including regional context, FX considerations, and support for non-US ticker formats such as `0700.HK` and `005930.KS`.

## System Architecture

AlphaAgent is organized into four main layers:

- **Data layer**
  Retrieves live market data, fundamentals, filings, transcripts, news, and regional context. It uses Yahoo Finance, Financial Modeling Prep, SEC public filings, and News/Google News sources where available.
- **Research agent layer**
  Includes signal, fundamental, context, macro, valuation, risk, memo, and critic agents.
- **Orchestration and evaluation layer**
  Uses LangGraph-style workflow orchestration, a critique/refinement loop, and evaluator checks for numerical consistency and citation coverage.
- **Application layer**
  Exposes the workflow through a Streamlit dashboard with progress tracking, tabbed outputs, analyst feedback, memo regeneration, and idea-log persistence.

## Key Features

- Multi-signal opportunity discovery before deep single-name research
- RAG over filings, earnings transcripts, news, and Asia regional context
- Separate company context and macro / FX / regional context via dedicated agents
- Relative valuation, scenario analysis, sensitivity tables, and structured bear cases
- Critique / red-team loop before final memo delivery
- Human-in-the-loop feedback, memo regeneration, PDF export, and idea-log persistence
- Environment-driven config, local cache, vector store persistence, and research artifact storage
- Live-first data flow with explicit fallback labeling such as `FMP Stable`, `Yahoo Fallback`, and `SEC Fallback`

## Example Output

For a live ticker such as `AAPL`, `MSFT`, `TSM`, or `0700.HK`, the dashboard can produce:

- a ranked opportunity screen with signal explanations
- a fundamental summary with revenue, margin, and cash flow commentary
- peer, sector, macro, and FX context
- scenario-based valuation and a bear-case breakdown
- a PM-style memo with why now, key drivers, valuation, catalysts, risks, and conclusion

Example memo structure:

- Company / ticker / sector
- Why now
- Key drivers
- Sector and macro context
- Fundamental analysis
- Valuation analysis
- Bull case
- Bear case
- Catalysts
- Risks
- Conclusion

## Tech Stack

- **Language / app framework**
  Python 3.11+ , FastAPI, Streamlit
- **Agent orchestration**
  LangGraph
- **LLM**
  Gemini via the OpenAI-compatible SDK interface
- **Market and fundamentals**
  Yahoo Finance live endpoints, Financial Modeling Prep
- **Unstructured data / RAG**
  SEC public filings, transcript APIs where available, News API or Google News RSS, local vector store
- **Core libraries**
  pandas, numpy, pydantic, httpx

## Quickstart

Create an environment and install dependencies:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version
pip install -e '.[dev]'
```

If `python3` points to 3.10 on your machine, use a newer interpreter to avoid slow dependency resolution and compatibility issues. The quoted install command avoids `zsh: no matches found: .[dev]`.

Copy environment variables before wiring real services:

```bash
cp .env.example .env
```

Recommended environment variables for a full live run:

```bash
GEMINI_API_KEY=
FMP_API_KEY=
NEWS_API_KEY=
TRANSCRIPT_API_KEY=
FILINGS_API_KEY=
```

Gemini is configured through the OpenAI SDK compatibility endpoint documented by Google:
[OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)

Run the app:

```bash
uvicorn main:app --reload
streamlit run app/dashboard.py
```

Run tests:

```bash
pytest
```

Example tickers you can try in the UI:

- `AAPL`
- `MSFT`
- `NVDA`
- `TSM`
- `0700.HK`
- `005930.KS`

## Storage

- `storage/cache/`: cached API responses
- `storage/vector_db/`: persisted local vector-store payloads
- `storage/exports/`: exported memo artifacts
- `storage/ideas/`: structured idea-log records for each research run
