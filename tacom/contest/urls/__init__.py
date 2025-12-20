from .contest import urlpatterns as contest_patterns
from .general import urlpatterns as general_patterns
from .judges import urlpatterns as judges_patterns
from .urls import urlpatterns as legacy_patterns

app_name = "contest"

urlpatterns = [*legacy_patterns, *general_patterns, *contest_patterns, *judges_patterns]
