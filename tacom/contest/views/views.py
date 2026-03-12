import json
import os
from decimal import Decimal
from logging import getLogger

from contest import payu
from contest.forms import (
    BlankForm,
    ContestBestOfShowForm,
    EditEntryForm,
    FakePaymentForm,
    FinalEntriesFormset,
    NewAdminPackage,
    NewEntryForm,
    NewPackageForm,
    NewPaymentForm,
    ProfileForm,
    ScoreSheetForm,
)
from contest.models import (
    Category,
    Contest,
    EntriesPackage,
    Entry,
    Payment,
    RebateCode,
    ScoreSheet,
    User,
)
from contest.permissions.capabilities import Capability
from contest.permissions.mixins import CapabilityRequiredMixin
from contest.utils import get_client_ip, mail_entry_status_change
from contest.views.contest import ContestContextMixin, ContestPassesTestMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, Prefetch, When
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
    View,
)
from django.views.generic.base import ContextMixin
from paypal.standard.forms import PayPalPaymentsForm

logger = getLogger("views")


class UserFullProfileMixin(UserPassesTestMixin):
    """
    Class redirects user to fill in the profile if he hasn't done so yet
    """

    def test_func(self):
        if not self.request.user.is_authenticated:
            return True
        return self.request.user.profile_complete

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.warning(self.request, _("Complete your profile, please."))
        return redirect("contest:profile_edit")


class UserOwnsPackageMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user
            == get_object_or_404(EntriesPackage, id=self.kwargs["package_id"]).owner
        )

    def handle_no_permission(self):
        raise Http404


class UsersEntryListView(LoginRequiredMixin, UserFullProfileMixin, ListView):
    """
    Displays list of user's entries - priomary purpose is to let him view
    the results after the registration has ended
    """

    template_name = "contest/view_entry_list.html"
    context_object_name = "entries"

    def __init__(self):
        self.contest = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, slug=self.kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        payu.update_user_payments_statuses(self.request.user)
        return (
            Entry.objects.filter(brewer=self.request.user)
            .filter(category__contest=self.contest)
            .select_related("category__style", "category__contest")
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context["contest"] = self.contest
        return context


class AddEntryView(LoginRequiredMixin, UserFullProfileMixin, CreateView):
    model = Entry
    template_name = "contest/add_entry.html"
    form_class = NewEntryForm

    def __init__(self):
        self.category = None
        self.contest = None
        self.style = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(
            Category.objects.select_related("contest", "style"), pk=kwargs["pk"]
        )
        self.contest = self.category.contest
        self.style = self.category.style
        if not self.contest.is_registrable:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["style"] = self.style
        context["contest"] = self.contest
        context["entries"] = (
            Entry.objects.filter(brewer=self.request.user)
            .filter(category__contest=context["contest"])
            .select_related("category__style", "category__contest")
        )
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["is_extra_mandatory"] = self.category.style.extra_info_is_required
        if get_language() == "pl":
            form_kwargs["extra_hint"] = self.category.style.extra_info_hint_pl
        else:
            form_kwargs["extra_hint"] = self.category.style.extra_info_hint
        form_kwargs["user"] = self.request.user
        form_kwargs["category"] = self.category
        form_kwargs["return_url"] = self.get_success_url()
        return form_kwargs

    def get_success_url(self):
        return reverse(
            "contest:add_entry_contest",
            kwargs={"slug": self.contest.slug},
        )

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form, error=True))

    def form_valid(self, form):
        # Save the form and set the success message
        response = super().form_valid(form)
        messages.success(self.request, _("Entry has been added successfully"))
        return response


class EditEntryView(UserPassesTestMixin, UpdateView):
    model = Entry
    template_name = "contest/generic_update.html"
    form_class = EditEntryForm

    def test_func(self):
        return (
            self.get_object().brewer == self.request.user
            and self.get_object().can_be_edited()
        )

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        category = self.get_object().category
        form_kwargs["is_extra_mandatory"] = category.style.extra_info_is_required
        form_kwargs["extra_hint"] = category.style.extra_info_hint
        form_kwargs["user"] = self.request.user
        form_kwargs["category"] = category
        form_kwargs["return_url"] = self.get_success_url()
        return form_kwargs

    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        else:
            return reverse(
                "contest:add_entry_contest",
                kwargs={"slug": self.object.category.contest.slug},
            )

    def form_valid(self, form):
        # Save the form and set the success message
        response = super().form_valid(form)
        messages.success(self.request, _("Entry has been updated successfully"))
        return response

    def handle_no_permission(self):
        """
        Override method to rise 404 instead of 403
        """
        try:
            return super().handle_no_permission()
        except PermissionDenied:
            raise Http404


