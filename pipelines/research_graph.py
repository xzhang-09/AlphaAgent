from __future__ import annotations

from typing import Callable

from agents.macro_agent import MacroAgent
from agents.context_agent import ContextAgent
from agents.critic_agent import CriticAgent
from agents.fundamental_agent import FundamentalResearchAgent
from agents.memo_agent import MemoAgent
from agents.risk_agent import RiskAgent
from agents.signal_agent import SignalDetectionAgent
from agents.valuation_agent import ValuationAgent
from config.settings import get_settings
from data.fx_data import FXDataAdapter
from data.fundamentals import FundamentalsAdapter
from data.market_data import MarketDataAdapter
from data.peer_data import PeerDataAdapter
from engine.memo_formatter import MemoFormatter
from engine.rag_processor import RAGProcessor
from pipelines.evaluator_pipeline import EvaluatorPipeline
from schemas.memo import AnalystFeedback
from schemas.research_state import ResearchState
from storage.idea_log import IdeaLogStore
from utils.citations import build_citations

try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover
    LANGGRAPH_AVAILABLE = False
    END = "__end__"

    class _CompiledGraph:
        def __init__(self, entry: str, nodes: dict, edges: dict, conditional_edges: dict) -> None:
            self.entry = entry
            self.nodes = nodes
            self.edges = edges
            self.conditional_edges = conditional_edges

        def invoke(self, state: dict, config: dict | None = None) -> dict:
            current = self.entry
            recursion_limit = int((config or {}).get("recursion_limit", 25))
            steps = 0
            while current != END:
                steps += 1
                if steps > recursion_limit:
                    raise RuntimeError(
                        f"Fallback graph recursion limit {recursion_limit} reached before hitting END."
                    )
                state = self.nodes[current](state)
                if current in self.conditional_edges:
                    router, mapping = self.conditional_edges[current]
                    current = mapping[router(state)]
                else:
                    next_nodes = self.edges[current]
                    current = next_nodes[0] if next_nodes else END
            return state

    class StateGraph:  # type: ignore[override]
        def __init__(self, _: type) -> None:
            self.nodes: dict[str, Callable[[dict], dict]] = {}
            self.edges: dict[str, list[str]] = {}
            self.conditional_edges: dict[str, tuple[Callable[[dict], str], dict[str, str]]] = {}
            self.entry = ""

        def add_node(self, name: str, fn: Callable[[dict], dict]) -> None:
            self.nodes[name] = fn

        def add_edge(self, source: str, target: str) -> None:
            self.edges.setdefault(source, []).append(target)

        def add_conditional_edges(self, source: str, router: Callable[[dict], str], mapping: dict[str, str]) -> None:
            self.conditional_edges[source] = (router, mapping)

        def set_entry_point(self, name: str) -> None:
            self.entry = name

        def compile(self) -> _CompiledGraph:
            return _CompiledGraph(self.entry, self.nodes, self.edges, self.conditional_edges)


