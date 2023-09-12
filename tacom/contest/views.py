from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import redirect, get_object_or_404, Http404
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, TemplateView, UpdateView, DetailView, CreateView, DeleteView
from django.views.generic.base import ContextMixin

from .forms import NewEntryForm
from .models import Contest, Category, Entry


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


class AddEntryStyleListView(LoginRequiredMixin, ContestAcceptsRegistration, ListView):
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


class AddEntryView(LoginRequiredMixin, CreateView):
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
            super().handle_no_permission()
        except PermissionDenied:
            raise Http404


class DeleteEntryView(UserPassesTestMixin, DeleteView):
    model = Entry
    # template_name = 'contest/entry_confirm_delete.html'
    context_object_name = 'entry'

    def test_func(self):
        return self.get_object().brewer == self.request.user and self.get_object().can_be_deleted()

    def form_valid(self, form):
        messages.success(
            self.request,
            _('Entry has been deleted')
        )

        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.POST.get('next')
        if next_url:
            return next_url
        else:
            return reverse('contest:add_entry_contest', kwargs={'slug': self.object.category.contest.slug})

    def handle_no_permission(self):
        """
        Override method to rise 404 instead of 403
        """
        try:
            super().handle_no_permission()
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
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'contest/generic_update.html'
    fields = [
        'username',
        'first_name',
        'last_name',
    ]
    success_url = reverse_lazy('contest:profile')

    def get_object(self, queryset=None):
        return self.request.user
