from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.db.models.lookups import IExact
from django.db import transaction
from django.db import IntegrityError

from .forms import *
from .models import *
from showCrime.settings import PlotPath, SiteURL

import logging
logger = logging.getLogger(__name__)

def index(request):
 	return render(request, 'dailyIncid/index.html')

def testPage(request):
	return HttpResponse("Hello, world. You're at dailyIncid test.")

def need2login(request):
	return render(request, 'dailyIncid/need2login.html', Context({}))

@login_required
def getQuery(request):

	# import pdb; pdb.set_trace()
	if request.method == 'POST':
		qform = twoTypeQ(request.POST)
		if qform.is_valid():
			qryData = qform.cleaned_data
			if qryData['crimeCat2']:
				qurl = '/dailyIncid/plots/%s+%s+%s.png' % (qryData['beat'],qryData['crimeCat'],qryData['crimeCat2'])
			else:
				qurl = '/dailyIncid/plots/%s+%s.png' % (qryData['beat'], qryData['crimeCat']) 
			return HttpResponseRedirect(qurl)
	else:
		qform = twoTypeQ()
		
	return render(request, 'dailyIncid/getQuery.html', {'form': qform, 'siteUrl': SiteURL})
	   
import os

import matplotlib

# Force matplotlib to not use any Xwindows backend.
# changed in webapps/django/lib/python2.7/matplotlib/mpl-data/matplotlibrc

matplotlib.use('Agg')

import pylab as p

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
from datetime import datetime,timedelta,date
import matplotlib.dates as mdates


# 2do:  reconcile djOakData code with c4a
MinYear = 2007
MaxYear = 2017
C4A_date_string = '%y%m%d_%H:%M:%S'


def monthIdx(cdate):
	mon = cdate.month+12*(cdate.year - MinYear) - 1
	return mon

def monthIdx1(dateStr):
	cdate = datetime.strptime( dateStr, C4A_date_string)
	mon = cdate.month+12*(cdate.year - MinYear) - 1
	return mon	

def plotResults(request,beat,crimeCat,crimeCat2=None):
 
	## build data vectors
	
	# 2do precompute, cache city-wide stats for all crimeCat
	
	if crimeCat2=='None':
		fname = '%s+%s' % (beat,crimeCat)
	else:
		fname = '%s+%s+%s' % (beat,crimeCat,crimeCat2)
	
	# Alternative: cache precomputed plots?
	
