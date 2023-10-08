from allauth.account import views as allauth_views
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include, reverse_lazy
from django.views.generic import RedirectView



urlpatterns = i18n_patterns(
    path(
        'accounts/password/change/',
        login_required(
            allauth_views.PasswordChangeView.as_view(
                success_url=reverse_lazy('contest:profile')
            )
        ),
        name='account_change_password'
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('contest/', include('contest.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('tinymce/', include('tinymce.urls')),
    path('rosetta/', include('rosetta.urls')),
    path('', RedirectView.as_view(url='/contest'), name='home')
)

if settings.DEBUG:
    urlpatterns.append(
        path("__debug__/", include("debug_toolbar.urls"))
    )
