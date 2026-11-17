"""Rules router (tier 1 of 3): deterministic, free, no LLM, no graph.

Run:  .venv/bin/python -m pytest tests/workflow/router_rules_test.py -v

Contract of route_by_rules(text) -> RoutingDecision | None
  * returns None when NO rule fires (the caller then tries the LLM classifier, then falls back to concept_qa)
  * when several rules fire, the highest-priority intent wins and the others are listed in secondary_intents
  * decision.source == "rules"; confidence is high for a single match, lower when rules disagree
"""
import pytest

from src.workflow.router import route_by_rules


def intent_of(text):
    d = route_by_rules(text)
    return d.intent if d else None


# ---------------------------------------------------------------- the 10 graded questions
GRADED = [
    ("What is compound interest?", None),
    ("What is an expense ratio?", None),
    ("What does diversification mean?", None),
    ("What's the difference between nominal and real returns?", None),
    ("Why do bond prices fall when interest rates go up?", None),
    ("How do I read a mutual fund factsheet? What should I look at first?", None),
    ("Should I invest in just one mutual fund or spread my money across several?", None),
    ("How are long-term capital gains on equity mutual funds taxed in India right now?", "tax"),
    ("I'm 28, I lost my job and can't pay my credit card EMI. Should I stop my SIP and move everything into gold?", None),
    ("What was the Nifty 50 closing value yesterday, and should I buy today?", "market"),
]

@pytest.mark.parametrize("text,expected", GRADED, ids=[f"graded{i+1}" for i in range(10)])
def test_graded_questions(text, expected):
    # None = no rule fires: the pipeline falls back to concept_qa, which is the right answer for these
    assert intent_of(text) == expected


# ---------------------------------------------------------------- one table per intent
@pytest.mark.parametrize("text", [
    "Analyze my portfolio", "How are my holdings doing?", "Show my positions", "What is my portfolio's risk?",
])
def test_portfolio(text):
    assert intent_of(text) == "portfolio"

@pytest.mark.parametrize("text", [
    "What is the share price of Reliance?", "Quote for TCS", "Where is the Sensex trading today?",
    "Nifty close yesterday", "What is the stock price of Infosys",
])
def test_market(text):
    assert intent_of(text) == "market"

@pytest.mark.parametrize("text", [
    "How is capital gains tax calculated?", "What is the 80C limit?", "How do I file my ITR?", "Explain LTCG vs STCG",
])
def test_tax(text):
    assert intent_of(text) == "tax"

@pytest.mark.parametrize("text", [
    "Can I reach 50 lakh in 10 years saving 20000 a month?", "How much do I need to save to retire at 50?",
    "Help me plan a goal to buy a house",
])
def test_goal(text):
    assert intent_of(text) == "goal"

@pytest.mark.parametrize("text", ["Latest news on HDFC Bank", "Any headlines about the RBI today?"])
def test_news(text):
    assert intent_of(text) == "news"


# ---------------------------------------------------------------- what must NOT match (false positives)
@pytest.mark.parametrize("text", [
    "What is a SIP?", "What is the price-to-earnings ratio?", "Why do bond prices fall when rates rise?",
    "What is inflation?",
    "I want to learn about my options for investing",          # 'my options' is not 'my portfolio'
    "Tell me about the Nifty index fund concept",              # concept, not a live quote request
    "What is the goal of diversification?",                    # bare 'goal' is not a planning request
    "What is retirement planning?",                            # concept, not 'can I retire at 50'
    "Explain the news cycle effect on markets",                # bare 'news' is not a news request
    "What is the price of a gold ETF?",                        # 'price of' needs a TICKER, not any word
    "What is the price of the underlying asset?",
])
def test_concept_questions_do_not_trigger_rules(text):
    assert intent_of(text) is None, route_by_rules(text)


# ---------------------------------------------------------------- priority and secondary intents
def test_two_rules_primary_wins_secondary_is_recorded():
    d = route_by_rules("How is my portfolio doing compared with the Nifty today?")
    assert d.intent == "portfolio" and "market" in d.secondary_intents

def test_goal_beats_portfolio_when_the_user_asks_for_a_projection():
    assert intent_of("Can I retire at 50 with my portfolio?") == "goal"

