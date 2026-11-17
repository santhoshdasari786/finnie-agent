from src.core.llm import LLMFactory
from src.workflow.memory import ConversationMemory, LLMRewriter
from src.agents.tax_education_agent import TaxEducationAgent
from src.rag.bootstrap import build_rag
from src.data.portfolio.store import ConnectionStore
from src.agents.portfolio_analysis_agent import PortfolioAnalysisAgent
from src.agents.finance_qa_agent import FinanceQAAgent
from src.common.models import QASettings
from src.core.guardrails import Guardrails
from src.workflow.graph import build_graph
from src.workflow.state import AGENT_NAMES

from src.agents.market_analysis_agent import MarketAnalysisAgent
from src.core.config import load_app_config
from src.data.market.base import PROVIDERS
from src.data.market.cache import build_market_provider
import src.data.market.yfinance_provider  # noqa: F401  (importing registers "yfinance")
import src.data.portfolio.sample  # noqa: F401  (importing registers "sample" in the portfolio SOURCES registry)
import src.data.portfolio.kite  # noqa: F401  (importing registers "kite" in the portfolio SOURCES registry)
from src.workflow.classifier import LLMClassifier
from src.agents.goal_planning_agent import GoalExtractor, GoalPlanningAgent
from src.agents.news_synthesizer_agent import NewsSynthesizerAgent
from src.data.news.base import NEWS_PROVIDERS
import src.data.news.google_news  # noqa: F401  (importing registers "google_news")
from src.workflow.runtime import Runtime


class _Pending:
    """Placeholder for an agent that isn't built yet, so the graph is always complete."""
    ready = False
    def __init__(self, name):
        self.name = name

    async def run(self, query, ctx=None):
        from src.core.contracts import AgentResult
        return AgentResult(agent=self.name, status="error", disclaimer="Not financial advice.",
                           text=f"The {self.name} agent isn't available yet.")


def build_agents(store: ConnectionStore | None = None) -> dict:
    agents = {n: _Pending(n) for n in AGENT_NAMES}
    provider = build_market_provider(PROVIDERS["yfinance"](), load_app_config().market_data)    # cache, retry, stale fallback
    rag = build_rag()      # build the embedder and Chroma store ONCE; both agents share them
    shared = dict(retriever=rag.retriever, glossary=rag.glossary, settings=rag.settings)
    agents["finance_qa"] = FinanceQAAgent(**shared)
    agents["tax_education"] = TaxEducationAgent(**shared)

    agents["market_analysis"] = MarketAnalysisAgent(provider)
    agents["portfolio"] = PortfolioAnalysisAgent(store or ConnectionStore(), provider)

    agents["goal_planning"] = GoalPlanningAgent(GoalExtractor(LLMFactory.get_default()))
    agents["news_synthesizer"] = NewsSynthesizerAgent(NEWS_PROVIDERS["google_news"]())


    return agents

# def build_app(settings: QASettings | None = None, store: ConnectionStore | None = None):
#     s = settings or QASettings()
#     return build_graph(build_agents(store), Guardrails(s), s)

# def build_app(settings: QASettings | None = None, store: ConnectionStore | None = None,
#               memory: ConversationMemory | None = None):
#     s = settings or QASettings()
#     llm = LLMFactory.get_default()
#     memory = memory or ConversationMemory(rewriter=LLMRewriter(llm))
#     return build_graph(build_agents(store), Guardrails(s), s, memory, LLMClassifier(llm))


def build_runtime(settings: QASettings | None = None, store: ConnectionStore | None = None,
                  memory: ConversationMemory | None = None) -> Runtime:
    """Everything one running app needs. The API uses this; the CLI only wants the graph (build_app)."""
    s = settings or QASettings()
    store = store or ConnectionStore()
    llm = LLMFactory.get_default()
    memory = memory or ConversationMemory(rewriter=LLMRewriter(llm))
    agents = build_agents(store)
    graph = build_graph(agents, Guardrails(s), s, memory, LLMClassifier(llm))
    return Runtime(graph=graph, agents=agents, store=store, memory=memory)


def build_app(settings: QASettings | None = None, store: ConnectionStore | None = None,
              memory: ConversationMemory | None = None):
    return build_runtime(settings, store, memory).graph


