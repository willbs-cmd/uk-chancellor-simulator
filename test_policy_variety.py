"""Coverage for the expanded randomized policy pool."""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import decisions


def test_weekly_policy_pool_has_more_topics_than_a_single_term_needs():
    assert len(decisions.DECISIONS) >= 25
    assert len(decisions.EXTRA_POLICY_DECISIONS) >= 15


def test_each_term_gets_ten_distinct_policy_topics_and_five_options_each():
    for seed in (1, 7, 42):
        topics = [
            decisions.get_weekly_decision(seed, 1, year, block)
            for year in range(1, 6)
            for block in (1, 2)
        ]
        assert len({topic['title'] for topic in topics}) == 10
        for topic in topics:
            assert len(topic['options']) == 5
            assert len(topic['effects']) == 5
            assert all('message' in effect for effect in topic['effects'])


def test_new_term_and_seed_can_change_the_topic_order():
    first = [decisions.get_weekly_decision(11, 1, y, b)['title'] for y in range(1, 6) for b in (1, 2)]
    second = [decisions.get_weekly_decision(12, 1, y, b)['title'] for y in range(1, 6) for b in (1, 2)]
    next_term = [decisions.get_weekly_decision(11, 2, y, b)['title'] for y in range(1, 6) for b in (1, 2)]
    assert first != second
    assert first != next_term