class ResearchGraph:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.market_data = MarketDataAdapter()
        self.peer_data = PeerDataAdapter()
        self.fx_data = FXDataAdapter()
        self.fundamentals = FundamentalsAdapter()
        self.rag = RAGProcessor()
        self.signal_agent = SignalDetectionAgent()
        self.fundamental_agent = FundamentalResearchAgent()
        self.context_agent = ContextAgent()
        self.macro_agent = MacroAgent()
        self.valuation_agent = ValuationAgent()
        self.risk_agent = RiskAgent()
        self.memo_agent = MemoAgent()
        self.critic_agent = CriticAgent()
        self.evaluator = EvaluatorPipeline()
        self.memo_formatter = MemoFormatter()
        self.idea_log = IdeaLogStore()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ResearchState)
        graph.add_node("load_data", self._load_data)
        graph.add_node("signal_agent", self._signal_agent)
        graph.add_node("fundamental_agent", self._fundamental_agent)
        graph.add_node("context_agent", self._context_agent)
        graph.add_node("macro_agent", self._macro_agent)
        graph.add_node("valuation_agent", self._valuation_agent)
        graph.add_node("risk_agent", self._risk_agent)
        graph.add_node("memo_agent", self._memo_agent)
        graph.add_node("critic_agent", self._critic_agent)
        graph.add_node("evaluator", self._evaluator)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("load_data")
        # Keep the graph sequential for now. LangGraph parallel fan-out requires
        # annotated merge semantics, and our shared state object is intentionally
        # modeled as a single mutable research record.
        graph.add_edge("load_data", "signal_agent")
        graph.add_edge("signal_agent", "fundamental_agent")
        graph.add_edge("fundamental_agent", "context_agent")
        graph.add_edge("context_agent", "macro_agent")
        graph.add_edge("macro_agent", "valuation_agent")
        graph.add_edge("valuation_agent", "risk_agent")
        graph.add_edge("risk_agent", "memo_agent")
        graph.add_edge("memo_agent", "critic_agent")
        graph.add_conditional_edges(
            "critic_agent",
            self._route_after_critic,
            {
                "refine_context": "context_agent",
                "refine_macro": "macro_agent",
                "refine_fundamental": "fundamental_agent",
                "refine_risk": "risk_agent",
                "rerun_memo": "memo_agent",
                "done": "evaluator",
            },
        )
        graph.add_edge("evaluator", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def run(self, ticker: str, analyst_feedback: dict[str, str] | None = None) -> ResearchState:
        initial_state = ResearchState(
            ticker=ticker.upper(),
            analyst_feedback=AnalystFeedback(**(analyst_feedback or {})),
            refinement_count=0,
            max_refinements=2,
            status_log=[],
        )
        return self.graph.invoke(initial_state, config={"recursion_limit": 50})

    def _load_data(self, state: ResearchState) -> ResearchState:
        ticker = state["ticker"]
        rag_context = self.rag.build_context(ticker)
        market_snapshot = self.market_data.get_market_snapshot(ticker)
        peer_snapshot = self.peer_data.get_peer_snapshot(ticker)
        live_peer_forward_pes = [
            float(row["forward_pe"])
            for row in peer_snapshot
            if row.get("ticker") != "INDUSTRY_MEDIAN" and row.get("forward_pe") is not None
        ]
        benchmark_peer_forward_pes = [
            float(row["forward_pe"])
            for row in peer_snapshot
            if row.get("ticker") == "INDUSTRY_MEDIAN" and row.get("forward_pe") is not None
        ]
        live_peer_ev_ebitda = [
            float(row["ev_ebitda"])
            for row in peer_snapshot
            if row.get("ticker") != "INDUSTRY_MEDIAN" and row.get("ev_ebitda") is not None
        ]
        benchmark_peer_ev_ebitda = [
            float(row["ev_ebitda"])
            for row in peer_snapshot
            if row.get("ticker") == "INDUSTRY_MEDIAN" and row.get("ev_ebitda") is not None
        ]
        if live_peer_forward_pes:
            market_snapshot["peer_forward_pe"] = round(sum(live_peer_forward_pes) / len(live_peer_forward_pes), 2)
        elif benchmark_peer_forward_pes:
            market_snapshot["peer_forward_pe"] = round(
                sum(benchmark_peer_forward_pes) / len(benchmark_peer_forward_pes),
                2,
            )
        if not market_snapshot.get("ev_ebitda"):
            if live_peer_ev_ebitda:
                market_snapshot["ev_ebitda"] = round(sum(live_peer_ev_ebitda) / len(live_peer_ev_ebitda), 2)
            elif benchmark_peer_ev_ebitda:
                market_snapshot["ev_ebitda"] = round(
                    sum(benchmark_peer_ev_ebitda) / len(benchmark_peer_ev_ebitda),
                    2,
                )
        state.update(
            {
                "company_profile": self.market_data.get_company_profile(ticker),
                "market_snapshot": market_snapshot,
                "fundamentals_snapshot": self.fundamentals.get_fundamentals_snapshot(ticker),
                "peer_snapshot": peer_snapshot,
                "macro_snapshot": self.market_data.get_macro_snapshot(ticker),
                "fx_snapshot": self.fx_data.get_fx_snapshot(ticker),
                "rag_context": rag_context,
                "citations": build_citations(rag_context),
            }
        )
        state["status_log"].append("load_data complete")
        return state

    def _signal_agent(self, state: ResearchState) -> ResearchState:
        state = self.signal_agent.run(state)
        state["status_log"].append("signal_agent complete")
        return state

    def _fundamental_agent(self, state: ResearchState) -> ResearchState:
        state = self.fundamental_agent.run(state)
        state["status_log"].append("fundamental_agent complete")
        return state

    def _context_agent(self, state: ResearchState) -> ResearchState:
        state = self.context_agent.run(state)
        state["status_log"].append("context_agent complete")
        return state

    def _macro_agent(self, state: ResearchState) -> ResearchState:
        state = self.macro_agent.run(state)
        state["status_log"].append("macro_agent complete")
        return state

    def _valuation_agent(self, state: ResearchState) -> ResearchState:
        state = self.valuation_agent.run(state)
        state["status_log"].append("valuation_agent complete")
        return state

    def _risk_agent(self, state: ResearchState) -> ResearchState:
        state = self.risk_agent.run(state)
        state["status_log"].append("risk_agent complete")
        return state

    def _memo_agent(self, state: ResearchState) -> ResearchState:
        state = self.memo_agent.run(state)
        state["status_log"].append("memo_agent complete")
        return state

    def _critic_agent(self, state: ResearchState) -> ResearchState:
        state = self.critic_agent.run(state)
        if state["critic_output"]["needs_refinement"]:
            state["refinement_count"] += 1
            state["status_log"].append(
                f"critic_agent refinement: {state['critic_output']['refinement_target']}"
            )
        else:
            state["status_log"].append("critic_agent complete")
        return state

    def _evaluator(self, state: ResearchState) -> ResearchState:
        state["evaluator_output"] = self.evaluator.run(state)
        state["status_log"].append("evaluator complete")
        return state

    def _finalize(self, state: ResearchState) -> ResearchState:
        final_memo_markdown = self.memo_formatter.render_markdown(state["memo_output"])
        idea_log_path = self.idea_log.save_run(state)
        state["final_output"] = {
            "title": state["memo_output"]["title"],
            "final_memo_markdown": final_memo_markdown,
            "passed_evaluator": state["evaluator_output"]["passed"],
            "citation_count": len(state["citations"]),
            "idea_log_path": str(idea_log_path),
        }
        state["status_log"].append("finalize complete")
        return state

    @staticmethod
    def _route_after_critic(state: ResearchState) -> str:
        critic = state["critic_output"]
        if not critic["needs_refinement"]:
            return "done"
        target = critic["refinement_target"]
        if target == "context_agent":
            return "refine_context"
        if target == "macro_agent":
            return "refine_macro"
        if target == "fundamental_agent":
            return "refine_fundamental"
        if target == "memo_agent":
            return "rerun_memo"
        return "refine_risk"


def run_research(ticker: str, analyst_feedback: dict[str, str] | None = None) -> ResearchState:
    return ResearchGraph().run(ticker=ticker, analyst_feedback=analyst_feedback)
