

import logging
import re

from src.common.models import GuardVerdict, QASettings

SELF_HARM_MESSAGE = (
    "I'm really sorry you're going through this. I can't help with this here, "
    "but you don't have to face it alone. Please reach out to someone you trust, "
    "or contact your local emergency number or a crisis helpline right now.")

_SELF_HARM = re.compile(
    r"\b(kill(ing)?\s+myself|end(ing)?\s+(my\s+life|it\s+all)|suicid\w*|self[- ]?harm"
    r"|want\s+to\s+die|don'?t\s+want\s+to\s+live)\b", re.I)


DISTRESS_SUFFIX = (
    "\n\nIf you're under financial pressure, a qualified financial counsellor, or your bank or lender's "
    "hardship team, can look at your actual numbers. This assistant only gives general education.")

_OBLIGATION = r"(?:mortgage|rent|loans?|bills?|e\.?m\.?i\.?s?|debts?|credit\s+cards?|instal?lments?|dues?|payments?)"
_UNABLE     = r"(?:can'?t|cannot|can\s+not|couldn'?t|unable\s+to|struggling\s+to)"
_PAY        = r"(?:pay|afford|repay|make|meet|cover)"

_DISTRESS = re.compile(
    rf"\b{_UNABLE}\s+{_PAY}\s+(?:\w+\s+){{0,3}}{_OBLIGATION}\b"     # can't pay (my credit card) EMI
    r"|\b(?:lost|losing)\s+(?:my|our)\s+(?:job|income|salary|business)\b"
    r"|\b(?:laid\s+off|got\s+fired|was\s+fired|made\s+redundant|unemployed|jobless)\b"
    r"|\b(?:lose|losing)\s+(?:my\s+)?(?:house|home)\b"
    r"|\bdrowning\s+in\s+debt\b|\bbehind\s+on\s+(?:my\s+)?(?:payments?|emis?|loan|rent)\b"
    r"|\bbankrupt(?:cy)?\b|\bdebt\s+collectors?\b|\brepossess\w*\b|\bevict\w*\b", re.I)


_ADVICE = re.compile(
    r"\bshould\s+i\s+(buy|sell|invest|put|switch|stop|start)\b"
    r"|\bwhich\s+(stock|fund|etf|share)s?\s+(should|to)\b"
    r"|\bis\s+it\s+(a\s+)?good\s+(time|idea)\s+to\b"
    r"|\bwhat\s+should\s+i\s+(buy|invest)", re.I)

_INJECTION = re.compile(
    r"\bignore\s+(all\s+|your\s+|the\s+|previous\s+)*(instructions|rules|prompt)\b"
    r"|\b(reveal|show|print)\s+(your\s+)?(system\s+)?prompt\b|\byou\s+are\s+now\b", re.I)


log = logging.getLogger(__name__)

class Guardrails:
    def __init__(self, settings: QASettings | None = None):
        self._s = settings or QASettings()

    def check(self, question: str) -> GuardVerdict:
        text = (question or "").strip()
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        if not re.search(r"\w", text):
            return self._block('empty' , self._s.redirect_message)
        if len(text) > self._s.max_question_chars:
            return self._block("too_long",
                               f"Please keep your question under {self._s.max_question_chars} characters."
                               )
        # Self Harm
        if _SELF_HARM.search(text):
            return self._block('self_harm', SELF_HARM_MESSAGE)

        # Distress
        flags = set()
        if _DISTRESS.search(text):
            flags.add("financial_distress")

        # advice seeking
        if _ADVICE.search(text):
            flags.add("advice_seeking")

        # Prompt injection
        if _INJECTION.search(text):
            flags.add("injection_attempt")
            log.warning("possible prompt-injection attempt")
        return GuardVerdict(flags=frozenset(flags))

    # def finalize(self, answer: str, verdict: GuardVerdict) -> str:
    #     return answer + DISTRESS_SUFFIX if "financial_distress" in verdict.flags else answer

    def finalize(self, answer: str, verdict: GuardVerdict) -> str:
        if "financial_distress" in verdict.flags and not answer.endswith(DISTRESS_SUFFIX):
            return answer + DISTRESS_SUFFIX
        return answer

    def _block(self, category, reply):
        log.info("guardrail blocked: %s", category)
        return GuardVerdict('block', category, reply)