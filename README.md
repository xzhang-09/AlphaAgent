# AlphaAgent

AlphaAgent is a multi-agent equity research workflow for idea discovery, single-name diligence, valuation framing, and PM-style memo generation.

It is designed for buy-side research workflows rather than black-box prediction. The system pulls live market and fundamentals data where available, builds company and macro context, runs a critique loop, and produces a structured investment memo that a human analyst can review and refine.

## What It Does

Input: a live ticker such as `AAPL`, `MSFT`, `NVDA`, `TSM`, `0700.HK`, or `005930.KS`

Output: a research package with:

- multi-signal screening and why-now framing
- company fundamentals summary
- peer, sector, macro, FX, and regional context
- scenario-based valuation and sensitivity analysis
- structured risk framing and bear-case coverage
- PM-style memo with citations, critique, evaluator checks, and idea-log persistence

The current workflow is:

```text
Opportunity screen
  -> data ingestion
  -> signal detection
  -> fundamental analysis
  -> company / peer context
  -> macro / FX / regional context
  -> valuation framing
  -> risk synthesis
  -> memo draft
  -> critic loop
  -> evaluator checks
  -> final memo + idea log
```

## Architecture

### 1. Research Pipeline

The repo is organized around a sequential research graph:

```text
load_data
  -> signal_agent
  -> fundamental_agent
  -> context_agent
  -> macro_agent
  -> valuation_agent
  -> risk_agent
  -> memo_agent
  -> critic_agent
  -> evaluator
  -> finalize
```

Each stage writes into a shared research state and contributes a specific artifact to the final memo.

### 2. Agent Layer

The research layer is implemented as specialized agents:

- `SignalDetectionAgent`: event, valuation, fundamental, and market signal screening
- `FundamentalResearchAgent`: business overview, revenue / margin trends, cash flow quality, filing support
- `ContextAgent`: peer comparison, sector trend summary, competitive framing
- `MacroAgent`: rates, FX, regional context, currency sensitivity
- `ValuationAgent`: relative valuation, scenario analysis, sensitivity tables
- `RiskAgent`: competition, regulation, macro, execution, valuation compression
- `MemoAgent`: PM-style memo generation with analyst feedback integration
- `CriticAgent`: red-team style memo review and refinement routing

### 3. Evaluation Layer

Before finalizing output, the system runs evaluator checks for:

- numerical consistency between memo text and structured outputs
- thin citation coverage
- unsupported valuation references
- low-quality or incomplete memo framing

### 4. App Layer

The workflow is exposed through:

- `FastAPI` for programmatic execution
- `Streamlit` for interactive research, memo review, debug payloads, and memo regeneration with analyst feedback

## Core Capabilities

### Opportunity Discovery

The system can screen candidate names before deep research and explain why a name is interesting now, based on a composite signal score across:

- event signals
- valuation signals
- fundamental signals
- market signals

### Live-First Data With Fallbacks

AlphaAgent prefers live external data, but it is designed to degrade gracefully when a provider is unavailable or a key is missing.

Examples used in the UI and status panels:

- `FMP Stable`
- `Yahoo Fallback`
- `SEC Fallback`
- `Damodaran`

This makes it easier to see whether a memo is supported by premium-ish structured data, public filing fallbacks, or lighter live-source substitutes.

### Cross-Region Coverage

The workflow is built with Asia-Pacific support in mind, including:

- non-US ticker normalization such as `0700.HK` and `005930.KS`
- FX reference pairs and currency sensitivity
- regional context in the macro layer

### Human-in-the-Loop Memo Refinement

The Streamlit UI lets an analyst revise:

- bull case
- bear case
- catalysts
- notes

The memo can then be regenerated with explicit analyst feedback preserved in the research state and saved into the idea log.

## Data Sources

The project currently uses a mix of live APIs, public data, and local persistence.

### Structured Market and Company Data

