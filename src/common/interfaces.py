from typing import Literal
from pydantic import BaseModel

from src.core.contracts import Citation
from src.core.contracts import AgentResult

_STATUS = {"rag": "ok", "glossary": "ok", "no_source": "no_source",
           "clarify": "clarify", "redirect": "redirect", "error": "error"}



class QARequest(BaseModel):
    question: str
    category_hint: str | None = None

class QAResult(BaseModel):
    answer: str
    citations: list[Citation]
    route: Literal["glossary", "rag", "no_source", "clarify", "redirect", "error"]
    disclaimer: str = "Educational information only — not financial advice."

    def to_result(self, agent: str = "finance_qa") -> AgentResult:
        return AgentResult(
            agent=agent,
            status=_STATUS[self.route],
            text=self.answer,
            citations=self.citations,
            disclaimer=self.disclaimer,
            meta={"route": self.route},
        )