def test_tax_beats_market_for_a_tax_question_about_a_stock():
    assert intent_of("What is the capital gains tax if I sell Reliance shares?") == "tax"

def test_a_single_match_is_more_confident_than_a_conflict():
    single = route_by_rules("Analyze my portfolio")
    conflict = route_by_rules("How is my portfolio doing compared with the Nifty today?")
    assert single.confidence > conflict.confidence


# ---------------------------------------------------------------- hygiene
def test_decision_shape():
    d = route_by_rules("Analyze my portfolio")
    assert d.source == "rules" and 0 < d.confidence <= 1 and d.normalized_question

@pytest.mark.parametrize("text", ["ANALYZE MY PORTFOLIO", "analyze   my    portfolio", "  Analyze my portfolio?  "])
def test_case_and_whitespace_do_not_matter(text):
    assert intent_of(text) == "portfolio"

@pytest.mark.parametrize("text", ["", "   ", "???"])
def test_empty_or_meaningless_text_matches_nothing(text):
    assert route_by_rules(text) is None

def test_symbols_are_extracted_for_market_questions():
    d = route_by_rules("What is the share price of RELIANCE and TCS?")
    assert set(d.symbols) >= {"RELIANCE", "TCS"}


def test_duplicate_symbols_are_listed_once_in_order():
    assert route_by_rules("Share price of TCS, then RELIANCE, then TCS again").symbols == ["TCS", "RELIANCE"]

def test_acronyms_are_not_symbols():
    assert route_by_rules("Share price of INFY after the RBI decision").symbols == ["INFY"]


# ---------------------------------------------------------------- market rule v2 (written RED first; found by a live CLI run)
# Live finding: "Sensex and NOPEXYZ price" fell through to Q&A because 'price' only counted in
# 'share price' / 'stock price' / 'price of TICKER'. These are the shapes that mean "give me a number".
@pytest.mark.parametrize("text", [
    "Sensex and NOPEXYZ price", "Sensex price", "Nifty level", "How is Nifty doing",
    "RELIANCE and TCS price", "TCS price", "price of Nifty 50", "Nifty 50 points today",
])
def test_quote_shaped_questions_route_to_market(text):
    assert intent_of(text) == "market", route_by_rules(text)

@pytest.mark.parametrize("text", [
    "What is the Sensex?",                                  # definition: Q&A
    "What is Nifty 50?",
    "Why does the Nifty go up when rates fall?",            # concept about the index, not a quote
    "What is the price of an ETF?",                         # ETF is an acronym, not a ticker
    "SIP price",
    "Does the RBI decision change bond price?",             # RBI is not an instrument
    "Explain the EMI price breakdown",
])
def test_quote_rule_does_not_swallow_concept_questions(text):
    assert intent_of(text) is None, route_by_rules(text)

def test_ticker_plus_price_extracts_the_symbols():
    d = route_by_rules("RELIANCE and TCS price")
    assert d.symbols == ["RELIANCE", "TCS"]


# ---------------------------------------------------------------- connect / disconnect commands -> portfolio agent
@pytest.mark.parametrize("text", [
    "connect to my portfolio", "Connect my portfolio", "connect sample", "connect kite", "connect zerodha",
    "please connect to the sample portfolio", "disconnect sample", "disconnect my portfolio", "connect csv",
])
def test_connect_commands_route_to_portfolio(text):
    assert intent_of(text) == "portfolio", route_by_rules(text)

@pytest.mark.parametrize("text", [
    "How do I connect my bank account to UPI?",          # 'connect' alone is not a portfolio command
    "What is the connection between inflation and rates?",
    "connect the dots between SIP and compounding",
])
def test_connect_in_other_senses_does_not_route(text):
    assert intent_of(text) is None, route_by_rules(text)

def test_connect_command_is_not_a_market_question_even_with_a_ticker_like_word():
    assert intent_of("connect sample") == "portfolio"


