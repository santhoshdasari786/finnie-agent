from src.agents.finance_qa_agent import FinanceQAAgent
from src.prompts.tax_prompts import (ASKS_FOR_NUMBER, FIGURES_CAUTION, HAS_FIGURE, NUMBERS_NOTE,
                                     TAX_DISCLAIMER, TAX_SYSTEM_PROMPT)


class TaxEducationAgent(FinanceQAAgent):
    name = "tax_education"
    _system_prompt = TAX_SYSTEM_PROMPT
    _forced_category = "costs-taxes"
    _disclaimer = TAX_DISCLAIMER

    def _extra_note(self, question):
        return NUMBERS_NOTE if ASKS_FOR_NUMBER.search(question) else ""

    def _check_answer(self, answer):
        return answer + FIGURES_CAUTION if HAS_FIGURE.search(answer) else answer