#	if os.path.isfile(PlotPath+fname+'.png'):
#		# 2do:  how to get figure from file?
#		img = getImage(PlotPath+fname+'.png')
#		canvas = FigureCanvas(img)
#		response = HttpResponse(content_type='image/png')
#		canvas.print_png(response)
#		return response

	nbins = 12 * ((MaxYear-MinYear)+1)
	cityFreq = [0 for m in range(nbins) ]
	beatFreq = [0 for m in range(nbins) ]
	  
	# NB: using regexp comparison with crimeCat prefix for cheapo hierarchy!
	
	# NB: need to include primary key (idx), cuz of deferred status from raw() ?
	
	# http://stackoverflow.com/questions/3105249/python-sqlite-parameter-substitution-with-wildcards-in-like
	startsCC = '^%s' % crimeCat

	# sqlite uses regexp
	# qryStr = "SELECT idx, cdate, beat FROM dailyIncid_oakcrime where crimeCat regexp %s"
	# WebFaction
	qryStr = 'SELECT idx, "cdateTime", beat FROM "dailyIncid_oakcrime" where "crimeCat" ~ %s'

	begQTime = datetime.now()
	for c in OakCrime.objects.raw(qryStr,[startsCC]):
	# for c in OakCrime.objects.raw(qryStrBAD):
		cd = c.cdateTime
		cb = c.beat
		mi = monthIdx(cd)
		if mi < 0 or mi > len(cityFreq):
			continue
		cityFreq[mi] += 1
		if beat==cb:
			beatFreq[mi] += 1

	if crimeCat2!='None':
		cityFreq2 = [0 for m in range(nbins) ]
		beatFreq2 = [0 for m in range(nbins) ]
			
		startsCC2 = '^%s' % crimeCat2
	
		# local
		# qryStr2 = "SELECT idx, cdateTime, beat FROM dailyIncid_oakcrime where crimeCat regexp %s"
		# WebFaction
		qryStr2 = 'SELECT idx, "cdateTime", beat FROM "dailyIncid_oakcrime" where "crimeCat" ~ %s'
	
		for c in OakCrime.objects.raw(qryStr2,[startsCC2]):
		# for c in OakCrime.objects.raw(qryStrBAD):
			cd = c.cdateTime
			cb = c.beat
			mi = monthIdx(cd)
			if mi < 0 or mi > len(cityFreq):
				continue
			cityFreq2[mi] += 1
			if beat==cb:
				beatFreq2[mi] += 1
				
	qryTime = datetime.now()-begQTime
		
	NGoodBeats = 57 # cf opd.GoodBeats
	avgFreq = [float(cityFreq[m])/NGoodBeats for m in range(nbins)]
	
	totBeat = sum(beatFreq)
	totCity = sum(cityFreq)
	
	## plot data
	
	f1 = p.figure()
	ax=f1.add_subplot(111)
		
	datemin = date(MinYear, 1, 1)
	datemax = date(MaxYear, 12, 1)
	dates = []
	for yr in range(MinYear,MaxYear+1):
		for mon in range(12):
			dates.append( date(yr,mon+1,1) )
	
	years	= mdates.YearLocator()   # every year
	months   = mdates.MonthLocator()  # every month
	yearsFmt = mdates.DateFormatter('%Y')
	
	# format the ticks
	ax.xaxis.set_major_locator(years)
	ax.xaxis.set_major_formatter(yearsFmt)
	ax.xaxis.set_minor_locator(months)
	ax.set_xlim(datemin, datemax)
   
	### PLOT
	
	if crimeCat2=='None':
		ax.plot(dates,beatFreq,label=('Beat %s' % beat))
		ax.plot(dates,avgFreq,label='BeatAvg (OPD total/57)')
	else:
		totBeat2 = sum(beatFreq2)
		totCity2 = sum(cityFreq2)
		avgFreq2 = [float(cityFreq2[m])/NGoodBeats for m in range(nbins)]

		ax.plot(dates,beatFreq,'b',label=('%s - Beat %s' % (crimeCat, beat)))
		ax.plot(dates,avgFreq,'b:',label='%s - BeatAvg (OPD total/57)' % (crimeCat))

		ax.plot(dates,beatFreq2,'g',label=('%s - Beat %s' % (crimeCat2, beat)))
		ax.plot(dates,avgFreq2,'g:',label='%s - BeatAvg' % (crimeCat2))
				
	runTime = str(datetime.now())
	runTime = runTime[:runTime.index(' ')] # HACK: drop time
	
	plotName = fname.replace('+',' ')
	if crimeCat2=='None':
		lbl = ('OPD Monthly Crime: %s (Total %d / %d)' % (plotName,totBeat, totCity))
	else:
		lbl = ('OPD Monthly Crime: %s\n(Total %d / %d ; %d / %d)' % (plotName,totBeat, totCity,totBeat2, totCity2))
		
	p.title(lbl,fontsize=10)
	p.legend(loc='upper left',fontsize=8)

	annote = 'ElectronicArtifacts.com'+' - '+runTime+\
		'\nOpenOakland.org -- a CodeForAmerica Brigade'
	p.text(0.65, 0.93,annote, \
				  horizontalalignment='left',verticalalignment='bottom', transform = ax.transAxes, \
				  fontsize=6 )
	
	f1.autofmt_xdate()
	
	figDPI=200
	fullPath = PlotPath+fname+'_'+runTime+'.png'
	userName = request.user.get_username()
	logger.info('user=%s plotting %d/%d (%6.2f sec) to %s' % (userName,totBeat,totCity,qryTime.total_seconds(),fullPath))
	f1.savefig(fullPath,dpi=figDPI)

	canvas = FigureCanvas(f1)
	response = HttpResponse(content_type='image/png')

	canvas.print_png(response)
	return response


def otherUtil(request):
	return render(request, 'dailyIncid/otherUtil.html')


## GeoDjango

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import Point
from django.contrib.gis.utils import LayerMapping

