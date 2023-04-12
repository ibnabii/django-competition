from django.contrib import admin

from .models import Contest

class ContestAdmin(admin.ModelAdmin):
    model = Contest

admin.site.register(Contest, ContestAdmin)
