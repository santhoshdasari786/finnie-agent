import pytest
from pydantic import ValidationError

from src.core.config import AppConfig, load_app_config


def test_real_app_yaml_loads_with_expected_values():
    cfg = load_app_config()
    assert cfg.market_data.providers == ["yfinance", "kite"]
    assert cfg.workflow.router.confidence_threshold == 0.6
    assert cfg.agents["tax_education"].category == "costs-taxes"
    assert "place_order" not in cfg.mcp_server.expose_tools


@pytest.mark.parametrize(
    "bad",
    [
        {"workfow": {}},                                          # misspelled top-level key
        {"market_data": {"cache_ttl": 10}},                       # misspelled nested key
        {"market_data": {"providers": ["yahoo"]}},                # not in the Literal
        {"workflow": {"router": {"confidence_threshold": 3}}},    # above le=1
        {"workflow": {"memory": {"backend": "redis"}}},           # not in the Literal
        {"agents": {"finance_qa": {}}},                           # profile is required
    ],
    ids=["top-key-typo", "nested-key-typo", "bad-provider", "threshold-range", "bad-backend", "missing-profile"],
)
def test_bad_config_is_rejected(bad):
    with pytest.raises(ValidationError):
        AppConfig.model_validate(bad)


def test_empty_config_falls_back_to_defaults():
    cfg = AppConfig.model_validate({})
    assert cfg.market_data.providers == ["yfinance", "kite"]
    assert cfg.portfolio.default_source == "sample"