# @transaction.atomic
def add_geo(request):
	'''Convert ylat + xlng attributes to django.contrib.gis.geos.Point
	associate each incid with zip5
	'''

	begTime = datetime.now()
	begTimeStr = begTime.strftime('%y%m%d_%H%M%S')
	
	userName = request.user.get_username()

	logger.info('user=%s add_geo: Start=%s' % (userName,begTimeStr))
	nmissPt = 0
	nullPt = Point([])
	rptInterval = 1000
	for i,c in enumerate(OakCrime.objects.all().order_by('opd_rd')):

		try:
			# with transaction.atomic():
			
			# pnt X is longitude, Y is latitude
			pnt = Point(c.xlng, c.ylat)
			c.point = pnt
			
			if c.point==nullPt:
				nmissPt += 1
				c.zip = None
				continue

# 			zipgeo = Zip5Geo.objects.get(geom__contains=pnt)
# 			c.zip = zipgeo.zcta5ce10

			c.save()
			
			# print i, c.opd_rd,c.zip

		except IntegrityError as e:
			logger.error('user=%s add_geo Integrity?! %d %s %s' % (userName, i,c.opd_rd,e))
			
		except Exception as e:
			logger.error('user=%s add_geo?! %d %s %s' % (userName,i,c.opd_rd,e))

		if (i % rptInterval) == 0:
			elapTime = datetime.now() - begTime
			logger.info('user=%s add_geo: %d %s NMiss=%d' % userName, (i,elapTime.total_seconds(),nmissPt))
				
	return HttpResponse("You're at add_geo")

@login_required
def nearHereMZ(request):

	# import pdb; pdb.set_trace()
	if request.method == 'POST':
		qform = getLatLng(request.POST)
		if not qform.is_valid():
			return HttpResponse("Invalid lat long form?!")

		srs_default = 4326 # WGS84
		srs_10N = 26910 	# UTM zone 10N
		closeRadius = 500
	
		qryData = qform.cleaned_data
		
		pt = Point(qryData['lng'],qryData['lat'],srid=srs_default)
		pt.transform(srs_10N)
		
		# tstDT = datetime(2017, 2, 10, 17, 00)
		nowDT = datetime.now()
		
		minDate = nowDT - timedelta(days=180)
		
		# emulate psql:
		# select point from table where point && 
		#	ST_Transform( ST_Buffer( ST_Transform( point, 32610 ), 500 ), 4326 )
		
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					filter(point__distance_lte=(pt, D(m=closeRadius))). \
					order_by('cdateTime')
					
		incidList = list(queryset)
		
		userName = request.user.get_username()
		logger.info('user=%s NearHereMZ: NIncid=%d near (lat=%s,lng=%s)' % (userName, len(incidList), qryData['lat'], qryData['lng']))

		context = {}
		context['lat'] = qryData['lat']
		context['lng'] = qryData['lng']
		context['nIncid'] = len(incidList)
		context['incidList'] =  incidList
			
		return render(request, 'dailyIncid/nearHereListMZ.html', Context(context))
	
	else:
		qform = getLatLng()
		
	return render(request, 'dailyIncid/getLatLong.html', {'form': qform})

@login_required
def choosePlace(request,ptype):

	if request.method == 'POST':
		qform = getPlaceList(request.POST,ptype=ptype)
		if not qform.is_valid():
			return HttpResponse("Invalid placeList form?!")

		qryData = qform.cleaned_data
		
		tpchoice = qryData['placeList']
		xlng = tpchoice.xlng
		ylat = tpchoice.ylat

		srs_default = 4326 # WGS84
		srs_10N = 26910 	# UTM zone 10N
		closeRadius = 500

		pt = Point(xlng,ylat,srid=srs_default)
		pt.transform(srs_10N)
		
		# tstDT = datetime(2017, 2, 10, 17, 00)
		nowDT = datetime.now()
		
		minDate = nowDT - timedelta(days=180)
		
		# emulate psql:
		# select point from table where point && 
		#	ST_Transform( ST_Buffer( ST_Transform( point, 32610 ), 500 ), 4326 )
		
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					filter(point__distance_lte=(pt, D(m=closeRadius))). \
					order_by('cdateTime')
					
		incidList = list(queryset)
		
		userName = request.user.get_username()
		logger.info('username=%s choosePlace: Ptype=%s Choice=%s NIncid=%d near (xlng=%s,ylat=%s)' % \
			(userName, ptype, tpchoice.name, len(incidList), xlng, ylat))

		context = {}
		context['lat'] = ylat
		context['lng'] = xlng
		context['nIncid'] = len(incidList)
		context['incidList'] =  incidList
		
		context['ptype'] = ptype
		context['pdesc'] = tpchoice.desc
		
		return render(request, 'dailyIncid/nearHereListMZ.html', Context(context))
	
	else:
		# qform = getPlaceList()
		qform = getPlaceList(ptype=ptype)
		qs2 = TargetPlace.objects.filter(placeType=ptype)
		qsl = [ (tp.ylat,tp.xlng,tp.name,tp.desc) for tp in list(qs2) ]
	
	return render(request, 'dailyIncid/getPlaceName.html', {'form': qform, 'ptype': ptype, 'qsl': qsl})
						
