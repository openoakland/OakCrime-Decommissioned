from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^testPage$', views.testPage, name='testPage'),
    url(r'^tstImage.JPG$', views.showImage, name='showImage'),
    url(r'^query/$', views.getQuery, name='query'),
    url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+).png$', views.plotResults, name='plotResults' ),
    url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+)\+(?P<crimeCat2>[\w_-]+).png$', views.plotResults, name='plotResult2' ),
]
