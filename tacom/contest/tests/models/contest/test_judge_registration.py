from contest.factories import ContestFactory, ContestState, PeriodState
from django.test import TestCase
import pytest


@pytest.mark.unit
class CanRegisterJudgesTests(TestCase):
    def test_cannot_register_before(self):
        contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.before)
        )
        self.assertEqual(contest.can_judges_register, False)

    def test_cannot_register_after(self):
        contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.after)
        )
        self.assertEqual(contest.can_judges_register, False)

    def test_can_register_during(self):
        contest = ContestFactory(
            _state=ContestState(judge_registration=PeriodState.during)
        )
        self.assertEqual(contest.can_judges_register, True)
