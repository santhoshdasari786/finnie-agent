import re

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str | None) -> set[float]:
    """Every number in the text as a float. Grouping style does not matter: 36,00,000 and 3,600,000 are equal."""
    out: set[float] = set()
    for raw in _NUM.findall(text or ""):
        try:
            out.add(float(raw.replace(",", "")))
        except ValueError:
            pass
    return out


def is_grounded(story: str | None, *sources: str | None) -> bool:
    """True when every number in `story` also appears in one of `sources`. Whole numbers below 10 are ignored."""
    allowed: set[float] = set()
    for source in sources:
        allowed |= numbers_in(source)
    return all((n < 10 and n == int(n)) or n in allowed for n in numbers_in(story))
