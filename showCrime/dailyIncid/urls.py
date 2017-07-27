from django.conf.urls import url

from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

	url(r'^need2login/.*$', views.need2login, name='need2login'),

	url(r'^login/$', auth_views.login, name='login'),
	url(r'^logout$', auth_views.logout, {'next_page':'index'}, name='logout',),

	# first interface
	url(r'^query/$', views.getQuery, name='query'),
	url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+).png$', views.plotResults, name='plotResults' ),
	url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+)\+(?P<crimeCat2>[\w_-]+).png$', views.plotResults, name='plotResult2' ),

	url(r'nearheremz/$', views.nearHereMZ, name='nearheremz'),
	
	url(r'choosePlace-(?P<ptype>\w+)/$', views.choosePlace, name='choosePlace'),
	
	# misc queries

	url(r'^otherUtil$', views.otherUtil, name='otherUtil'),
	url(r'^addZip$', views.add_zip, name='addZip'),
	url(r'^tstBART$', views.tstAllFile, name='tstFile'),
	## Obsolete
	url(r'^addGeo$', views.add_geo, name='addGeo'),
	
	# DRF/API
	url(r'beatAPI/(?P<beat>.+)/$', views.BeatAPI.as_view(), name='beatlist'),
	url(r'nearHereAPI/(?P<lng>.+)_(?P<lat>.+)/$', views.NearHereAPI.as_view(), name='nearhereapi'),
	url(r'crimeCatAPI/(?P<cc>.+)/$', views.CrimeCatAPI.as_view(), name='crimecatapi'),
	

	url(r'^testPage$', views.testPage, name='testPage'),
	

]