from django.contrib import admin
from django.contrib.gis.admin import GeoModelAdmin
from django.contrib.gis.measure import D

from rest_framework import viewsets, generics
from dailyIncid import serializers

from datetime import datetime, timedelta

# ViewSet classes are almost the same thing as View classes, except that
# they provide operations such as read, or update, and not method
# handlers such as get or put.

# The example above would generate the following URL patterns:
# 
#     URL pattern: ^diAPI/$ Name: 'dailyIncid-list'
#     URL pattern: ^diAPI/{pk}/$ Name: 'dailyIncid-detail'
# 
# class IncidViewSet(viewsets.ReadOnlyModelViewSet):
# 	"""API endpoint for DailyIncidents
# 	"""
# 
# 	serializer_class = serializers.IncidSerializer
# 
# 	minDate = datetime.now() - timedelta(days=730)
# 	queryset = OakCrime.objects.filter(cdateTime__gt=minDate).order_by('opd_rd')

# The simplest way to filter the queryset of any view that subclasses
# GenericAPIView is to override the .get_queryset() method.
	
class BeatAPI(generics.ListAPIView):
	'''API view for crimes from specified beat 
		restricted to last two years 
	'''
	
	serializer_class = serializers.IncidSerializer
	
	def get_queryset(self):
		# restrict to last two years
		begTime = datetime.now()
		minDate = datetime.now() - timedelta(days=730)
		beat = self.kwargs['beat']
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
						filter(beat__iexact=beat). \
						order_by('opd_rd')
		
		nresult = len(queryset)
		elapTime = datetime.now() - begTime
		userName = self.request.user.get_username()
		logger.info('user=%s BeatListAPI %s nresult=%d (%6.2f sec) ' % (userName,beat,nresult,elapTime.total_seconds()))

		return queryset

class NearHereAPI(generics.ListAPIView):
	'''API view for crimes within 500m of this longitude_latitude, 
		restricted to last 6 months 
	'''

	serializer_class = serializers.IncidSerializer
	
	def get_queryset(self):

		lngStr = self.kwargs['lng']
		latStr = self.kwargs['lat']
		
		pt = Point(float(lngStr), float(latStr))
		
		closeRadius = 500
		begTime = datetime.now()
		minDate = datetime.now() - timedelta(days=180)

		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(point__distance_lte=(pt, D(m=closeRadius))). \
					order_by('cdateTime')

		nresult = len(queryset)
		elapTime = datetime.now() - begTime
		userName = self.request.user.get_username()
		logger.info('user=%s NearHereAPI lng=%s lat=%s nresult=%d (%6.2f sec)' % (userName,lngStr,latStr,nresult,elapTime.total_seconds()))

		return queryset

class CrimeCatAPI(generics.ListAPIView):
	'''API view for crimes of this crime category 
		restricted to last 6 months 
	'''
	serializer_class = serializers.IncidSerializer
	
	def get_queryset(self):

		crimeCat = self.kwargs['cc']
		begTime = datetime.now()
		# restrict to last two years
		minDate = datetime.now() - timedelta(days=180)

		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
						filter(crimeCat__iexact=crimeCat). \
						order_by('opd_rd')

		nresult = len(queryset)
		elapTime = datetime.now() - begTime
		userName = self.request.user.get_username()
		logger.info('user=%s CrimeCatAPI cc=%s nresult=%d (%6.2f sec)' % (userName,crimeCat,nresult,elapTime.total_seconds()))

		return queryset

class NearBART(generics.ListAPIView):	

	serializer_class = serializers.IncidSerializer
	
	def get_queryset(self):
		# restrict to 3 months, near BART station
		
		# Centroid of MCAR's three entrances
		# 37.828199, -122.265944 
		# 37 degrees 49'41.5"N 122 degrees 15'57.4"W
		MCAR_lat = 37.828199
		MCAR_lng = -122.265944
		MCAR_pt = Point(MCAR_lng, MCAR_lat)
		closeRadius = 300


		dateTimeArgString = self.kwargs['datetime']
