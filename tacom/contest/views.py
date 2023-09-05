from datetime import date

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Count
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, TemplateView, UpdateView, DetailView, CreateView

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


class AddEntryStyleListView(LoginRequiredMixin, ListView):
    """
    Allows selection of the style, to which user wants to register.
    Contest has been already chosen (and is passed via url slug)
    """

    template_name = 'contest/add_entry_style_list.html'
    context_object_name = 'styles'

    def get(self, request, *args, **kwargs):
        contest = Contest.objects.get(slug=self.kwargs['slug'])
        if contest.registration_date_to < date.today() or contest.registration_date_from > date.today():
            messages.error(
                self.request,
                _('This contest does not allow registration as of today')
            )

            return redirect('contest:add_entry')
        else:
            return super().get(request, *args, **kwargs)

    def get_queryset(self):
        # TODO: cache Contest object?
        contest = Contest.objects.get(slug=self.kwargs['slug'])
        return (Style.objects
                .filter(categories__in=Category.objects.filter(contest=contest)
                # .filter(categories__in=categories_not_full)
                # TODO: filter out categories in which user reached entries_limit
                ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contest'] = Contest.objects.get(slug=self.kwargs['slug'])
        context['entries'] = (Entry.objects
                              .filter(brewer=self.request.user)
                              .filter(category__contest=context['contest']))
        return context


class AddEntryView(LoginRequiredMixin, CreateView):
    model = Entry
    template_name = 'contest/add_entry.html'
    form_class = NewEntryForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contest'] = Contest.objects.get(slug=self.kwargs['slug'])
        context['entries'] = (Entry.objects
                              .filter(brewer=self.request.user)
                              .filter(category__contest=context['contest']))

        context['style'] = Category.objects.get(id=self.kwargs['pk']).style
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        category = Category.objects.get(id=self.kwargs['pk'])
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


class ContestDetailView(DetailView):
    model = Contest
    # queryset = Contest.objects.prefetch_related('categories__style')  # 2 queries
    queryset = Contest.objects.prefetch_related(
        Prefetch('categories', queryset=Category.objects.select_related('style'))
    )  # 1 query


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'contest/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entries'] = Entry.objects.filter(brewer=self.request.user)
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
