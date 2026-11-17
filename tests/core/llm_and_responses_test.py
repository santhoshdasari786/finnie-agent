"""The LLM factory (config -> chat model, cached default) and the response normaliser.

Run:  .venv/bin/python -m pytest tests/core/llm_and_responses_test.py -v
No network and no keys: the provider classes are replaced by recorders.

Contract
  LLMFactory      provider and model come from config.yaml; temperature is passed only when set (some models reject it);
                  an unknown provider is an error; get_default() builds once per process
  AgentResponse   a model's reply may be a string or a list of content parts; either way the user gets clean text
"""
import sys
import types

import pytest

from src.core.llm import CONFIG_PATH, LLMFactory
from src.core.responses import AgentResponse


class Recorder:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def providers(monkeypatch):
    """Stand-ins for the three LangChain provider packages, imported lazily by the factory."""
    for module, cls in (("langchain_google_genai", "ChatGoogleGenerativeAI"), ("langchain_openai", "ChatOpenAI"),
                        ("langchain_anthropic", "ChatAnthropic")):
        fake = types.ModuleType(module)
        setattr(fake, cls, type(cls, (Recorder,), {}))
        monkeypatch.setitem(sys.modules, module, fake)
    monkeypatch.setattr(LLMFactory, "_default_instance", None)


# ================================================================ the factory
@pytest.mark.parametrize("provider, cls", [("google", "ChatGoogleGenerativeAI"), ("openai", "ChatOpenAI"), ("anthropic", "ChatAnthropic")])
def test_each_provider_builds_its_own_chat_model(providers, provider, cls):
    llm = LLMFactory.build(provider, "some-model", temperature=0.3)
    assert type(llm).__name__ == cls and llm.kwargs == {"model": "some-model", "temperature": 0.3}


def test_an_unknown_provider_is_refused():
    with pytest.raises(ValueError, match="Unknown LLM provider: 'martian'"):
        LLMFactory._build({"provider": "martian", "model": "x"})


def test_temperature_is_left_out_when_not_configured(providers):
    llm = LLMFactory._build({"provider": "google", "model": "flash-lite"})
    assert llm.kwargs == {"model": "flash-lite"}                # some models ignore or reject a temperature


def test_a_temperature_of_zero_is_still_passed(providers):
    assert LLMFactory._build({"provider": "openai", "model": "m", "temperature": 0}).kwargs["temperature"] == 0


def test_an_empty_config_falls_back_to_google_and_a_default_model(providers):
    llm = LLMFactory._build({})
    assert type(llm).__name__ == "ChatGoogleGenerativeAI" and llm.kwargs["model"]


def test_the_default_is_built_from_config_yaml_once_and_reused(providers, monkeypatch):
    monkeypatch.setattr(LLMFactory, "_load_config", staticmethod(lambda: {"provider": "anthropic", "model": "claude-x"}))
    first = LLMFactory.get_default()
    assert type(first).__name__ == "ChatAnthropic" and first.kwargs["model"] == "claude-x"
    monkeypatch.setattr(LLMFactory, "_load_config", staticmethod(lambda: {"provider": "openai", "model": "other"}))
    assert LLMFactory.get_default() is first                    # cached: one client for every agent


def test_the_real_config_file_loads_and_names_a_provider():
    cfg = LLMFactory._load_config()
    assert CONFIG_PATH.name == "config.yaml" and cfg["provider"] in {"google", "openai", "anthropic"} and cfg["model"]


def test_an_empty_config_file_is_an_empty_llm_section(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("", encoding="utf-8")
    monkeypatch.setattr("src.core.llm.CONFIG_PATH", tmp_path / "config.yaml")
    assert LLMFactory._load_config() == {}


# ================================================================ responses
class Msg:
    def __init__(self, content):
        self.content = content


def test_a_plain_string_is_stripped():
    r = AgentResponse.from_message(Msg("  hello there \n"))
    assert r.text == "hello there" and str(r) == "hello there" and r.raw == "  hello there \n"


def test_a_list_of_parts_is_joined_and_only_text_parts_count():
    parts = [{"type": "text", "text": "First."}, {"type": "thinking", "text": "hidden reasoning"}, {"type": "text", "text": "Second."}]
    assert AgentResponse.from_message(Msg(parts)).text == "First.\nSecond."


def test_plain_strings_inside_a_list_are_kept():
    assert AgentResponse.from_message(Msg(["one", {"type": "text", "text": "two"}, 3])).text == "one\ntwo\n3"


def test_empty_parts_are_dropped():
    assert AgentResponse.from_message(Msg([{"type": "text", "text": ""}, {"type": "text", "text": "x"}])).text == "x"


def test_a_dict_part_without_text_is_just_empty():
    assert AgentResponse.from_message(Msg([{"type": "text"}])).text == ""


def test_anything_else_is_turned_into_text():
    assert AgentResponse.from_message(Msg(42)).text == "42"


def test_print_renders_markdown_when_rich_is_available(capsys):
    AgentResponse.from_message(Msg("**bold** words")).print()
    assert "bold" in capsys.readouterr().out


def test_print_falls_back_to_plain_text_without_rich(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rich.console", None)       # makes `from rich.console import Console` raise ImportError
    AgentResponse.from_message(Msg("plain words")).print()
    assert capsys.readouterr().out.strip() == "plain words"
