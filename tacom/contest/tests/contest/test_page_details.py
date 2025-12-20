from itertools import product

from bs4 import BeautifulSoup
from contest.factories import ContestFactory, ContestState, PeriodState
from django.test import TestCase
from django.urls import reverse


class ButtonsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        date_states: list[PeriodState] = list(PeriodState)
        bool_states = [True, False]
        cls.contest_states = [
            ContestState(
                judge_registration=judge_registration,
                registration=registration,
                result_is_published=result_is_published,
            )
            for judge_registration, registration, result_is_published in product(
                date_states, date_states, bool_states
            )
        ]

    def test_buttons_enabled_disabled(self):
        for state in self.contest_states:
            with self.subTest(
                judge_registration=state.judge_registration.value,
                registration=state.registration.value,
                result_is_published=state.result_is_published,
            ):
                contest = ContestFactory(_state=state)
                url = reverse(
                    "contest:contest_detail",
                    kwargs={"slug": contest.slug},
                )
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                soup = BeautifulSoup(response.content, "html.parser")
                buttons = {
                    "judge_registration": "contest-judging",
                    "registration": "contest-register",
                    "result_is_published": "contest-results",
                }
                for button_name, button_id in buttons.items():
                    with self.subTest(button=button_name):
                        button = soup.find(id=button_id)
                        self.assertIsNotNone(button)
                        classes = button.get("class", [])

                        version = getattr(state, button_name)
                        expected_enabled = (
                            version == PeriodState.during
                            if isinstance(version, PeriodState)
                            else version
                        )
                        if expected_enabled:
                            self.assertNotIn("disabled", classes)
                        else:
                            self.assertIn("disabled", classes)
