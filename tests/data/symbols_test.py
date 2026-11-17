"""Pulling instruments out of free text (deterministic, no network).

Run:  .venv/bin/python -m pytest tests/data/symbols_test.py -v
"""
import pytest

from src.data.market.models import Instrument
from src.data.market.symbols import extract_instruments

NIFTY = Instrument(symbol="NIFTY50", exchange="INDEX")
SENSEX = Instrument(symbol="SENSEX", exchange="INDEX")

@pytest.mark.parametrize("text", ["Nifty close today", "nifty", "NIFTY 50 level", "nifty50 price", "Nifty 50"])
def test_nifty_in_any_case_or_spacing(text):
    assert extract_instruments(text) == [NIFTY]

def test_sensex():
    assert extract_instruments("where is the sensex") == [SENSEX]

def test_uppercase_tickers_are_nse_stocks():
    assert extract_instruments("RELIANCE and TCS price") == [Instrument(symbol="RELIANCE"), Instrument(symbol="TCS")]

def test_indexes_and_stocks_mix_indexes_first():
    assert extract_instruments("TCS vs Nifty") == [NIFTY, Instrument(symbol="TCS")]

def test_duplicates_collapse_keeping_first_seen_order():
    got = extract_instruments("TCS INFY TCS nifty NIFTY")
    assert got == [NIFTY, Instrument(symbol="TCS"), Instrument(symbol="INFY")]

@pytest.mark.parametrize("text", ["What is a SIP?", "How is the NSE doing", "RBI and ITR and LTCG", "ETF IPO FD PPF NPS",
                                  "reliance share price", "", "   "])
def test_nothing_instrument_like_gives_empty(text):
    assert extract_instruments(text) == []

def test_nifty_and_sensex_words_are_not_also_stock_tickers():
    assert extract_instruments("NIFTY SENSEX") == [NIFTY, SENSEX]
