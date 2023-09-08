from datetime import date

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count, F
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, TemplateView, UpdateView, DetailView, CreateView
from django.views.generic.base import ContextMixin

from .forms import NewEntryForm
from .models import Contest, Category, Style, Entry


class PublishedContestListView(ListView):
    ordering = ['-judging_date_from']
    queryset = Contest.objects.filter(competition_is_published=True)
    template_name = 'contest/contest_list.html'

    def get(self, *args, **kwargs):
        if self.queryset.count() == 1:
            return redirect('contest:contest_detail', slug=self.queryset.first().slug)
        return super().get(*args, **kwargs)


class AddEntryContestListView(LoginRequiredMixin, ListView):
    """
    Allows selection of the contest, which user wants to register
    """
    ordering = ['-registration_date_to']
    queryset = (Contest.objects
                .filter(registration_date_from__lte=date.today())
                .filter(registration_date_to__gte=date.today()))
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
        self.contest = get_object_or_404(Contest, slug=self.kwargs['slug'])
        if self.contest.registration_date_to < date.today() or self.contest.registration_date_from > date.today():
            messages.error(
                request,
                _('This contest does not allow registration as of today')
            )
            return redirect('contest:add_entry')
        else:
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
    Allows selection of the style, to which user wants to register.
    Contest has been already chosen (and is passed via url slug)
    """

    template_name = 'contest/add_entry_style_list.html'
    context_object_name = 'styles'

    def get_queryset(self):
        full_categories = (Entry.objects
                           .filter(brewer=self.request.user)
                           # .select_related('category')
                           .filter(category__contest=self.contest)
                           .values('category', 'category__entries_limit')
                           .annotate(cnt=Count('id'))
                           .filter(cnt__gte=F('category__entries_limit'))
                           .values_list('category_id', flat=True)
                           )
        return (Style.objects
                .filter(categories__in=Category.objects.filter(contest=self.contest))
                .exclude(categories__id__in=full_categories)

                )


class AddEntryView(LoginRequiredMixin, ContestAcceptsRegistration, CreateView):
    model = Entry
    template_name = 'contest/add_entry.html'
    form_class = NewEntryForm

    def post(self, request, *args, **kwargs):
        # save contest
        self.contest = get_object_or_404(
            Contest,
            slug=self.kwargs['slug']
        )
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['style'] = get_object_or_404(Category.objects.select_related('style'), id=self.kwargs['pk']).style
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        category = get_object_or_404(Category.objects.select_related('style'), id=self.kwargs['pk'])
        # Category.objects.get(id=self.kwargs['pk'])
        form_kwargs['is_extra_mandatory'] = category.style.extra_info_is_required
        form_kwargs['extra_hint'] = category.style.extra_info_hint
        form_kwargs['user'] = self.request.user
        form_kwargs['category'] = category
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


class ContestDetailView(DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    queryset = Contest.objects.filter(competition_is_published=True).prefetch_related(
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
