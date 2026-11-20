"""Tier 1 of the router: deterministic rules. Free, instant, unit-testable.

Contract: route_by_rules(text) -> RoutingDecision | None
  None  = no rule fired; the caller tries the LLM classifier, then falls back to concept_qa.
  Rules favour PRECISION over recall: a rule that wrongly fires sends the user to the wrong agent with
  high confidence, while a rule that misses only defers to the next tier.
"""
import difflib
import re

from src.workflow.state import Intent, RoutingDecision

_I = re.IGNORECASE


def _rule(intent: Intent, pattern: str) -> tuple[Intent, re.Pattern]:
    return intent, re.compile(pattern, _I)


# ORDER IS PRIORITY: the first rule that fires is the intent, the others become secondary_intents.
#   goal > portfolio > tax > market > news
#   "Can I retire at 50 with my portfolio?" is a goal question that uses the portfolio as data;
#   "capital gains tax if I sell Reliance" is tax even though it names a stock.
_RULES: list[tuple[Intent, re.Pattern]] = [
    _rule("goal", r"\bcan i (reach|retire|afford)\b"
                  r"|\bhow much (do i need to|should i) save\b"
                  r"|\bhow much sip\b|\bwhat sip (amount|should|do i)\b"
                  r"|\bhow much (do i need to|should i|must i) (invest|save)\b.*\b(month|monthly|sip)\b"
                  r"|\bhow (long|many years)\b.*\b(to|until|before)\b.*\b(reach|get to|have|become|hit)\b"
                  r"|\bif i (invest|save|put|add|deposit)\b.*\b(per month|a month|monthly|every month|each month)\b"
                  r"|\bretire (at|by|in)\b"
                  r"|\bplan a goal\b|\bmy (financial )?goal\b|\bsave for\b"
                  r"|\bstart (over|again)\b|\bnew goal\b|\bforget (my|the) (numbers|goal|details)\b"
                  r"|\bassum(e|ing)\b.*\d\s*(%|percent)"),



    _rule("portfolio", r"\bmy (portfolio|holdings|positions)\b"
                       r"|\b(?:dis)?connect\b.*\b(portfolio|sample|kite|zerodha|csv|manual)\b"),
    _rule("tax", r"\b(tax|taxed|taxation|capital gains?|ltcg|stcg|80c|itr)\b"),
    _rule("market",
          # an index name only counts together with a live-data word (close, today, ...);
          # bare "Nifty" is usually a concept question
          r"\b(nifty|sensex)\b.*\b(close|closing|trading|today|yesterday)\b"
          r"|\b(close|closing)\b.*\b(nifty|sensex)\b"
          r"|\bshare price\b|\bstock price\b|\bquote (for|of)\b|\btrading (at|today)\b"
          # (?-i:...) turns IGNORECASE off just here: "price of" must be followed by an UPPERCASE ticker
                    r"|\bprice of (?-i:[A-Z]{2,})\b"
          # a quote-shaped word next to an index name
          r"|\b(nifty|sensex)\b.*\b(price|level|points|quote|doing)\b"
          r"|\b(price|level|quote)\b.*\b(nifty|sensex)\b"
          # a quote word next to a real ticker; the (?!...) lookahead rejects acronyms that aren't instruments
          r"|(?-i:\b(?!(?:ETF|SIP|EMI|RBI|ITR|LTCG|STCG|IPO|FD|PPF|NPS|NSE|BSE|USD|INR)\b)[A-Z]{2,}\b).*\b(price|quote)\b"
          r"|\b(price|quote)\b.*(?-i:\b(?!(?:ETF|SIP|EMI|RBI|ITR|LTCG|STCG|IPO|FD|PPF|NPS|NSE|BSE|USD|INR)\b)[A-Z]{2,}\b)"),

    _rule("news", r"\bnews (on|about|for)\b|\blatest news\b|\bheadlines\b"),
        # lowest priority: "I'm aggressive, can I retire at 50?" is a goal question that also states a preference
    _rule("profile", r"\b(i am|i'm|im)\s+(an?\s+)?(conservative|moderate|aggressive)(\s+(investor|saver|risk[- ]taker))?\s*[.!]?$"
                     r"|\bmy risk (appetite|tolerance) is (conservative|moderate|aggressive)\b"
                     r"|\bset my risk (appetite|tolerance)?\s*(to )?(conservative|moderate|aggressive)\b"
                     r"|^\s*(use |try |make it |make me |go with |set it to |switch to |change it to )?(an? )?"
                     r"(conservative|moderate|aggressive)( one| risk| investor)?\s*[.!?]?\s*$"),
    _rule("news", r"\bnews (on|about|for)\b|\blatest news\b|\bheadlines\b"
                  r"|\bany news\b|\bnews today\b|\bwhat'?s (the )?(latest )?news\b"),


]

_TICKER = re.compile(r"\b[A-Z]{2,}\b")                                    # case-sensitive on purpose
_NOT_TICKERS = frozenset({"ITR", "LTCG", "STCG", "SIP", "EMI", "RBI"})    # all-caps, but not instruments

CONFIDENCE_SINGLE = 0.95       # one rule fired
CONFIDENCE_CONFLICT = 0.75     # several rules fired: probably right, less sure


def _symbols(text: str) -> list[str]:
    found = (s for s in _TICKER.findall(text) if s not in _NOT_TICKERS)
    return list(dict.fromkeys(found))              # de-duplicate, keep first-seen order


_WORD = re.compile(r"[A-Za-z]{7,12}")
_PORTFOLIO_SIMILARITY = 0.85          # "portifolio", "portfolo", "porfolio" pass; "portion" (0.75) and "portrait" do not


def _fix_portfolio_typos(text: str) -> str:
    """People misspell "portfolio" and the rules then miss it ("using my portifolio" ran as a plain goal question).
    Only a word that is very close to it is changed, and only to that one word, so nothing else is rewritten."""
    def fix(m: re.Match) -> str:
        w = m.group(0)
        close = w.lower() != "portfolio" and not w.lower().startswith("portfolios") and \
            difflib.SequenceMatcher(None, w.lower(), "portfolio").ratio() >= _PORTFOLIO_SIMILARITY
        return "portfolio" if close else w
    return _WORD.sub(fix, text)


def route_by_rules(text: str | None) -> RoutingDecision | None:
    normalized = _fix_portfolio_typos(" ".join((text or "").split()))     # collapse spaces and newlines
    if not normalized.strip("?!. "):
        return None                                 # empty or punctuation only: no opinion

    hits = [intent for intent, rule in _RULES if rule.search(normalized)]
    if not hits:
        return None

    return RoutingDecision(
        intent=hits[0],
        confidence=CONFIDENCE_SINGLE if len(hits) == 1 else CONFIDENCE_CONFLICT,
        source="rules",
        normalized_question=normalized,
        secondary_intents=hits[1:],
        symbols=_symbols(normalized) if "market" in hits else [],
    )
