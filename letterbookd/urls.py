from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _


def home(request):
    return HttpResponse(_("Bienvenue sur letterbookd."))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
]