# ---------------------------------------------------------------- goal questions asked other ways (2026-11-14)
@pytest.mark.parametrize("text", [
    "How much SIP do I need for 1 crore in 10 years?", "What SIP should I start for 50 lakh in 8 years",
    "How much should I invest every month to get 1 crore?", "How long to reach 25 lakh if I add 10k monthly?",
    "How many years to get to 1 crore?", "If I invest 10000 per month for 15 years what will I get?",
    "If I save 5k a month for 5 years, how much will I have?", "Can I reach 1 crore in 10 years ?",
    "If I put 5000 a month into a fund for 10 years, what will I have?", "If I deposit 10k each month for 5 years what do I get?",
    "If I add 2k every month for 3 years how much is that?",
])
def test_goal_questions_in_other_words(text):
    assert intent_of(text) == "goal"

@pytest.mark.parametrize("text", [
    "What is a SIP?", "What SIP is better, monthly or weekly?", "How much should I invest in gold?",
    "How long does a SIP take to settle?", "If I invest in a mutual fund, what is the risk?", "How long is a lock-in period?",
])
def test_these_are_not_goal_questions(text):
    assert intent_of(text) != "goal"


# ---------------------------------------------------------------- stated preferences and "start over" (Memory v2)
@pytest.mark.parametrize("text", [
    "I'm an aggressive investor", "I am a conservative investor.", "im moderate", "I'm aggressive",
    "My risk appetite is conservative", "my risk tolerance is moderate", "Set my risk appetite to aggressive",
])
def test_a_stated_risk_appetite_is_a_profile_statement(text):
    assert intent_of(text) == "profile"

@pytest.mark.parametrize("text", [
    "What is an aggressive fund?", "I'm aggressive about saving every month", "Is a moderate portfolio safer?",
    "What does conservative mean?", "I'm a moderate investor, can I retire at 50?",
])
def test_these_are_not_profile_statements(text):
    assert intent_of(text) != "profile"

def test_a_risk_statement_inside_a_goal_question_stays_a_goal_question():
    assert intent_of("I'm an aggressive investor, can I retire at 50?") == "goal"

@pytest.mark.parametrize("text", ["let's start over", "Start over", "start again please", "new goal please",
                                  "forget my numbers", "forget the goal"])
def test_start_over_phrases_go_to_the_goal_agent(text):
    assert intent_of(text) == "goal"

@pytest.mark.parametrize("text", ["What is a reset fund?", "I want a new car in 5 years", "What is the start of the financial year?"])
def test_ordinary_sentences_are_not_start_over(text):
    assert intent_of(text) != "goal"


# ---------------------------------------------------------------- a bare risk word is a statement too
@pytest.mark.parametrize("text", [
    "aggressive", "Conservative.", "moderate", "use aggressive", "try conservative", "make it aggressive",
    "go with moderate", "switch to aggressive", "change it to conservative", "make me aggressive", "aggressive one",
    "an aggressive investor", "moderate risk",
])
def test_a_bare_risk_word_sets_the_risk_appetite(text):
    assert intent_of(text) == "profile"

@pytest.mark.parametrize("text", [
    "aggressive funds", "What is conservative?", "moderate returns on gold", "investments", "is aggressive better?",
    "Aggressive growth funds in India",
])
def test_these_are_not_risk_statements(text):
    assert intent_of(text) != "profile"


# ---------------------------------------------------------------- "assuming 12% returns" alone is a goal assumption
@pytest.mark.parametrize("text", ["assuming 12% returns", "Assume 10 percent growth", "assuming 7.5% a year", "assuming a 9% return"])
def test_an_assumed_return_goes_to_the_goal_agent(text):
    assert intent_of(text) == "goal"

@pytest.mark.parametrize("text", ["What is 12% of 500?", "Assuming I retire at 60", "assume the market falls", "what is a 12% return worth"])
def test_these_are_not_return_assumptions(text):
    assert intent_of(text) != "goal" or "retire" in text


# ---------------------------------------------------------------- news asked other ways
@pytest.mark.parametrize("text", ["any news on Infosys", "Any news today?", "what's the news", "whats the latest news",
                                  "news today", "latest news on Infosys", "headlines for Tata Motors", "any news this week",
                                  "Any news about the market?"])
def test_news_questions_in_other_words(text):
    assert intent_of(text) == "news"

@pytest.mark.parametrize("text", ["What is financial news?", "What is a newsletter?", "How do I read the news section of a factsheet?"])
def test_these_are_not_news_requests(text):
    assert intent_of(text) != "news"