class DeleteEntryView(UserPassesTestMixin, DeleteView):
    model = Entry
    # template_name = 'contest/entry_confirm_delete.html'
    context_object_name = "entry"

    def get_queryset(self):
        return super().get_queryset().select_related("brewer", "category")

    def get_object(self, queryset=None):
        return self.object_cached

    @cached_property
    def object_cached(self):
        return super().get_object()

    def test_func(self):
        entry = self.get_object()
        return entry.brewer == self.request.user and entry.can_be_deleted()

    def form_valid(self, form):
        messages.success(self.request, _("Entry has been deleted"))

        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        else:
            return reverse_lazy(
                "contest:add_entry_contest",
                kwargs={"slug": self.object.category.contest.slug},
            )

    def handle_no_permission(self):
        """
        Override method to rise 404 instead of 403
        """

        try:
            return super().handle_no_permission()
        except PermissionDenied:
            raise Http404


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "contest/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = Entry.objects.filter(
            brewer=self.request.user
        ).select_related("category__contest", "category__style")
        context["is_one_contest"] = Contest.registrable.count() == 1
        if context["is_one_contest"]:
            context["contest"] = Contest.registrable.first()
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "contest/generic_update.html"
    form_class = ProfileForm
    success_url = reverse_lazy("contest:profile")

    def get_object(self, queryset=None):
        return self.request.user


class AddPackageView(LoginRequiredMixin, UserFullProfileMixin, CreateView):
    model = EntriesPackage
    template_name = "contest/package_update.html"
    success_url = reverse_lazy("contest:profile")
    form_class = NewPackageForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = None
        self.contest = None

    def get_form_kwargs(self):
        self.owner = self.request.user
        self.contest = Contest.objects.get(slug=self.kwargs["slug"])
        kwargs = super().get_form_kwargs()
        kwargs["entries"] = Entry.objects.filter(category__contest=self.contest).filter(
            brewer=self.owner
        )
        kwargs["purpose"] = ""
        kwargs["owner"] = self.owner
        kwargs["contest"] = self.contest
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.owner
        form.instance.contest = self.contest
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["referer"] = self.request.META.get("HTTP_REFERER")
        return context


class AddPackageForPayment(AddPackageView, ContestContextMixin):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["entries"] = kwargs["entries"].filter(is_paid=False)
        kwargs["purpose"] = _("for payment")
        return kwargs

    def get_success_url(self):
        return reverse(
            "contest:payment_method_selection",
            kwargs={"slug": self.contest.slug, "package_id": self.object.id},
        )


