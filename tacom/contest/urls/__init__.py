from .urls import urlpatterns as legacy_patterns
from .general import urlpatterns as general_patterns
from .contest import urlpatterns as contest_patterns

app_name = "contest"

urlpatterns = [
    *legacy_patterns,
    *general_patterns,
    *contest_patterns,
]
