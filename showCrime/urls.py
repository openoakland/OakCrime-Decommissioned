from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from rest_framework import routers

from dailyIncid import views

urlpatterns = [
    url(r'^$', views.index, name='showCrimeIndex'),
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^dailyIncid/', include('dailyIncid.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