class AddPackageForPrinting(AddPackageView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["entries"] = kwargs["entries"].filter(is_paid=True)
        kwargs["purpose"] = _("to print labels")
        # kwargs['target'] = '_blank'
        return kwargs

    def get_success_url(self):
        return reverse("contest:labels_print", kwargs={"package_id": self.object.id})


class AddPackageOfDelivered(
    CapabilityRequiredMixin, ContestContextMixin, AddPackageView
):
    required_capability = Capability.ENTRY_RECEIVE
    form_class = NewAdminPackage

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["entries"] = (
            Entry.objects.filter(category__contest=self.contest)
            .filter(is_paid=True)
            .filter(is_received=False)
            .order_by("code")
        )
        kwargs["purpose"] = _("to mark as delivered")
        kwargs["show_entry_codes"] = True
        return kwargs

    def get_success_url(self):
        return reverse(
            "contest:delivery_process",
            args=(
                self.contest.slug,
                self.object.id,
            ),
        )


class ProcessPackageDelivered(CapabilityRequiredMixin, ContestContextMixin, DeleteView):
    model = EntriesPackage
    template_name = "contest/generic_update.html"
    form_class = BlankForm
    required_capability = Capability.ENTRY_RECEIVE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        text = _("Are you sure, you want to mark following entries as delivered?")
        kwargs["head_info"] = mark_safe(
            f"{text}<ol>{self.object.entries_codes_as_li()}</ol>"
        )
        return kwargs

    def get_success_url(self):
        contest = self.object.contest
        brewers = set(self.object.entries.values_list("brewer", flat=True))
        for brewer in brewers:
            mail_entry_status_change(
                self.object.entries.filter(brewer__id=brewer).all(), "RECEIVED"
            )
        self.object.entries.update(is_received=True)
        return reverse("contest:delivery_select", args=(contest.slug,))


class SelectPaymentMethodView(
    LoginRequiredMixin, UserOwnsPackageMixin, ContestContextMixin, CreateView
):
    model = Payment
    form_class = NewPaymentForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.package = None

    def dispatch(self, request, *args, **kwargs):
        self.package = get_object_or_404(EntriesPackage, id=self.kwargs["package_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["contest"] = self.package.contest
        return kwargs

    def get_discount(self):
        try:
            promo_code = RebateCode.objects.get(user=self.package.owner)
        except RebateCode.DoesNotExist:
            return 0
        if promo_code:
            return self.package.contest.discount_rate
        else:
            return 0

    def form_valid(self, form):
        form.instance.user = self.package.owner
        form.instance.contest = self.package.contest
        form.instance.amount = round(
            self.package.contest.entry_fee_amount
            * self.package.entries.count()
            * Decimal(1 - self.get_discount() / 100),
            2,
        )
        form.instance.currency = self.package.contest.entry_fee_currency
        return super().form_valid(form)

    def get_success_url(self):
        # first add entries
        for entry in self.package.entries.all():
            self.object.entries.add(entry)
        # delete package as it's not needed anymore
        self.package.delete()

        # decide what to do next
        if self.object.method.code == "fake":
            return reverse("contest:payment_fake", args=(self.object.id,))
        if self.object.method.code == "transfer":
            return reverse("contest:payment_transfer", args=(self.object.id,))
        if self.object.method.code == "payu":
            return reverse("contest:payment_payu", args=(self.object.id,))
        if self.object.method.code == "paypal":
            return reverse("contest:payment_paypal", args=(self.object.id,))


class PaymentView(LoginRequiredMixin, FormView):
    template_name = "contest/generic_update.html"

    def __init__(self, *args, **kwargs):
        self.payment = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.payment = get_object_or_404(Payment, id=self.kwargs["payment_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["return_url"] = reverse(
            "contest:add_entry_contest", args=(self.payment.contest.slug,)
        )
        return kwargs

    def get_success_url(self):
        return reverse("contest:add_entry_contest", args=(self.payment.contest.slug,))


class FakePaymentView(PaymentView):
    form_class = FakePaymentForm

    def form_valid(self, form):
        if form.cleaned_data.get("payment_successful", "") == "yes":
            self.payment.entries.update(is_paid=True)
            self.payment.status = Payment.PaymentStatus.OK
        else:
            self.payment.status = Payment.PaymentStatus.FAILED
        self.payment.save()
        return super().form_valid(form)


class TransferPaymentView(PaymentView):
    form_class = BlankForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["head_info"] = mark_safe(self.payment.contest.payment_transfer_info)
        return kwargs

    def form_valid(self, form):
        self.payment.status = Payment.PaymentStatus.AWAITING
        self.payment.save()
        messages.success(
            self.request,
            _("We are awaiting your payment. Once it is received we will notify you."),
        )
        return super().form_valid(form)


class PayUPaymentView(PaymentView):

    def get(self, request, *args, **kwargs):
        payu_url = payu.get_order_link(
            payment=self.payment,
            ip=get_client_ip(request),
            next_url=request.build_absolute_uri(
                reverse(
                    "contest:payment_payu_redirect", args=(self.payment.contest.slug,)
                )
            ),
            notify_url=request.build_absolute_uri(
                reverse("contest:payment_payu_notification", args=(self.payment.id,))
            ).replace("http", "https"),
        )
        return redirect(payu_url)


class PayUPaymentRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.GET.get("error") == "501":
            messages.warning(self.request, _("Payment failed"))
        else:
            messages.success(
                self.request,
                _(
                    "Status of your entries will be updated upon receiving confirmation from PayU"
                ),
            )
        return reverse("contest:add_entry_contest", args=(self.kwargs["contest_slug"],))


@method_decorator(csrf_exempt, name="dispatch")
class PayUNotificationView(View):
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        # async calls - if payment already completed, then ignore
        if payment.status == Payment.PaymentStatus.OK:
            return HttpResponse(status=200)
        data = json.loads(request.body)

        # check if order in body matches order in URL, also amount and currency in payment matches
        order = data.get("order", {})
        if (
            order.get("orderId") != payment.code
            or float(order.get("totalAmount")) != float(payment.amount)
            or order.get("currencyCode") != payment.currency
        ):
            return HttpResponse(status=404)

        status = order.get("status")
        status_mapping = {
            "PENDING": Payment.PaymentStatus.AWAITING,
            "COMPLETED": Payment.PaymentStatus.OK,
            "CANCELED": Payment.PaymentStatus.FAILED,
        }
        if not status or status not in status_mapping.keys():
            return HttpResponse(status=404)

        payment.status = status_mapping.get(status)
        payment.save()

        return HttpResponse("OK")


class PayPalDispatchView(PaymentView):
    template_name = "contest/paypal_dispatch.html"

    def get_form(self, form_class=None):
        paypal_data = {
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": self.payment.amount,
            "item_name": f"{self.payment.contest.title} - {_('Entries')}: "
            f"{[entry.code for entry in self.payment.entries.all()]}",
            "invoice": self.payment.id,
            "currency_code": self.payment.currency,
            # 'charset': 'UTF-8',
            "notify_url": self.request.build_absolute_uri(reverse("paypal-ipn")),
            "return_url": self.request.build_absolute_uri(
                reverse("contest:payment_paypal_success", args=(self.payment.id,))
            ),
            "cancel_url": self.request.build_absolute_uri(
                reverse("contest:payment_paypal_failure", args=(self.payment.id,))
            ),
        }
        return PayPalPaymentsForm(initial=paypal_data)


class PaymentRedirectView(RedirectView):
    def __init__(self, *args, **kwargs):
        self.payment = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.payment = get_object_or_404(Payment, id=self.kwargs["payment_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        return reverse("contest:add_entry_contest", args=(self.payment.contest.slug,))


class PayPalSuccessRedirectView(PaymentRedirectView):

    def get(self, request, *args, **kwargs):
        self.payment.status = Payment.PaymentStatus.OK
        self.payment.save()
        messages.success(self.request, _("Payment successful"))
        return super().get(request, *args, **kwargs)


class PayPalFailureRedirectView(PaymentRedirectView):
    def get(self, request, *args, **kwargs):
        self.payment.status = Payment.PaymentStatus.FAILED
        self.payment.save()
        messages.warning(self.request, _("Payment failed"))
        return super().get(request, *args, **kwargs)


class LabelPrintoutView(LoginRequiredMixin, UserOwnsPackageMixin, TemplateView):
    template_name = "contest/labels.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.package = None

    def dispatch(self, request, *args, **kwargs):
        self.package = get_object_or_404(
            EntriesPackage.objects.select_related("owner"), id=self.kwargs["package_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = Entry.objects.filter(
            id__in=self.package.entries.all()
        ).select_related("category__style")
        context["user"] = self.package.owner
        return context


class PaymentManagementView(CapabilityRequiredMixin, ContestContextMixin, ListView):
    required_capability = Capability.ENTRY_PAYMENTS
    model = Payment

    def get_queryset(self):
        return (
            Payment.pending.filter(contest=self.contest)
            .select_related("user")
            .prefetch_related(
                "entries", "entries__category", "entries__category__style"
            )
        )


class PaymentReceivedView(CapabilityRequiredMixin, ContestContextMixin, DeleteView):
    required_capability = Capability.ENTRY_PAYMENTS

    def get_object(self, queryset=None):
        return get_object_or_404(
            Payment.pending.select_related("user").prefetch_related(
                "entries", "entries__category", "entries__category__style"
            ),
            pk=self.kwargs["pk"],
        )

    def get_success_url(self):
        return reverse("contest:payment_list", args=(self.contest.slug,))

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.status = Payment.PaymentStatus.OK
        self.object.save()
        return HttpResponseRedirect(success_url)


class ContestJudgingEliminationsMixin(ContestPassesTestMixin):

    def test_func(self):
        return self.contest.is_judging_eliminations


class ContestJudgingFinalsMixin(ContestPassesTestMixin):

    def test_func(self):
        return self.contest.is_judging_finals


class ContestJudgingBOSMixin(ContestPassesTestMixin):

    def test_func(self):
        return self.contest.is_judging_bos


class JudgingListView(
    CapabilityRequiredMixin, ContestJudgingEliminationsMixin, ListView
):
    model = Entry
    template_name = "contest/judging_list_by_style.html"
    context_object_name = "entries"
    required_capability = Capability.VIEW_JUDGING_ENTRIES_LIST

    def get_queryset(self):
        return (
            Entry.objects.filter(is_received=True)
            .filter(is_paid=True)
            .filter(category__contest=self.contest)
            .select_related("category__style", "brewer")
            .order_by("category__style__name", "code")
        )


class ScoreSheetView(CapabilityRequiredMixin, ContestContextMixin, DetailView):
    model = ScoreSheet
    required_capability = Capability.VIEW_SCORESHEET


class MyScoreSheetView(DetailView):
    model = ScoreSheet
    template_name = "contest/scoresheet_detail_brewer.html"

    def test_func(self):
        scoresheet = self.get_object()
        # verify if contest already published results
        if not scoresheet.entry.category.contest.show_results:
            return False
        # verify if user owns the entry
        return scoresheet and self.request.user == scoresheet.entry.brewer

    def get_object(self, queryset=None):
        return get_object_or_404(ScoreSheet, entry=self.kwargs["pk"])


class ScoreSheetTableMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        # Get the existing context data from the parent class
        context = super().get_context_data(**kwargs)

        # Labels
        context["appearance_header"] = _("Appearance")
        context["aroma_header"] = _("Aroma")
        context["body_header"] = _("Flavor and Body")
        context["finish_header"] = _("Finish")
        context["overall_header"] = _("Overall Impression")

        # Appearance table
        context["appearance_table"] = [
            {
                "category": _("UNACCEPTABLE"),
                "description": _("Major faults"),
                "points": "0 - 2",
            },
            {
                "category": _("BELOW AVERAGE"),
                "description": _("Serious faults, poor quality"),
                "points": "3 - 4",
            },
            {
                "category": _("AVERAGE"),
                "description": _("Few minor faults"),
                "points": "5 - 6",
            },
            {
                "category": _("GOOD"),
                "description": _("Mainly within style, minor faults"),
                "points": "7 - 8",
            },
            {
                "category": _("VERY GOOD"),
                "description": _("No faults, Mead mostly within style"),
                "points": "9 - 10",
            },
            {
                "category": _("PERFECT"),
                "description": _("Appearance ideal with style"),
                "points": "11 - 12",
            },
        ]

        # Aroma/Bouquet table
        context["aroma_table"] = [
            {
                "category": _("UNACCEPTABLE"),
                "description": _("Repulsing smell, major faults"),
                "points": "0 - 5",
            },
            {
                "category": _("BELOW AVERAGE"),
                "description": _("Serious faults, poor quality"),
                "points": "6 - 10",
            },
            {
                "category": _("AVERAGE"),
                "description": _("Aroma mostly within style, minor faults"),
                "points": "11 - 15",
            },
            {
                "category": _("GOOD"),
                "description": _("Pleasant bouquet mostly within style"),
                "points": "16 - 20",
            },
            {
                "category": _("VERY GOOD"),
                "description": _("Pleasant bouquet within the style"),
                "points": "21 - 24",
            },
            {
                "category": _("PERFECT"),
                "description": _("Complex and pleasant, ideal with style"),
                "points": "25 - 30",
            },
        ]

        # Flavour and Body table
        context["flavor_table"] = [
            {
                "category": _("UNACCEPTABLE"),
                "description": _("Repulsing taste, major faults"),
                "points": "0 - 5",
            },
            {
                "category": _("BELOW AVERAGE"),
                "description": _("Serious faults, poor quality"),
                "points": "6 - 10",
            },
            {
                "category": _("AVERAGE"),
                "description": _("Flavor mostly within the style, minor faults"),
                "points": "11 - 15",
            },
            {
                "category": _("GOOD"),
                "description": _("Pleasant flavor mostly within style"),
                "points": "16 - 20",
            },
            {
                "category": _("VERY GOOD"),
                "description": _("Pleasant flavor within the style"),
                "points": "21 - 26",
            },
            {
                "category": _("PERFECT"),
                "description": _("Complex and pleasant, ideal with style"),
                "points": "27 - 32",
            },
        ]

        # Finish table
        context["finish_table"] = [
            {
                "category": _("UNACCEPTABLE"),
                "description": _("Repulsing aftertaste"),
                "points": "0 - 2",
            },
            {
                "category": _("BELOW AVERAGE"),
                "description": _("No finish and/or bad aftertaste"),
                "points": "3 - 4",
            },
            {
                "category": _("AVERAGE"),
                "description": _("Short finish with neutral aftertaste"),
                "points": "5 - 6",
            },
            {
                "category": _("GOOD"),
                "description": _("Medium finish with pleasant aftertaste"),
                "points": "7 - 8",
            },
            {
                "category": _("VERY GOOD"),
                "description": _("Medium/long finish, pleasant aftertaste"),
                "points": "9 - 11",
            },
            {
                "category": _("PERFECT"),
                "description": _("Long and pleasant finish and aftertaste"),
                "points": "12 - 14",
            },
        ]

        # Overall Impression table
        context["overall_table"] = [
            {
                "category": _("UNACCEPTABLE"),
                "description": _("Major faults and/or style differences"),
                "points": "0 - 2",
            },
            {
                "category": _("BELOW AVERAGE"),
                "description": _("Serious faults, poor quality"),
                "points": "3 - 4",
            },
            {
                "category": _("AVERAGE"),
                "description": _("Mead mostly within the style, minor faults"),
                "points": "5 - 6",
            },
            {
                "category": _("GOOD"),
                "description": _("Most of the attributes within the style"),
                "points": "7 - 8",
            },
            {
                "category": _("VERY GOOD"),
                "description": _("No faults, Mead mostly within the style"),
                "points": "9 - 10",
            },
            {
                "category": _("PERFECT"),
                "description": _("Mead ideal with the style"),
                "points": "11 - 12",
            },
        ]

        return context


class ScoreSheetEdit(
    ContestJudgingEliminationsMixin,
    CapabilityRequiredMixin,
    ScoreSheetTableMixin,
    UpdateView,
):
    model = ScoreSheet
    form_class = ScoreSheetForm
    required_capability = Capability.EDIT_SCORESHEET

    def get_success_url(self):
        return reverse(
            "contest:scoresheet_view",
            args=(
                self.contest.slug,
                self.object.id,
            ),
        )


class ScoreSheetCreate(
    ContestJudgingEliminationsMixin,
    CapabilityRequiredMixin,
    ScoreSheetTableMixin,
    CreateView,
):
    model = ScoreSheet
    form_class = ScoreSheetForm
    required_capability = Capability.EDIT_SCORESHEET

    def form_valid(self, form):
        entry = get_object_or_404(Entry, pk=self.kwargs["entry"])
        existing = ScoreSheet.objects.filter(entry=entry).first()
        if existing:
            # Redirect silently instead of creating
            self.object = existing
            return HttpResponseRedirect(self.get_success_url())
        form.instance.entry = entry
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "contest:scoresheet_view",
            args=(
                self.contest.slug,
                self.object.id,
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scoresheet"] = {
            "entry": get_object_or_404(Entry, pk=self.kwargs["entry"])
        }
        return context


class MedalsListView(ListView, ContestContextMixin):
    template_name = "contest/medal_list_by_style.html"
    context_object_name = "entries"

    def __init__(self, *args, **kwargs):
        self.contest = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return (
            Entry.objects.filter(category__contest=self.contest)
            # .filter(scoresheets__has_medal=True)
            # .distinct()
            .filter(place__gt=0)
            .order_by("category__style__name", "brewer")
            .select_related("brewer", "category__style")
            .prefetch_related("scoresheets")
        )

    def dispatch(self, request, *args, **kwargs):
        self.contest = Contest.objects.prefetch_related("bos_entry").get(
            slug=self.kwargs["contest_slug"]
        )
        if not (self.contest and self.contest.show_results):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["best_of_show"] = self.contest.bos_entry
        return context


class PrivacyView(TemplateView):
    template_name = "contest/privacy_en.html"

    def get_template_names(self):
        current_language = get_language()
        if current_language == "pl":
            return ["contest/privacy_pl.html"]

        return [self.template_name]


class PartnersGalleryView(TemplateView):
    template_name = "contest/partners_gallery_template.html"
    items_per_row = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Parameters
        images_path = os.path.join("contest", "partners")
        context["max_width"] = 150
        context["max_height"] = 150

        # Path to the static/partners directory
        app_static_path = os.path.join(
            settings.BASE_DIR, "contest", "static", images_path
        )
        collectstatic_path = os.path.join(settings.STATIC_ROOT, images_path)
        # Prefer collectstatic location if it exists (i.e. in prod)
        images_dir = (
            collectstatic_path if os.path.isdir(collectstatic_path) else app_static_path
        )

        # List all valid image files (e.g., jpg, png, gif, etc.)
        valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        images = [
            f for f in os.listdir(images_dir) if f.lower().endswith(valid_extensions)
        ]
        images = sorted(images)
        # Construct the URLs for the static images
        image_urls = [
            os.path.join(settings.STATIC_URL, images_path, img) for img in images
        ]

        # Add the image URLs to the context
        context["image_urls"] = image_urls
        context["items_per_row"] = self.items_per_row

        return context


class JudgingFinalsListView(
    CapabilityRequiredMixin, ContestJudgingFinalsMixin, ListView
):
    template_name = "contest/judging_finals_list.html"
    context_object_name = "categories"
    required_capability = Capability.JUDGE_FINALS

    def get_queryset(self):
        categories = (
            Category.objects.filter(contest__slug=self.kwargs["slug"])
            .annotate(
                finals_count=Count(
                    Case(
                        When(entries__scoresheets__final_round=True, then=1),
                        output_field=IntegerField(),
                    )
                ),
                entries_delivered=Count(
                    Case(
                        When(entries__is_paid=True, entries__is_received=True, then=1),
                        output_field=IntegerField(),
                    )
                ),
            )
            .prefetch_related(
                Prefetch(
                    "entries",
                    queryset=Entry.objects.filter(place__gt=0).order_by("place"),
                    to_attr="winning_entries",
                )
            )
        )
        return categories


class JudgingFinalsCategoryView(
    CapabilityRequiredMixin, ContestJudgingFinalsMixin, UpdateView
):
    template_name = "contest/judging_finals_category.html"
    required_capability = Capability.JUDGE_FINALS

    def get_success_url(self):
        return reverse("contest:judging_finals_list", args=(self.kwargs["slug"],))

    def get_queryset(self):
        finals = Category.objects.get(id=self.kwargs["category_id"]).entries_in_final
        return Entry.objects.filter(id__in=finals)

    def get_context(self):
        context = {
            "formset": FinalEntriesFormset(queryset=self.get_queryset()),
            "style": Category.objects.get(id=self.kwargs["category_id"]).style.name,
            "contest": self.contest,
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context())

    def post(self, request, *args, **kwargs):
        formset = FinalEntriesFormset(request.POST, queryset=self.get_queryset())

        if formset.is_valid():
            formset.save()
            return redirect(self.get_success_url())  # Replace with your success URL
        return render(request, self.template_name, self.get_context())

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            _("Final round results saved for category: ")
            + Category.objects.get(id=self.kwargs["category_id"]).style.name,
        )

        return response


class JudgeBosView(CapabilityRequiredMixin, ContestJudgingBOSMixin, ListView):
    required_capability = Capability.JUDGE_BOS
    context_object_name = "entries"
    template_name = "contest/judging_bos_list.html"

    def get_queryset(self):
        queryset = (
            Entry.objects.filter(category__contest=self.contest)
            .filter(place=1)
            .order_by("category__style__name")
            .select_related("category__style")
        )
        logger.debug(f"JudgeBossView:\n{queryset.values()}")
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["best_of_show"] = self.contest.bos_entry
        context["contest"] = self.contest
        return context


class JudgeBosSelect(CapabilityRequiredMixin, ContestJudgingBOSMixin, UpdateView):
    required_capability = Capability.JUDGE_BOS
    model = Contest
    form_class = ContestBestOfShowForm
    template_name = "contest/judging_bos_selection.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        contest = self.contest
        candidates = (
            Entry.objects.filter(category__contest=contest)
            .filter(place=1)
            .order_by("category__style__name")
            .select_related("category__style")
        )
        kwargs["candidates"] = candidates
        logger.debug(
            "JudgeBosSelect: candidates:\n{candidates}".format(candidates=candidates)
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contest"] = self.get_object()
        return context

    def get_success_url(self):
        return reverse(
            "contest:judging_bos_view", kwargs={"slug": self.get_object().slug}
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Best Of Show saved"))
        return response