- Yahoo Finance live quote and quote-summary endpoints
- Financial Modeling Prep
- FRED, where configured
- Damodaran industry benchmark data via `compdata`

### Unstructured Evidence

- SEC public filings
- transcript sources where available
- News API or Google News RSS fallback
- Asia / regional news context

### Local Persistence

- response cache under `storage/cache/`
- local retrieval payloads under `storage/vector_db/`
- exported artifacts under `storage/exports/`
- idea logs under `storage/ideas/`

## Repository Structure

```text
agents/       Specialized research agents
app/          Streamlit dashboard and UI components
config/       Environment loading and runtime settings
data/         External data clients and adapters
engine/       Memo formatting, valuation model, RAG processing
exports/      Export helpers
pipelines/    Opportunity screen, evaluator, research graph
schemas/      Typed research and memo schemas
storage/      Idea-log persistence and local runtime storage
tests/        Unit and workflow tests
utils/        LLM wrapper, ticker helpers, citations, source summaries
main.py       FastAPI entrypoint
```

## Quickstart

### Prerequisites

- Python 3.11+
- `pip` or a virtual environment tool of your choice

### Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

If your shell is `zsh`, keep the quotes around `'.[dev]'`.

### Environment Variables

Common variables for a full local run:

```bash
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-flash

FMP_API_KEY=
FRED_API_KEY=
EDGAR_USER_AGENT=
NEWS_API_KEY=
FILINGS_API_KEY=
TRANSCRIPT_API_KEY=
MARKET_DATA_API_KEY=

ENABLE_RESPONSE_CACHE=false
VECTOR_DB_PATH=./storage/vector_db
CACHE_DIR=./storage/cache
EXPORT_DIR=./storage/exports
IDEAS_DIR=./storage/ideas
```

Notes:

- `GEMINI_API_KEY` enables LLM memo and critic output
- `FMP_API_KEY` improves fundamentals and peer coverage
- `EDGAR_USER_AGENT` is recommended when using SEC fallbacks
- `VECTOR_DB_PATH` controls where the local retrieval store persists JSON payloads
- the app still runs with partial configuration, but some sections may fall back to lighter sources

## Running the Project

### FastAPI

```bash
uvicorn main:app --reload
```

Available endpoints include:

- `GET /health`
- `GET /research/examples`
- `POST /research/run`

### Streamlit Dashboard

```bash
streamlit run app/dashboard.py
```

The dashboard supports:

- running single-ticker research
- viewing signal, fundamental, context, macro, valuation, risk, memo, critique, and evaluation tabs
- source badges and data-availability summaries
- debug mode for raw JSON payloads
- memo regeneration with analyst feedback

## Testing

Run the full test suite:

```bash
pytest -q
```

The tests are designed to run hermetically with stubbed live data, so they should not depend on your local `.env` or external network responses.

## Example Tickers

- `AAPL`
- `MSFT`
- `NVDA`
- `TSM`
- `0700.HK`
- `005930.KS`
- `JPY=X`

## Current Design Choices

### Why Sequential Instead of Fully Parallel

The research graph is intentionally sequential right now. The shared research state is modeled as a single mutable record, which keeps the workflow simpler and easier to reason about while the agent outputs are still tightly coupled.

### Why Memo-First Instead of Trade Automation

This project is a research assistant. It is optimized for:

- evidence gathering
- structured reasoning
- valuation support
- PM-ready communication

It is not a broker integration, order-routing system, or automated execution stack.

## Limitations

- data quality depends on source availability and free-tier limits
- some providers require API keys for better coverage
- valuation output is framing support, not a complete institutional model
- memo quality improves materially when richer citation coverage is available

## Tech Stack

- Python 3.11+
- FastAPI
- Streamlit
- Pydantic
- pandas / numpy
- LangGraph-style orchestration
- OpenAI-compatible SDK usage for Gemini
- httpx
- yfinance

## License

This project is licensed under the MIT License.
