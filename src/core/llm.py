from pathlib import Path
import yaml
from langchain_core.language_models import BaseChatModel

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


class LLMFactory:
    """Builds LangChain chat models from config.yaml. get_default() caches
    one instance per process so every agent reuses the same LLM object."""

    _default_instance: BaseChatModel | None = None

    @classmethod
    def get_default(cls) -> BaseChatModel:
        if cls._default_instance is None:
            cls._default_instance = cls._build(cls._load_config())
        return cls._default_instance

    @classmethod
    def build(cls, provider: str, model: str, temperature: float = 0.2) -> BaseChatModel:
        """Explicit override, bypassing config.yaml — e.g. for tests or a one-off agent."""
        return cls._build({"provider": provider, "model": model, "temperature": temperature})

    @staticmethod
    def _load_config() -> dict:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("llm", {})

    @staticmethod
    def _build(cfg: dict) -> BaseChatModel:
        provider = cfg.get("provider", "google")
        model = cfg.get("model", "gemini-3.5-flash-lite")
        temperature = cfg.get("temperature")

        kwargs = {"model": model}
        if temperature is not None:
            kwargs["temperature"] = temperature

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(**kwargs)
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(**kwargs)
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(**kwargs)

        raise ValueError(f"Unknown LLM provider: {provider!r}")