# 		dtbits = dateTimeArgString.split('-')
# 		dty = int(dtbits[0])
# 		dtm = int(dtbits[1])
# 		dtd = int(dtbits[2])
# 		dth = int(dtbits[3])
# 		dtm = int(dtbits[4])
# 		dateTimeArg = datetime(dty,dtm,dtd,dth,dtm)
		
		# tstDT = datetime(2017, 2, 10, 17, 00)
		# minDate = tstDT - timedelta(days=90)
		minDate = datetime.datetime(2016, 11, 12, 17, 0)

		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(point__distance_lte=(MCAR_pt, D(m=closeRadius))). \
					order_by('cdateTime')

		return queryset

## Misc hacks

def add_zip(request):
	'''associate each incid with zip5
	ASSUME points already added to incidents
	'''

	begTime = datetime.now()
	begTimeStr = begTime.strftime('%y%m%d_%H%M%S')
	
	userName = request.user.get_username()
	logger.info('userName=%s add_zip: Start=%s' % (userName, begTimeStr))
	rptInterval = 1000
	nnull = 0
	for i,c in enumerate(OakCrime.objects.all()): # .order_by('opd_rd')):

		if (i % rptInterval) == 0:
			elapTime = datetime.now() - begTime
			logger.info('userName=%s add_zip: %d %s NNull=%d' % (userName,i,elapTime.total_seconds(),nnull))

		try:
			pnt = c.point
			if pnt==None:
				nnull += 1
				c.zip = ''
				continue
			
			zipgeo = Zip5Geo.objects.get(geom__contains=pnt)
			c.zip = zipgeo.zcta5ce10
			
			c.save()

		except IntegrityError as e:
			logger.error('userName=%s add_zip Integrity?! %d %s %s' % (userName,i,c.opd_rd,e))
			
		except Exception as e:
			logger.error('userName=%s add_zip?! %d %s %s' % (userName,i,c.opd_rd,e))

	
	return HttpResponse("userName=%s add_zip complete NNullPoint=%d" % (userName,nnull))

import csv
def tstAllFile(request):

	SeriousCrimeCatExact = ["HOMOCIDE","SEX_RAPE","WEAPONS"]
	SeriousCrimeCatStarts = ["ROBBERY","ASSAULT"]
		
	locTbl = {} # locName-> (lat,lng)
	bartStationFile = '/Data/sharedData/c4a_oakland/OAK_data/BART/bart-OAK-nincid.csv'
	park4File = '/Data/sharedData/c4a_oakland/OAK_data/parks-dist4.csv'
	
	csvDictReader = csv.DictReader(open(park4File,"r"))
	
	for entry in csvDictReader:
		# "Name","Entrance","NIncid","Lat","Lng"
		name = entry['Name']+'_'+entry['Entrance']
		loc = {'lng': entry['Lng'], 'lat': entry['Lat']}
		locTbl[name] = loc
	
	closeRadius = 500
	tstDT = datetime(2017, 2, 10, 17, 00)
	minDate = tstDT - timedelta(days=180)
	userName = request.user.get_username()
	for loc,qryData in locTbl.items():
		

		srs_default = 4326 # WGS84
		srs_10N = 26910 	# UTM zone 10N
		closeRadius = 500
	
		pt = Point(float(qryData['lng']),float(qryData['lat']),srid=srs_default)

		pt.transform(srs_10N)
		
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(point__distance_lte=(pt, D(m=closeRadius))). \
					order_by('cdateTime')
		incidList = list(queryset)
		nserious = 0
		for incid in incidList:
			if incid.crimeCat == None or len(incid.crimeCat)==0:
				continue
			for cc in SeriousCrimeCatExact:
				if incid.crimeCat == cc:
					nserious += 1
					continue
			for ccPrefix in SeriousCrimeCatStarts:
				if incid.crimeCat.startswith(ccPrefix):
					nserious += 1
					continue
			
		logger.info('userName=%s tstAllBART: %s NIncid=%d NSerious=%d near (lat=%s,lng=%s)' % \
				(userName, loc,len(incidList),nserious, qryData['lat'], qryData['lng']))
		
	return HttpResponse('tstAllBART %d locations' % (len(locTbl)))


