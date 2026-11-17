from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResponse:
    """Normalizes a LangChain AIMessage into clean, printable text."""

    raw: Any
    text: str

    @classmethod
    def from_message(cls, message: Any) -> "AgentResponse":
        content = message.content
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = [
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
                if not isinstance(block, dict) or block.get("type") == "text"
            ]
            text = "\n".join(p for p in parts if p)
        else:
            text = str(content)
        return cls(raw=content, text=text.strip())

    def print(self) -> None:
        try:
            from rich.console import Console
            from rich.markdown import Markdown
            Console().print(Markdown(self.text))
        except ImportError:
            print(self.text)

    def __str__(self) -> str:
        return self.text
