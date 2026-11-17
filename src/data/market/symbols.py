import re
from src.data.market.models import Instrument

_INDEX_RULES = [(re.compile(r"\bnifty(?:\s?50)?\b", re.I), "NIFTY50"),
                (re.compile(r"\bsensex\b", re.I), "SENSEX")]
_TICKER = re.compile(r"\b[A-Z]{2,}\b")
_NOT_TICKERS = frozenset({"NIFTY", "SENSEX", "ITR", "LTCG", "STCG", "SIP", "EMI", "RBI",
                          "NSE", "BSE", "ETF", "IPO", "USD", "INR", "FD", "PPF", "NPS"})

def extract_instruments(text: str) -> list[Instrument]:
    found: dict[Instrument, None] = {}
    for rule, symbol in _INDEX_RULES:
        if rule.search(text):
            found[Instrument(symbol=symbol, exchange="INDEX")] = None
    for sym in _TICKER.findall(text):
        if sym not in _NOT_TICKERS:
            found[Instrument(symbol=sym)] = None
    return list(found)
