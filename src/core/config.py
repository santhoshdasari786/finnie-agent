from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]            # src/core/config.py -> project root
APP_CONFIG_PATH = PROJECT_ROOT / "src" / "config" / "app.yaml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")                 # a misspelled key fails loudly


class RouterCfg(_Strict):
    model: dict | None = None
    confidence_threshold: float = Field(0.6, ge=0, le=1)
    history_turns: int = Field(6, ge=0)

class MemoryCfg(_Strict):
    backend: Literal["memory", "sqlite"] = "memory"

class Timeouts(_Strict):
    llm: int = 30
    market: int = 10
    kite: int = 60

class WorkflowCfg(_Strict):
    router: RouterCfg = RouterCfg()
    memory: MemoryCfg = MemoryCfg()
    timeouts_seconds: Timeouts = Timeouts()

class MarketDataCfg(_Strict):
    providers: list[Literal["yfinance", "kite", "alpha_vantage"]] = ["yfinance", "kite"]
    cache_ttl_seconds: int = 1800
    default_exchange: str = "NSE"

class PortfolioCfg(_Strict):
    default_source: Literal["sample", "csv", "kite", "manual"] = "sample"
    sample_path: str = "./data/sample_portfolio.csv"

class AgentProfileCfg(_Strict):
    profile: str
    category: str | None = None

class McpCfg(_Strict):
    transport: Literal["stdio"] = "stdio"
    expose_tools: list[str] = []

class AppConfig(_Strict):
    workflow: WorkflowCfg = WorkflowCfg()
    market_data: MarketDataCfg = MarketDataCfg()
    portfolio: PortfolioCfg = PortfolioCfg()
    agents: dict[str, AgentProfileCfg] = {}
    mcp_server: McpCfg = McpCfg()


def load_app_config(path: Path = APP_CONFIG_PATH) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
