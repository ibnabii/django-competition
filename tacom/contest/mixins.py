class NextUrlMixin:
    def get_next_url(self):
        return (
            self.request.headers.get("HX-Current-URL") or self.request.get_full_path()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next_url"] = self.get_next_url()
        return context
