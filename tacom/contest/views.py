import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404, Http404
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    ListView, TemplateView, UpdateView, DetailView, CreateView, DeleteView, FormView, RedirectView, View
)
from django.views.generic.base import ContextMixin

from .forms import NewEntryForm, ProfileForm, NewPackageForm, NewPaymentForm, FakePaymentForm, BlankPaymentForm
from .models import Contest, Category, Entry, User, EntriesPackage, Payment
from .utils import get_client_ip
from . import payu


class PublishedContestListView(ListView):
    ordering = ['-judging_date_from']
    queryset = Contest.published
    template_name = 'contest/contest_list.html'

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect('contest:contest_detail', slug=self.queryset.first().slug)
        return super().get(*args, **kwargs)


class AddEntryContestListView(ListView):
    """
    Allows selection of the contest, which user wants to register
    """
    ordering = ['-registration_date_to']
    queryset = Contest.registrable

    template_name = 'contest/add_entry_contest_list.html'


class ContestAcceptsRegistration(ContextMixin):
    """
    This adds Contest and user's Entries in this Contest to context.
    Also adds validation if contest accepts registration at the moment.
    ContextMixin is the base class, as this is the class in the views hierarchy that:
    1. Adds get_context_data method
    2. Is the 'youngest' common ancestor for ListView and CreateView (which are view classes used in the process)
    """

    def __init__(self):
        super().__init__()
        self.contest = None

    def get(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest.registrable, slug=self.kwargs['slug'])
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contest'] = self.contest
        context['entries'] = (Entry.objects
                              .filter(brewer=self.request.user)
                              .filter(category__contest=context['contest'])
                              .select_related('category__style', 'category__contest')
                              )
        return context


class UserFullProfileMixin(UserPassesTestMixin):
    """
    Class redirects user to fill in the profile if he hasn't done so yet
    """

    def test_func(self):
        return self.request.user.profile_complete

    def handle_no_permission(self):
        messages.warning(
            self.request,
            _('Complete your profile, please.')
        )
        return redirect('contest:profile_edit')


class AddEntryStyleListView(LoginRequiredMixin, UserFullProfileMixin, ContestAcceptsRegistration, ListView):
    """
    Allows selection of the Style (via Category), to which user wants to register.
    Contest has been already chosen (and is passed via url slug)
    """

    template_name = 'contest/add_entry_style_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return (Category.objects
                .not_full(self.request.user)
                .filter(contest=self.contest)
                .select_related('style')
                .order_by('style__name')
                )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_limit_left = self.contest.user_limit_left(self.request.user)
        contest_limit_left = self.contest.global_limit_left
        context['user_limit_left'] = user_limit_left
        context['contest_limit_left'] = contest_limit_left
        context['can_add'] = (
                (user_limit_left is None or user_limit_left > 0)
                and
                (contest_limit_left is None or contest_limit_left > 0)
        )
        if not context['can_add']:
            if user_limit_left is not None and user_limit_left <= 0:
                context['limit_exhausted_info'] = (
                    _("You have reached the limit of entries allowed per participant.")
                )
            else:
                context['limit_exhausted_info'] = (
                    _("This competition has reached it's entries limit.")
                )
        return context


class AddEntryView(LoginRequiredMixin, UserFullProfileMixin, CreateView):
    model = Entry
    template_name = 'contest/add_entry.html'
    form_class = NewEntryForm

    def __init__(self):
        self.category = None
        self.contest = None
        self.style = None
        super().__init__()

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category.objects.select_related('contest', 'style'), pk=kwargs['pk'])
        self.contest = self.category.contest
        self.style = self.category.style
        if not self.contest.is_registrable():
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['style'] = self.style
        context['contest'] = self.contest
        context['entries'] = (Entry.objects
                              .filter(brewer=self.request.user)
                              .filter(category__contest=context['contest'])
                              .select_related('category__style', 'category__contest')
                              )
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['is_extra_mandatory'] = self.category.style.extra_info_is_required
        form_kwargs['extra_hint'] = self.category.style.extra_info_hint
        form_kwargs['user'] = self.request.user
        form_kwargs['category'] = self.category
        return form_kwargs

    def get_success_url(self):
        messages.success(
            self.request,
            _('Entry has been added successfully')
        )
        return reverse('contest:add_entry_contest', kwargs={'slug': self.object.category.contest.slug})

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, error=True)
        )


