import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from django.urls import reverse

from .models.config import DiscoveredUrl, HttpMethod
from .models.url_manager import UrlCategory


@dataclass
class TestContext:
    __test__ = False  # prevent pytest from collecting this as a test class
    resolved_url: str
    authorized_users: list
    unauthorized_users: list
    method_data: dict[str, dict] = field(default_factory=dict)


class BaseDataProvider(ABC):
    @abstractmethod
    def setup(self) -> None: ...

    @abstractmethod
    def get_test_context(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> TestContext: ...

    @abstractmethod
    def get_anonymous_user(self): ...

    @abstractmethod
    def teardown(self) -> None: ...


# ─────────────────────────────────────────────────────────────
# Project-specific implementation
# ─────────────────────────────────────────────────────────────

_CAPABILITY_TO_ROLE = {
    "JUDGE_FINALS": "judge_finals",
    "JUDGE_BOS": "judge_bos",
    "VIEW_JUDGING_ENTRIES_LIST": "judge",
    "EDIT_SCORESHEET": "judge",
    "VIEW_SCORESHEET": "judge",
    "CONTEST_MANAGE_TEAM": "manager",
    "CONTEST_MANAGE_JUDGES": "manager",
    "ENTRY_RECEIVE": "entry_manager",
    "ENTRY_PAYMENTS": "entry_manager",
    "ENTRY_ENCODE": "entry_coder",
    "ENTRY_DECODE": "entry_coder",
    "SYSTEM_TRANSLATE": None,  # global role via Django group
}

_SLUG_A = "url-test-contest-a"
_SLUG_B = "url-test-contest-b"

_URL_PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")


class ContestDataProvider(BaseDataProvider):
    """
    Project-specific data provider for the contest app.
    Creates two contests (A and B) for capability testing.
    """

    def setup(self) -> None:
        from contest.factories.user_factory import UserFactory
        from contest.models import Contest, Style, Category, Entry

        # Shared test style (deterministic slug)
        self.style, _ = Style.objects.get_or_create(
            slug="url-test-style-um",
            defaults={
                "name": "URL Test Style",
                "description": "Test style for URL Manager",
                "description_pl": "Styl testowy dla URL Managera",
            },
        )

        # Two contests with deterministic slugs (update_or_create ensures fresh state)
        self.contest_a, _ = Contest.objects.update_or_create(
            slug=_SLUG_A,
            defaults=self._contest_defaults(_SLUG_A),
        )
        self.contest_b, _ = Contest.objects.update_or_create(
            slug=_SLUG_B,
            defaults=self._contest_defaults(_SLUG_B),
        )

        # Ensure each contest has at least one category
        self._ensure_category(self.contest_a)
        self._ensure_category(self.contest_b)

        # Basic user (logged in, no capabilities)
        self.basic_user = UserFactory(profile=True)

        # Entry owned by basic_user
        cat_a = self.contest_a.categories.first()
        self.entry_a = Entry.objects.filter(
            category__contest=self.contest_a,
            brewer=self.basic_user,
        ).first()
        if not self.entry_a and cat_a:
            self.entry_a = Entry.objects.create(
                category=cat_a,
                brewer=self.basic_user,
                name="URL Test Entry",
                sweetness=Entry.SweetnessLevel.MEDIUM,
                carbonation=Entry.CarbonationLevel.STILL,
                is_received=True,
                is_paid=True,
            )

        # Package owned by basic_user
        self._setup_package()

        # Payment owned by basic_user
        self._setup_payment()

        # ScoreSheet for an entry
        self._setup_scoresheet()

        # JudgeInCompetition for judge management URLs
        self._setup_judge_application()

        # User capability cache: capability_name → user with that cap for contest_a
        self._cap_users: dict[str, object] = {}

    def _ensure_category(self, contest) -> None:
        from contest.models import Category

        if not contest.categories.exists():
            try:
                Category.objects.create(
                    contest=contest,
                    style=self.style,
                    entries_limit=5,
                )
            except Exception:
                # Another worker may have created it; refresh
                contest.refresh_from_db()

    def _contest_defaults(self, slug: str) -> dict:
        from faker import Faker

        f = Faker("pl_PL")
        from datetime import date, timedelta

        today = date.today()
        return {
            "title": f"URL Test Contest {slug}",
            "description": f.paragraph(),
            "description_pl": f.paragraph(),
            "rules": f.paragraph(),
            "rules_pl": f.paragraph(),
            "entry_fee_amount": "10.00",
            "entry_fee_currency": "PLN",
            "payment_transfer_info": "",
            "discount_rate": 0,
            "delivery_address": f.address(),
            "registration_date_from": today - timedelta(days=5),
            "registration_date_to": today + timedelta(days=5),
            "judge_registration_date_from": today - timedelta(days=5),
            "judge_registration_date_to": today + timedelta(days=5),
            "delivery_date_from": today - timedelta(days=5),
            "delivery_date_to": today + timedelta(days=5),
            "judging_date_from": today - timedelta(days=5),
            "judging_date_to": today + timedelta(days=5),
            "competition_is_published": True,
            "result_is_published": True,
            "is_judging_eliminations": True,
            "is_judging_finals": True,
            "is_judging_bos": True,
        }

    def _setup_package(self) -> None:
        from contest.models import EntriesPackage

        try:
            self.package_a = EntriesPackage.objects.filter(
                owner=self.basic_user, contest=self.contest_a
            ).first()
            if not self.package_a:
                self.package_a = EntriesPackage.objects.create(
                    owner=self.basic_user,
                    contest=self.contest_a,
                )
                self.package_a.entries.add(self.entry_a)
        except Exception:
            self.package_a = None

    def _setup_payment(self) -> None:
        from contest.models import Payment, PaymentMethod

        try:
            method, _ = PaymentMethod.objects.get_or_create(
                code="fake",
                defaults={
                    "name": "Fake - for testing",
                    "name_pl": "Udawana - do testów",
                },
            )
            self.payment_method = method
            self.payment_a = Payment.objects.filter(
                user=self.basic_user, contest=self.contest_a
            ).first()
            if not self.payment_a:
                self.payment_a = Payment.objects.create(
                    method=method,
                    user=self.basic_user,
                    contest=self.contest_a,
                    amount="10.00",
                    currency="PLN",
                )
        except Exception:
            self.payment_a = None
            self.payment_method = None

    def _setup_scoresheet(self) -> None:
        from contest.models import ScoreSheet

        try:
            self.scoresheet_a = ScoreSheet.objects.filter(entry=self.entry_a).first()
            if not self.scoresheet_a:
                self.scoresheet_a = ScoreSheet.objects.create(
                    entry=self.entry_a,
                    appearance_score=5,
                    aroma_score=15,
                    flavor_score=15,
                    finish_score=5,
                    overall_score=5,
                )
        except Exception:
            self.scoresheet_a = None

    def _setup_judge_application(self) -> None:
        from contest.models.judges import JudgeInCompetition
        from contest.factories.user_factory import UserFactory

        try:
            judge_user = UserFactory(profile=True, judge=True)
            self.judge_application = JudgeInCompetition.objects.filter(
                contest=self.contest_a
            ).first()
            if not self.judge_application:
                self.judge_application = JudgeInCompetition.objects.create(
                    contest=self.contest_a,
                    user=judge_user,
                )
        except Exception:
            self.judge_application = None

    def get_test_context(
        self,
        url: DiscoveredUrl,
        category: UrlCategory,
        subcategory: str | None = None,
    ) -> TestContext:
        kwargs = self._url_kwargs(url)

        try:
            resolved_url = reverse(url.full_name, kwargs=kwargs)
        except Exception:
            resolved_url = f"/__unresolvable__/{url.full_name}/"

        method_data = self._get_method_data(url)

        if category == "anonymous":
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[],
                unauthorized_users=[],
                method_data=method_data,
            )

        if category == "logged_in":
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[self.basic_user],
                unauthorized_users=[],
                method_data=method_data,
            )

        if category == "by_capability":
            cap_name = subcategory or ""
            cap_user = self._get_cap_user(cap_name)
            unauthorized = [self.basic_user]
            if cap_name in _CAPABILITY_TO_ROLE:
                wrong_user = self._create_user_with_capability(cap_name, self.contest_b)
                unauthorized.append(wrong_user)
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[cap_user] if cap_user else [],
                unauthorized_users=unauthorized,
                method_data=method_data,
            )

        if category == "by_group":
            group_name = subcategory or ""
            group_user = self._create_user_in_group(group_name)
            return TestContext(
                resolved_url=resolved_url,
                authorized_users=[group_user],
                unauthorized_users=[self.basic_user],
                method_data=method_data,
            )

        return TestContext(
            resolved_url=resolved_url,
            authorized_users=[],
            unauthorized_users=[],
            method_data=method_data,
        )

    def _get_cap_user(self, capability_name: str):
        if capability_name not in self._cap_users:
            user = self._create_user_with_capability(capability_name, self.contest_a)
            self._cap_users[capability_name] = user
        return self._cap_users[capability_name]

    def _create_user_with_capability(self, capability_name: str, contest):
        from contest.factories.user_factory import UserFactory
        from contest.models.membership import ContestMembership, ContestMembershipRole

        role_value = _CAPABILITY_TO_ROLE.get(capability_name)
        if not role_value:
            return None

        user = UserFactory(profile=True)
        membership = ContestMembership.objects.create(user=user, contest=contest)
        ContestMembershipRole.objects.create(membership=membership, role=role_value)
        # Tag user for AccessTester user_type reporting
        user._test_capability = capability_name
        return user

    def _create_user_in_group(self, group_name: str):
        from contest.factories.user_factory import UserFactory
        from django.contrib.auth.models import Group

        user = UserFactory()
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        user._test_group = group_name
        return user

    def _url_kwargs(self, url: DiscoveredUrl) -> dict:
        # url-specific implementation:
        if url.namespace == "contest" and url.name == "toggle_contest_role":
            kwargs = {
                "contest_slug": self.contest_a.slug,
                "role_name": "judge",
                "user_id": self.basic_user.id,
            }
        else:
            kwargs = {}
            for match in _URL_PARAM_RE.finditer(url.url_pattern):
                type_str, param_name = match.group(1), match.group(2)
                value = self._resolve_param(param_name, type_str, url)
                if value is not None:
                    kwargs[param_name] = value
        return kwargs

    def _resolve_param(self, param_name: str, type_str: str | None, url: DiscoveredUrl):
        if param_name == "contest_slug":
            return self.contest_a.slug
        if param_name == "style_slug":
            return self.style.slug
        if param_name == "functionality":
            return "judging"

        # UUID-based params
        if param_name == "category_id":
            cat = self.contest_a.categories.first()
            return cat.id if cat else None
        if param_name == "package_id":
            return self.package_a.id if self.package_a else None
        if param_name == "payment_id":
            return self.payment_a.id if self.payment_a else None
        if param_name == "entry":
            return self.entry_a.id
        if param_name == "pk":
            return self._resolve_pk_param(url)

        # Fallback by type
        if type_str == "uuid":
            import uuid

            return uuid.uuid4()
        if type_str == "slug":
            return "test"
        if type_str == "int":
            return 1
        if type_str == "str":
            return "test"
        return None

    def _resolve_pk_param(self, url: DiscoveredUrl):
        # For UUID pk params
        url_name = url.name
        if url_name in (
            "entry_edit",
            "entry_delete",
            "entry_results",
            "add_entry_category",
        ):
            if url_name == "add_entry_category":
                cat = self.contest_a.categories.first()
                return cat.id if cat else None
            return self.entry_a.id
        if url_name in ("scoresheet_view", "scoresheet_edit"):
            return self.scoresheet_a.id if self.scoresheet_a else None
        if url_name in ("judge_status_edit", "judge_status_view"):
            return self.judge_application.id if self.judge_application else None
        if url_name in ("delivery_process",):
            return self.package_a.id if self.package_a else None
        if url_name in ("payment_process",):
            return self.payment_a.id if self.payment_a else None
        return 1

    def _get_method_data(self, url: DiscoveredUrl) -> dict[str, dict]:
        data: dict[str, dict] = {}
        for method in url.supported_methods:
            if method in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH):
                form_data = self._minimal_form_data(url, method)
                data[method.value] = form_data
        return data

    def _minimal_form_data(self, url: DiscoveredUrl, method: HttpMethod) -> dict:
        return {}

    def get_anonymous_user(self):
        return None

    def teardown(self) -> None:
        pass
