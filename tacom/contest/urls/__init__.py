from .access_management import urlpatterns as access_management_patterns
from .contest import urlpatterns as contest_patterns
from .encoding import url_patterns as encoding_patterns
from .entry_registration import url_patterns as entry_registartion_patterns
from .general import urlpatterns as general_patterns
from .judges import urlpatterns as judges_patterns
from .urls import urlpatterns as legacy_patterns


app_name = "contest"

urlpatterns = [
    *legacy_patterns,
    *general_patterns,
    *contest_patterns,
    *judges_patterns,
    *entry_registartion_patterns,
    *access_management_patterns,
    *encoding_patterns,
]
