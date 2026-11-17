"""Narration must not introduce numbers: every number the model writes has to come from the facts we gave it.

Real case (2026-11-15): the facts said "₹20,000 a month for 15 years"; the model added "a total of ₹36,00,000".
The arithmetic was right, but the prompt says "use ONLY the numbers in DATA" and a prompt is only a request.
This is the check in code. A story that fails it is dropped and the user gets the numbers block alone.

Run:  .venv/bin/python -m pytest tests/core/grounding_test.py -v
"""
import pytest

from src.core.grounding import is_grounded, numbers_in


# ================================================================ numbers_in
def test_plain_and_comma_numbers_are_read_as_numbers():
    assert numbers_in("₹4,539,454 and 15 years") == {4539454.0, 15.0}

def test_decimals_and_percentages():
    assert numbers_in("4.5% a year") == {4.5}

def test_indian_and_western_grouping_are_the_same_number():
    assert numbers_in("₹36,00,000") == numbers_in("₹3,600,000") == {3600000.0}

def test_a_trailing_comma_or_full_stop_is_not_part_of_the_number():
    assert numbers_in("worth ₹2,794,828, or ₹6,339,246.") == {2794828.0, 6339246.0}

def test_no_numbers():
    assert numbers_in("nothing here") == set() and numbers_in("") == set() and numbers_in(None) == set()


# ================================================================ is_grounded
FACTS = "Portfolio: ₹4,539,454 over 15 years, saving ₹20,000 a month. Rates 3%, 7%, 11%."

def test_a_story_that_repeats_the_facts_is_grounded():
    assert is_grounded("You save ₹20,000 monthly for 15 years and could reach ₹4,539,454 at 7%.", FACTS)

def test_a_new_number_is_not_grounded():
    assert not is_grounded("You will put away a total of ₹36,00,000.", FACTS)

def test_a_different_format_of_a_known_number_is_fine():
    assert is_grounded("That is about ₹45,39,454.", FACTS)

def test_a_rounded_number_is_not_the_same_number():
    assert not is_grounded("Roughly ₹4.5 million.", FACTS)

def test_numbers_from_the_question_are_allowed_when_given_as_a_source():
    assert is_grounded("You asked about ₹30,000 a month.", FACTS, "what if I save 30000?")

def test_without_that_source_they_are_not():
    assert not is_grounded("You asked about ₹30,000 a month.", FACTS)

def test_single_digit_numbers_are_ignored():
    assert is_grounded("In 3 short steps, 1 idea: ₹20,000 a month.", FACTS)

def test_a_story_with_no_numbers_is_grounded():
    assert is_grounded("This is only an illustration.", FACTS)

def test_one_bad_number_among_good_ones_fails_the_story():
    assert not is_grounded("₹20,000 a month for 15 years makes ₹9,999,999.", FACTS)

def test_none_story_or_sources_are_safe():
    assert is_grounded("", FACTS) and is_grounded(None, FACTS) and not is_grounded("₹55,555", None)

def test_a_near_miss_is_not_accepted():
    assert not is_grounded("₹4,539,455", FACTS)
