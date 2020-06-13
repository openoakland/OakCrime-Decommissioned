from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^need2login/.*$', views.need2login, name='need2login'),
    url(r'^vaporWare/.*$', views.vaporWare, name='vaporWare'),

    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout$', auth_views.logout, {'next_page': 'index'}, name='logout', ),

	url(r'^djga/', include('google_analytics.urls')),

    # first interface
    url(r'^query/$', views.getQuery, name='query'),
    url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+).png$', views.plotResults, name='plotResults'),
    url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+)\+(?P<crimeCat2>[\w_-]+).png$', views.plotResults,
        name='plotResult2'),

    url(r'nearhere/$', views.nearHere, name='nearhere'),

    url(r'choosePlace-(?P<ptype>\w+)/$', views.choosePlace, name='choosePlace'),

    # doc pages

    # url(r'^doc/$', TemplateView.as_view(template_name="dailyIncid/doc.html")),
    # 170901: add most recent addition stats
    url(r'^doc/$', views.docView, name='docView'),
    url(r'^interface/$', TemplateView.as_view(template_name="dailyIncid/interface.html")),
    url(r'^faq/$', TemplateView.as_view(template_name="dailyIncid/faq.html")),

    url(r'heatmap/$', views.heatmap, name='heatmap'),
    url(r'heatmap/(?P<mapType>.+)/$', views.heatmap, name='heatmapTyped'),

    # NB: params not part of url!?
    url(r'hybridQual/(?P<mapType>.+)/$', views.hybridQual, name='hybridQual'),

    # url(r'getNCPC/$', views.getBeat, name='getBeat'),
    # url(r'ncpc2/$', views.bldNCPCRpt2, name='ncpc'),
    # url(r'downloadNCPC/(?P<beat>[0-9XY+]+)_(?P<minDateDigit>[0-9]+)_(?P<maxDateDigit>[0-9]+)/$', views.downloadNCPC,
    #     name='downloadNCPC'),

    url(r'incidRpt/(?P<opd_rd>.+)/$', views.incidRpt, name='incidRpt'),

    # DRF/API
    url(r'beatAPI/(?P<beat>.+)/$', views.BeatAPI.as_view(), name='beatlist'),
    url(r'nearHereAPI/(?P<lng>.+)_(?P<lat>.+)/$', views.NearHereAPI.as_view(), name='nearhereapi'),
    url(r'crimeCatAPI/(?P<cc>.+)/$', views.CrimeCatAPI.as_view(), name='crimecatapi'),

    url(r'^testPage$', views.testPage, name='testPage'),
]