class EditEntryView(UserPassesTestMixin, UpdateView):
    model = Entry
    template_name = 'contest/generic_update.html'
    form_class = NewEntryForm

    def test_func(self):
        return self.get_object().brewer == self.request.user and self.get_object().can_be_edited()

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        category = self.get_object().category
        form_kwargs['is_extra_mandatory'] = category.style.extra_info_is_required
        form_kwargs['extra_hint'] = category.style.extra_info_hint
        form_kwargs['user'] = self.request.user
        form_kwargs['category'] = category
        return form_kwargs

    def get_success_url(self):
        next_url = self.request.POST.get('next')
        messages.success(
            self.request,
            _('Entry has been updated successfully')
        )
        if next_url:
            return next_url
        else:
            return reverse('contest:add_entry_contest', kwargs={'slug': self.object.category.contest.slug})

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
    context_object_name = 'entry'

    def get_queryset(self):
        return super().get_queryset().select_related('brewer', 'category')

    def get_object(self, queryset=None):
        return self.object_cached

    @cached_property
    def object_cached(self):
        return super().get_object()

    def test_func(self):
        entry = self.get_object()
        return entry.brewer == self.request.user and entry.can_be_deleted()

    def form_valid(self, form):
        messages.success(
            self.request,
            _('Entry has been deleted')
        )

        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        print(next_url)
        if next_url:
            return next_url
        else:
            return reverse_lazy('contest:add_entry_contest', kwargs={'slug': self.object.category.contest.slug})

    def handle_no_permission(self):
        """
        Override method to rise 404 instead of 403
        """

        try:
            return super().handle_no_permission()
        except PermissionDenied:
            raise Http404


class ContestDetailView(DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    queryset = Contest.published.prefetch_related(
        Prefetch('categories', queryset=Category.objects.select_related('style'))
    )  # 1 query


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'contest/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entries'] = (Entry.objects
                              .filter(brewer=self.request.user)
                              .select_related('category__contest', 'category__style')
                              )
        contest = Contest.registrable
        context['is_one_contest'] = Contest.registrable.count() == 1
        if context['is_one_contest']:
            context['contest'] = Contest.registrable.first()
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'contest/generic_update.html'
    form_class = ProfileForm
    success_url = reverse_lazy('contest:profile')

    def get_object(self, queryset=None):
        return self.request.user


class ContestDeliveryAddressView(DetailView):
    model = Contest
    template_name = 'contest/contest_delivery_addr.html'
    queryset = Contest.published


class AddPackageView(LoginRequiredMixin, UserFullProfileMixin, CreateView):
    model = EntriesPackage
    template_name = 'contest/package_update.html'
    success_url = reverse_lazy('contest:profile')
    form_class = NewPackageForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.owner = None
        self.contest = None

    def get_form_kwargs(self):
        self.owner = self.request.user
        self.contest = Contest.objects.get(slug=self.kwargs['slug'])
        kwargs = super().get_form_kwargs()
        kwargs['entries'] = (Entry.objects
                             .filter(category__contest=self.contest)
                             .filter(brewer=self.owner)
                             )
        kwargs['purpose'] = ''
        kwargs['owner'] = self.owner
        kwargs['contest'] = self.contest
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.owner
        form.instance.contest = self.contest
        return super().form_valid(form)


