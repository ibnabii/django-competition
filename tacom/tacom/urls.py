from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include, reverse
from django.views.generic import RedirectView

urlpatterns = i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('contest/', include('contest.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('tinymce/', include('tinymce.urls')),
    path('', RedirectView.as_view(url='/contest'), name='home')
)
