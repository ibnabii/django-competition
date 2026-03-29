from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView

from contest.models import Entry, Contest
from contest.permissions.capabilities import Capability
from contest.permissions.mixins import CapabilityRequiredMixin
from contest.views import ContestContextMixin


class EntriesListView(ContestContextMixin, CapabilityRequiredMixin, ListView):
    context_object_name = "entries"
    required_capability = Capability.ENTRY_ENCODE
    template_name = "contest/entry_coding_page.html"

    def get_queryset(self):
        qs = (
            Entry.objects.filter(category__contest=self.contest)
            .order_by("code")
            .select_related("category", "category__style")
        )
        return qs

    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist("selected_entries")

        if not selected_ids:
            messages.warning(request, "No entries selected.")
            return redirect(request.path)

        entries = Entry.objects.filter(id__in=selected_ids)

        # --- BOILERPLATE START ---
        for entry in entries:
            entry.secret_code = entry.generate_secret_code()
            entry.save()

        # --- BOILERPLATE END ---

        messages.success(request, f"{entries.count()} entries processed.")
        return redirect(request.path)


class EntriesListViewPrintable(EntriesListView):
    template_name = "contest/entry_coding_page_print.html"

    def get_queryset(self):
        ALLOWED_SORTS = {"code", "-code", "secret_code", "-secret_code", "category"}

        sort_by = self.request.GET.get("sort_by", "code")
        if sort_by not in ALLOWED_SORTS:
            sort_by = "code"
        if sort_by == "category":
            sort_by = "category__style__name"

        qs = (
            Entry.objects.filter(category__contest=self.contest)
            .order_by(sort_by)
            .select_related("category", "category__style")
        )
        return qs


class EntryNewCodeView(ContestContextMixin, CapabilityRequiredMixin, DetailView):
    model = Entry
    required_capability = Capability.ENTRY_ENCODE
    template_name = "contest/entries_coding/_entry_item.html"
    context_object_name = "entry"
    pk_url_kwarg = "entry_id"

    def get_queryset(self):
        qs = (
            Entry.objects.filter(category__contest=self.contest)
            .order_by("code")
            .select_related("category", "category__style")
        )
        return qs

    def post(self, request, *args, **kwargs):
        from string import ascii_uppercase

        entry = self.get_object()
        new_code = request.POST.get("new_code")
        # set code if it's valid
        if new_code:
            new_code = new_code.upper()
            print(
                list(
                    self.model.objects.filter(
                        secret_code=new_code, category__contest=self.contest
                    ).all()
                )
            )
            if (
                all(letter in ascii_uppercase for letter in new_code)
                and len(new_code) == 4
                and not self.model.objects.filter(
                    secret_code=new_code, category__contest=self.contest
                ).exists()
            ):
                entry.secret_code = new_code
            else:
                return self.get(request, *args, **kwargs)

        # or generate a new one
        else:
            entry.secret_code = entry.generate_secret_code()

        entry.save()
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nr"] = self.request.POST.get("nr")
        return context