class AddPackageForPayment(AddPackageView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entries'] = kwargs['entries'].filter(is_paid=False)
        kwargs['purpose'] = _('for payment')
        return kwargs

    def get_success_url(self):
        return reverse('contest:payment_method_selection', kwargs={
            'slug': self.contest.slug,
            'package_id': self.object.id
        })


class UserOwnsPackageMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user == get_object_or_404(EntriesPackage, id=self.kwargs['package_id']).owner

    def handle_no_permission(self):
        raise Http404


class SelectPaymentMethodView(LoginRequiredMixin, UserOwnsPackageMixin, CreateView):
    model = Payment
    form_class = NewPaymentForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.package = None

    def dispatch(self, request, *args, **kwargs):
        self.package = get_object_or_404(EntriesPackage, id=self.kwargs['package_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['contest'] = self.package.contest
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.package.owner
        form.instance.contest = self.package.contest
        form.instance.amount = self.package.contest.entry_fee_amount * self.package.entries.count()
        form.instance.currency = self.package.contest.entry_fee_currency
        return super().form_valid(form)

    def get_success_url(self):
        # first add entries
        for entry in self.package.entries.all():
            self.object.entries.add(entry)
        # delete package as it's not needed anymore
        self.package.delete()

        # decide what to do next
        if self.object.method.code == 'fake':
            return reverse('contest:payment_fake', args=(self.object.id,))
        if self.object.method.code == 'transfer':
            return reverse('contest:payment_transfer', args=(self.object.id,))
        if self.object.method.code == 'payu':
            return reverse('contest:payment_payu', args=(self.object.id,))


class PaymentView(LoginRequiredMixin, FormView):
    template_name = 'contest/generic_update.html'

    def __init__(self, *args, **kwargs):
        self.payment = None
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.payment = get_object_or_404(Payment, id=self.kwargs['payment_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['return_url'] = reverse('contest:add_entry_contest', args=(self.payment.contest.slug,))
        return kwargs

    def get_success_url(self):
        return reverse('contest:add_entry_contest', args=(self.payment.contest.slug,))


class FakePaymentView(PaymentView):
    form_class = FakePaymentForm

    def form_valid(self, form):
        if form.cleaned_data.get('payment_successful', '') == 'yes':
            self.payment.entries.update(is_paid=True)
            self.payment.status = Payment.PaymentStatus.OK
        else:
            self.payment.status = Payment.PaymentStatus.FAILED
        self.payment.save()
        return super().form_valid(form)


class TransferPaymentView(PaymentView):
    form_class = BlankPaymentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['head_info'] = mark_safe(self.payment.contest.payment_transfer_info)
        return kwargs

    def form_valid(self, form):
        self.payment.status = Payment.PaymentStatus.AWAITING
        self.payment.save()
        return super().form_valid(form)


class PayUPaymentView(PaymentView):

    def get(self, request, *args, **kwargs):
        payu_url = payu.get_order_link(
            payment=self.payment,
            ip=get_client_ip(request)
            next_url=request.build_absolute_uri(
                reverse('contest:payment_payu_redirect', args=(self.payment.contest.slug,))
            ),
            notify_url=request.build_absolute_uri(
                reverse('contest:payment_payu_notification', args=(self.payment.id,))
            )
        )
        return redirect(payu_url)


class PayUPaymentRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.GET.get('error') == '501':
            messages.warning(
                self.request,
                _('Payment failed')
            )
        else:
            messages.success(
                self.request,
                _('Status of your entries will be updated upon receiving confirmation from PayU')
            )
        return reverse('contest:add_entry_contest', args=(self.kwargs['contest_slug'],))


@method_decorator(csrf_exempt, name='dispatch')
class PayUNotificationView(View):
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        # async calls - if payment already completed, then ignore
        if payment.status == Payment.PaymentStatus.OK:
            return HttpResponse(status=200)
        data = json.loads(request.body)

        # check if order in body matches order in URL, also amount and currency in payment matches
        order = data.get('order', {})
        if (
            order.get('orderId') != payment.code
            or
            float(order.get('totalAmount')) != float(payment.amount)
            or
            order.get('currencyCode') != payment.currency
        ):
            return HttpResponse(status=404)

        status = order.get('status')
        status_mapping = {
            'PENDING': Payment.PaymentStatus.AWAITING,
            'COMPLETED': Payment.PaymentStatus.OK,
            'CANCELED': Payment.PaymentStatus.FAILED
        }
        if not status or status not in status_mapping.keys():
            return HttpResponse(status=404)

        payment.status = status_mapping.get(status)
        payment.save()

        return HttpResponse('OK')
