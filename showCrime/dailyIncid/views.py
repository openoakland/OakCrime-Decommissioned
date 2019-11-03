import logging
import random

import geojson 
import pytz
from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import D
from django.db import DatabaseError, connection
from django.db.models import Max, Min, Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import generics

from dailyIncid import serializers
from .forms import *
from .models import *


def awareDT(naiveDT):
	utc=pytz.UTC
	return utc.localize(naiveDT)

def rikNoLogin(cbfn): 
	# print('rikNoLogin cbfn',cbfn)
	return cbfn
login_required = rikNoLogin

logger = logging.getLogger(__name__)

def index(request):
 	return render(request, 'dailyIncid/index.html')

def testPage(request):
	return HttpResponse("Hello, world. You're at dailyIncid test.")

def need2login(request):
	logger.warning('need2login attempt')
	return render(request, 'dailyIncid/need2login.html', {})


@login_required
def getQuery(request):

	userName = request.user.get_username()

	# import pdb; pdb.set_trace()
	if request.method == 'POST':
		logger.info('user=%s getQuery-Post' % (userName))
		qform = twoTypeQ(request.POST)
		if qform.is_valid():
			qryData = qform.cleaned_data
			if qryData['crimeCat2']:
				qurl = '/dailyIncid/plots/%s+%s+%s.png' % (qryData['beat'],qryData['crimeCat'],qryData['crimeCat2'])
			else:
				qurl = '/dailyIncid/plots/%s+%s.png' % (qryData['beat'], qryData['crimeCat']) 
			return HttpResponseRedirect(qurl)
	else:
		logger.info('user=%s getQuery-nonPost' % (userName))
		qform = twoTypeQ()
		
	return render(request, 'dailyIncid/getQuery.html', {'form': qform})
	   

import matplotlib

# Force matplotlib to not use any Xwindows backend.
# changed in webapps/django/lib/python2.7/matplotlib/mpl-data/matplotlibrc

matplotlib.use('Agg')

import pylab as p

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from datetime import datetime,timedelta,date
import matplotlib.dates as mdates


# 2do:  reconcile djOakData code with c4a
MinYear = 2014
MaxYear = 2019
C4A_date_string = '%y%m%d_%H:%M:%S'


OakMinLat = 37.72635305398124	# south
OakMaxLat = 37.85354698750914	# north
OakMinLng = -122.34998208964241	# west
OakMaxLng = -122.11985846164134	# east
	
OakCenterLat = 37.7987417644
OakCenterLng = -122.2378203971 

#			   west				south			  east				 north
OaklandBBox = [-122.34998208964241, 37.72635305398124, -122.11985846164134, 37.85354698750914]

MCAR_lat = 37.828199
MCAR_lng = -122.265944
	
FTVL_lat = 37.77499525
FTVL_lng = -122.2242715

def monthIdx(cdate):
	mon = cdate.month+12*(cdate.year - MinYear) - 1
	return mon

def monthIdx1(dateStr):
	cdate = datetime.strptime( dateStr, C4A_date_string)
	mon = cdate.month+12*(cdate.year - MinYear) - 1
	return mon	

def plotResults(request,beat,crimeCat,crimeCat2=None):
	userName = request.user.get_username()

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

	begQTime = awareDT(datetime.now())

	for c in OakCrime.objects.raw(qryStr,[startsCC]):
	# for c in OakCrime.objects.raw(qryStrBAD):
		cd = c.cdateTime
		if cd.year < MinYear or cd.year > MaxYear:
			logger.info('user=%s plotResults: date out of range?! OPD_RD=%s %s' % (userName,c.opd_rd,c.cdateTime))
			continue
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
				
	qryTime = awareDT(datetime.now())-begQTime
		
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

		# 180914: modify legends
		ax.plot(dates,beatFreq,'b',label=('%s - Beat %s' % (crimeCat, beat)))
		ax.plot(dates,avgFreq,'b:',label='%s - Citywide average' % (crimeCat))

		ax.plot(dates,beatFreq2,'g',label=('%s - Beat %s' % (crimeCat2, beat)))
		ax.plot(dates,avgFreq2,'g:',label='%s - Citywide average' % (crimeCat2))
		
	begQTime = awareDT(datetime.now())
		
	runTime = str(begQTime)
	runTime = runTime[:runTime.index(' ')] # HACK: drop time
	
	plotName = fname.replace('+',' ')
	if crimeCat2=='None':
		lbl = ('OPD Monthly Crime: %s (Total %d / %d)' % (plotName,totBeat, totCity))
	else:
		lbl = ('OPD Monthly Crime: %s\n(Total %d / %d ; %d / %d)' % (plotName,totBeat, totCity,totBeat2, totCity2))
		
	p.title(lbl,fontsize=10)
	p.legend(loc='upper left',fontsize=8)

	# 180914: modify annotation
	annote = 'OpenOakland.org'+' - '+runTime
	p.text(0.7, 0.95,annote, \
				  horizontalalignment='left',verticalalignment='bottom', transform = ax.transAxes, \
				  fontsize=6 )
	
	f1.autofmt_xdate()
	
	figDPI=200
	fullPath = settings.PLOT_PATH+fname+'_'+runTime+'.png'
	logger.info('user=%s plotting %d/%d (%6.2f sec) to %s' % (userName,totBeat,totCity,qryTime.total_seconds(),fullPath))
	
	# 2do: 181218  fix plot file permission
	# f1.savefig(fullPath,dpi=figDPI)

	canvas = FigureCanvas(f1)

	# 180914: error "fname must be a PathLike or file handle"
	# https://stackoverflow.com/a/1109442/1079688
	import io
	buf = io.BytesIO()
	f1.savefig(buf, format='png')
	# matplotlib.pyplot.close(f1)
	response = HttpResponse(buf.getvalue(), content_type='image/png')
	
	return response


@login_required
def otherUtil(request):
	userName = request.user.get_username()
	logger.info('user=%s otherUtil' % (userName))
	return render(request, 'dailyIncid/otherUtil.html')


## GeoDjango

from django.contrib.gis.geos import Point


@login_required
def nearHere(request):

	userName = request.user.get_username()

	# import pdb; pdb.set_trace()
	if request.method == 'POST':
		logger.info('user=%s nearHere-Post' % (userName))
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
		nowDT = awareDT(datetime.now())
		
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
		
		logger.info('user=%s NearHere: NIncid=%d near (lat=%s,lng=%s)' % (userName, len(incidList), qryData['lat'], qryData['lng']))

		context = {}
		context['lat'] = qryData['lat']
		context['lng'] = qryData['lng']
		context['nIncid'] = len(incidList)
		context['incidList'] =  incidList
			
		return render(request, 'dailyIncid/nearHereListMB.html', context)
	
	else:
		logger.info('user=%s nearHereMZ-nonPost' % (userName))
		qform = getLatLng()
		
	return render(request, 'dailyIncid/getLatLong.html', {'form': qform})

@login_required
def choosePlace(request,ptype):

	userName = request.user.get_username()

	if request.method == 'POST':
		logger.info('user=%s choosePlace-Post' % (userName))
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
		nowDT = awareDT(datetime.now())
		
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
		
		logger.info('username=%s choosePlace: Ptype=%s Choice=%s NIncid=%d near (xlng=%s,ylat=%s)' % \
			(userName, ptype, tpchoice.name, len(incidList), xlng, ylat))

		context = {}
		context['lat'] = ylat
		context['lng'] = xlng
		context['nIncid'] = len(incidList)
		context['incidList'] =  incidList
		
		context['ptype'] = ptype
		context['pdesc'] = tpchoice.desc
		
		return render(request, 'dailyIncid/nearHereListMB.html', context)
	
	else:
		logger.info('user=%s choosePlace-nonPost' % (userName))
		# qform = getPlaceList()
		qform = getPlaceList(ptype=ptype)
		qs2 = TargetPlace.objects.filter(placeType=ptype)
		qsl = [ (tp.ylat,tp.xlng,tp.name,tp.desc) for tp in list(qs2) ]
	
	return render(request, 'dailyIncid/getPlaceName.html', {'form': qform, 'ptype': ptype, 'qsl': qsl})

@login_required	
def heatmap(request,mapType='general'):
	'''browsable version of Oakland area's crimes with date range slider
	170911
	'''

	userName = request.user.get_username()
	logger.info('user=%s mapType=%s heatmap' % (userName,mapType))

	nowDT = awareDT(datetime.now())
	minDate = nowDT - timedelta(days=90)

	begTime = nowDT
	
	if mapType == 'general':
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					order_by('cdateTime')

	elif mapType=='gun':
		# replicate query ala that for Scott Morris
		# select opd_rd, nvictim, nhospital, weapon, "gswP", "cdateTime", addr from "dailyIncid_oakcrime" 
		# where "cdateTime" > '2017-01-01'::date and weapon like 'gun%' and (nvictim>0 or nhospital>0 or "gswP")
		# order by opd_rd
		
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					filter( models.Q(weapon__contains='gun') | models.Q(gswP=True) )
				
	incidList = list(queryset)

# 	ocoFirst = incidList[0]
# 	ocoLast = incidList[-1]
# 	print('heatmap',ocoFirst.opd_rd,ocoFirst.cdateTime,ocoLast.opd_rd,ocoLast.cdateTime)
	
	elapTime = awareDT(datetime.now()) - begTime
	logger.info('username=%s heatmap %s : NIncid=%d  (%6.2f sec)' % (userName, mapType, len(incidList),elapTime.total_seconds()))

	# In Django 1.8+, the template's render method takes a dictionary for
	# the context parameter. Support for passing a Context instance is
	# deprecated, and gives an error in Django 1.10+

	context = {}
	context['mapType'] = mapType
	context['nincid'] = len(incidList)
	context['cxlng'] = FTVL_lng
	context['cylat'] = FTVL_lat
	
	# 2do: mapbox unifies heatmap with circles
	context['heatmap'] = True
	
	# NB: javascript uses ZERO-based months!
	context['minDate'] = [minDate.year,minDate.month-1,minDate.day]
	context['maxDate'] = [nowDT.year,nowDT.month-1,nowDT.day]

	context['minSlider'] = [minDate.year,minDate.month-1,minDate.day]
	context['maxSlider'] = [nowDT.year,nowDT.month-1,nowDT.day]
	
	# dataArr =  [ [lat, lng, intensity], ... ]
	# dataArr = [ [o.ylat,o.xlng,1] for o in incidList]
	
	gjFeatures = []
	for o in incidList:
		# 180129: mapbox needs points as geojson, (lng,lat order)
		[jlat,jlng] = jitterCoord(o.ylat, o.xlng)
		pt = geojson.Point( (jlng, jlat) )
		f = geojson.Feature( geometry=pt, properties={"count": 1} )
		f.properties['opd_rd'] = o.opd_rd
		dtstr = o.cdateTime.strftime('%a,%b-%d-%y_%I:%M%p')
		f.properties['cdateTime'] = dtstr
		f.properties['crimeCat'] = o.crimeCat
		if mapType == 'gun':
			# if o.source.startswith("DLog"):
			if o.source.find('SOC_') == -1:
				f.properties['majorIncid'] = 'DLog'
			if o.gswP:
				f.properties['majorIncid'] = 'True'
			else:
				f.properties['majorIncid'] =' False'
		else:
			majorP = majorCrimeCatP(o)
			
			f.properties['majorIncid'] =  majorP
			
		gjFeatures.append(f)

	gjCollection = geojson.FeatureCollection(gjFeatures)
	rawgj = geojson.dumps(gjCollection)
	
	context['dataArr'] = rawgj

	# MapZen bounding box coordinates in a 'southwest_lng,southwest_lat,northeast_lng,northeast_lat' format	
	# MapBox bounding box coordinates in an array of LngLatLike objects in [sw, ne] order, or an array of
	# numbers in [west, south, east, north] order.
	
	mapBound = OaklandBBox
	context['mapBounds'] = mapBound
	
	if mapType == 'gun':
		# for guns, restrict crimeCat to those mentioned
		ccMention = set()
		for oco in incidList:
			cc = oco.crimeCat
			ccbits = cc.split('_')
			ccMention.add(ccbits[0])
		ccatList = list(ccMention)
		if '' in ccatList:
			ccatList.remove('')
		context['crimeCat'] = ccatList	

	
	return render(request, 'dailyIncid/heatmap.html', context)

					
@login_required	
def hybridQual(request,mapType):
	'''HYBRID qualified heatmap: accepts additional filter parameters
	AND uses NIncid thresh to select between heatmap vs marker display
	'''

	nowDT = awareDT(datetime.now())
	minDate = nowDT - timedelta(days=90)
		
	NIncidForMarkers = 75
		
	userName = request.user.get_username()
	
	if mapType == 'general':
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					order_by('cdateTime')

	elif mapType=='gun':
		# replicate query ala that for Scott Morris
		# select opd_rd, nvictim, nhospital, weapon, "gswP", "cdateTime", addr from "dailyIncid_oakcrime" 
		# where "cdateTime" > '2017-01-01'::date and weapon like 'gun%' and (nvictim>0 or nhospital>0 or "gswP")
		# order by opd_rd
		
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					exclude(xlng__isnull=True). \
					exclude(ylat__isnull=True). \
					filter( models.Q(weapon__contains='gun') | models.Q(gswP=True) )
					
	logline = 'username=%s hybridQual %s: qs0=%d' % (userName, mapType, qs0.count())
	logger.info(logline)

# 	list0 = list(qs0)
# 	ocoFirst = list0[0]
# 	ocoLast = list0[-1]
# 	print('hybrid',ocoFirst.opd_rd,ocoFirst.cdateTime,ocoLast.opd_rd,ocoLast.cdateTime)

	ccatList = request.GET.getlist('crimeCat')

	NTopLevelCC = 16 # updated 190812
	if len(ccatList) < NTopLevelCC:
		
		# NB: disjunction across separate crimeCat query sets!
		qscc = OakCrime.objects.none()
		for cc in ccatList:
			# NB: __startswith converts to LIKE cc%
			qs1 = qs0.filter(crimeCat__startswith=cc)
			qscc = (qscc | qs1)
			# print(cc,qs1.count(),qscc.count())
	
		logline = 'username=%s hybridQual: crimeCat="%s" postCC=%d' % (userName, ccatList, qscc.count())
		logger.info(logline)
		
	elif mapType == 'gun':
		# for guns, restrict crimeCat to those mentioned
		ccMention = set()
		for oco in qs0:
			cc = oco.crimeCat
			ccbits = cc.split('_')
			ccMention.add(ccbits[0])
		ccatList = list(ccMention)
		ccatList.remove('')

		qscc = OakCrime.objects.none()
		for cc in ccatList:
			# NB: __startswith converts to LIKE cc%
			qs1 = qs0.filter(crimeCat__startswith=cc)
			qscc = (qscc | qs1)
			# print(cc,qs1.count(),qscc.count())
	
		logline = 'username=%s hybridQual: gun crimeCat="%s" postCC=%d' % (userName, ccatList, qscc.count())
		logger.info(logline)
				
	else:
		qscc = qs0
		logline = 'username=%s hybridQual: No CC filter; postCC=%d' % (userName, qscc.count())
		logger.info(logline)
		
		
	# bounding box coordinates in a 'southwest_lng,southwest_lat,northeast_lng,northeast_lat' format	
	mapboundStr = request.GET['mapBounds']
	mapBound = eval(mapboundStr)

	# bbox = xmin, ymin, xmax, ymax
	poly = Polygon.from_bbox(mapBound)
	
	# HACK: better django might keep this manipulation over QuerySets?
	ocoList = list(qscc)
	
	# returned as Y,M,D STRING, to avoid JS/Python (0 vs 1-index) month numbering
	# JS display format = "MMM D YYYY"
	selectDateFmt = "%b %d %Y"
	dateDiffThresh = timedelta(days=2)

	minSelectDateStr = request.GET['minDate']
	maxSelectDateStr = request.GET['maxDate']
	minSelectDate = awareDT(datetime.strptime(minSelectDateStr,selectDateFmt))
	maxSelectDate = awareDT(datetime.strptime(maxSelectDateStr,selectDateFmt))
	
	# 2do: these queryset filters don't work?
	# NB: django comparison requires just date!
	# minSelectDate = datetime.date(minSelectDate)
	# maxSelectDate = datetime.date(maxSelectDate)
	# 	qs0 = qs0.filter(cdateTime__date__gt=minSelectDate)
	#	qs0 = qs0.filter(cdateTime__date__lt=maxSelectDate)
	
	minDateChg = abs(minSelectDate - minDate) > dateDiffThresh
	if minDateChg:
		minDate = minSelectDate
		
	maxDateChg = abs(maxSelectDate - nowDT) > dateDiffThresh
	if maxDateChg:
		maxDate = maxSelectDate
	else:
		maxDate = nowDT

	ocoList3 = []
	for oco in ocoList:
		dt = oco.cdateTime
		if 	(not minDateChg or (minDateChg and dt > minSelectDate)) and \
			(not maxDateChg or (maxDateChg and dt < maxSelectDate)): 
			ocoList3.append(oco)
			
	logline = 'username=%s hybridQual: postDateFilter=%d %s (%s) - %s (%s)' % \
		(userName, len(ocoList3),minSelectDateStr,minDateChg, maxSelectDateStr, maxDateChg)
	logger.info(logline)

	ocoList4 = []
	for oco in ocoList3:
		pt = oco.point
		if pt==None:
			logline = 'username=%s hybridQual: No point, DLog?! %s %s' % \
				(userName, oco.opd_rd,oco.source)
			logger.info(logline)
			continue
		if poly.contains(pt):
			ocoList4.append(oco)
			
	incidList = ocoList4
	nincid = len(incidList)
	elapTime = awareDT(datetime.now()) - nowDT
	logline = 'username=%s hybridQual: nincid=%d bbox=%s (%6.2f sec)' % (userName, nincid,mapBound,elapTime.total_seconds())
	logger.info(logline)
			
	context = {}
	context['mapType'] = mapType
	context['qualified'] = True
	context['nincid'] = nincid
	context['crimeCat'] = ccatList
	# NB: need to convert to list for javascript
	context['mapBounds'] = list(mapBound)
	
	# NB: javascript uses ZERO-based months!
	context['minDate'] = [minDate.year,minDate.month-1,minDate.day]
	context['maxDate'] = [maxDate.year,maxDate.month-1,maxDate.day]
	if minDateChg:
		context['minSlider'] = [minSelectDate.year,minSelectDate.month-1,minSelectDate.day]
	else:
		context['minSlider'] = [minDate.year,minDate.month-1,minDate.day]
	if maxDateChg:
		context['maxSlider'] = [maxSelectDate.year,maxSelectDate.month-1,maxSelectDate.day]
	else:
		context['maxSlider'] = [nowDT.year,nowDT.month-1,nowDT.day]

	# 2do: mapbox unifies heatmap with circles
	
	# dataArr =  [ [lat, lng, intensity], ... ]
	# dataArr = [ [o.ylat,o.xlng,1] for o in ocoList4]
	
	# gjPoints = [ geojson.Point( (o.xlng, o.ylat) ) for o in ocoList4]
	# gjFeatures = [ geojson.Feature( geometry=gjpt, properties={"count": 1} ) for gjpt in gjPoints ]

	# 180130: extract only those incident details required for circle label; add as geojson properties
	# incid.opd_rd, incid.cdateTime, incid.crimeCat
	# also move major/minor crimeCat logic here (vs. javascript in heatmap.html)

	gjFeatures = []
	for o in ocoList4:
		[jlat,jlng] = jitterCoord(o.ylat, o.xlng)
		# 180129: mapbox needs points as geojson, (lng,lat order)
		pt = geojson.Point( (jlng, jlat) )
		f = geojson.Feature( geometry=pt, properties={"count": 1} )
		f.properties['opd_rd'] = o.opd_rd
		dtstr = o.cdateTime.strftime('%a,%b-%d-%y_%I:%M%p')
		f.properties['cdateTime'] = dtstr
		f.properties['crimeCat'] = o.crimeCat
		if mapType == 'gun':
			# if o.source.startswith("DLog"):
			if o.source.find('SOC_') == -1:
				f.properties['majorIncid'] = 'DLog'
			if o.gswP:
				f.properties['majorIncid'] = 'True'
			else:
				f.properties['majorIncid'] =' False'
		else:
			majorP = majorCrimeCatP(o)
			f.properties['majorIncid'] =  majorP
			
		gjFeatures.append(f)
	
	gjCollection = geojson.FeatureCollection(gjFeatures)
	rawgj = geojson.dumps(gjCollection)
	
	context['dataArr'] = rawgj
	
	return render(request, 'dailyIncid/heatmap.html', context)

NCPCChair2Beat = {'rik': '09X',
					'ncpc-03Y': '03Y',
					'ncpc-rock': '12Y+13X',
					'ncpc-glake': '14Y+16X',
					'ncpc-21XY': '21X+21Y',
					'ncpc-13Y': '13Y',
				  	'rdsmith': '15X',
					'ncpc-11X': '11X',
					}

@login_required	
def bldNCPCRpt(request):
	'''produce report for NCPC of beat 
	'''

	nowDT = awareDT(datetime.now())
	minDate = nowDT - timedelta(days=60)
				
	userName = request.user.get_username()

	if userName not in NCPCChair2Beat:
		logline = 'username=%s bldNCPCRpt No beat ?!' % (userName)
		logger.info(logline)
		need2login(request)
	
	beat = NCPCChair2Beat[userName]
	if beat.find('+') != -1:
		beatList = beat.split('+')
		beat0 = beatList[0]
		beat1 = beatList[1]
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					filter( Q(beat=beat0) | Q(beat=beat1) ). \
					order_by('cdateTime')
		
	else:
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=nowDT). \
					filter(beat=beat). \
					order_by('cdateTime')
	
	incidList0 = list(qs0)		
	nbeat = len(incidList0)	
	logline = 'username=%s bldNCPCRpt Beat=%s N=%d' % (userName, beat,nbeat)
	logger.info(logline)

	# qs1 uses relaxed bbox around beat's incidents

	xlngMin = ylatMin = 1000.
	xlngMax = -1000.
	ylatMax = 0.
	xlngSum = 0.
	ylatSum = 0.
	ncoord = 0
	
	incid0_opd_rd_Dict = {} # dict for quick tests by second vicinity set
	for incid in incidList0:
		incid0_opd_rd_Dict[incid.opd_rd] = True
		if incid.ylat == None:
			continue
		
		ncoord += 1
		xlngSum += incid.xlng
		ylatSum += incid.ylat
		
		if incid.ylat < ylatMin:
			ylatMin = incid.ylat
		if incid.ylat > ylatMax:
			ylatMax = incid.ylat
		
		if incid.xlng < xlngMin:
			xlngMin = incid.xlng
		if incid.xlng > xlngMax:
			xlngMax= incid.xlng
			
	ctrXLng = xlngSum / float(ncoord)
	ctrYLat = ylatSum / float(ncoord)
	
	# relax bbox
	# BBoxBorder = 1e-3
	BBoxBorder = 1e-2
	
	# 	xmin = sw[0]
	# 	ymin = ne[1]
	# 	xmax = sw[1]
	# 	ymax = ne[0]
	
# 	xlngMin -= BBoxBorder
# 	xlngMax += BBoxBorder
# 	ylatMin -= BBoxBorder
# 	ylatMax += BBoxBorder

	xlngMin = ctrXLng - BBoxBorder
	xlngMax = ctrXLng + BBoxBorder
	ylatMin = ctrYLat - BBoxBorder
	ylatMax = ctrYLat + BBoxBorder
	
	bbox = (xlngMin, ylatMin, xlngMax, ylatMax)
	geom = Polygon.from_bbox(bbox)
	
	qs1 = OakCrime.objects.filter(cdateTime__gt=minDate). \
				filter(cdateTime__lt=nowDT). \
				filter(point__contained=geom). \
				order_by('cdateTime')
	incidList1 = list(qs1)		
	nvicinity = len(incidList1)	
	logline = 'username=%s bldNCPCRpt Beat=%s NVincinity=%d' % (userName, beat,nvicinity)
	logger.info(logline)
	
	context = {}
	
	context['beat'] = beat
	context['user'] = userName
	context['nbeat'] = nbeat
	context['nvicinity'] = nvicinity

	maxDateDigits = nowDT.strftime('%y%m%d')
	minDateDigits = minDate.strftime('%y%m%d')
	maxDateStr = nowDT.strftime('%b %d %Y')
	minDateStr = minDate.strftime('%b %d %Y')

	context['minDateDigits'] = minDateDigits
	context['maxDateDigits'] = maxDateDigits
	
	context['minDateStr'] = minDateStr
	context['maxDateStr'] = maxDateStr

	gjFeatures = []
	for o in incidList1:
		if o.ylat == None:
			f = geojson.Feature( geometry=None, properties={"count": 1} )
		else:
			[jlat,jlng] = jitterCoord(o.ylat, o.xlng)
			pt = geojson.Point( (jlng, jlat) )
			f = geojson.Feature( geometry=pt, properties={"count": 1} )
		f.properties['opd_rd'] = o.opd_rd
		dtstr = o.cdateTime.strftime('%a,%b-%d-%y_%I:%M%p')
		f.properties['cdateTime'] = dtstr
		f.properties['crimeCat'] = o.crimeCat
	
		# NB: use major flag to distinguish beat from vicinity
		if o.source.find('SOC_') == -1:
			f.properties['majorIncid'] = 'DLog'
		else:
			# NB: mapbox get works on STRINGS
			f.properties['majorIncid'] =  str(o.opd_rd in incid0_opd_rd_Dict)
		
		gjFeatures.append(f)

	gjCollection = geojson.FeatureCollection(gjFeatures)
	rawgj = geojson.dumps(gjCollection)
	
	context['dataArr'] = rawgj

	# MapZen bounding box coordinates in a 'southwest_lng,southwest_lat,northeast_lng,northeast_lat' format	
	# MapBox bounding box coordinates in an array of LngLatLike objects in [sw, ne] order, or an array of
	# numbers in [west, south, east, north] order.
	
	context['mapBounds'] = list(bbox)
	
	return render(request, 'dailyIncid/ncpc.html', context)


def bldNCPCcsv(incidList):
	
	outFields = ['opd_rd','cdateTime','dlogData','ctype','desc','beat','addr','crimeCat']
	quoteFields = ['ctype', 'desc', 'addr']
	
	outs = ''
	line = ''
	for f in outFields:
		line += '%s,' % f 
	line = line[:-1]
	line += '\n'
	outs += line
	
	for incid in incidList:
		line = ''
		for f in outFields:
			if f in quoteFields:
				s = '"%s"' % getattr(incid, f)
			else:
				s = '%s' % getattr(incid, f)
			if s == 'None':
				s = ' '
			line += '%s,' % s
		line = line[:-1]
		line += '\n'
		outs += line
	
	return outs
		
		
@login_required	
def downloadNCPC(request, beat,minDateDigit,maxDateDigit):

	userName = request.user.get_username()
	
	if userName not in NCPCChair2Beat or beat != NCPCChair2Beat[userName]:
		logline = 'username=%s downloadNCPC Wrong beat=%s ?!' % (userName, beat)
		logger.info(logline)
		need2login(request)
	
	minDate = awareDT(datetime.strptime( minDateDigit, '%y%m%d'))
	maxDate = awareDT(datetime.strptime( maxDateDigit, '%y%m%d'))
	
	if beat.find('+') != -1:
		beatList = beat.split('+')
		beat0 = beatList[0]
		beat1 = beatList[1]
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=maxDate). \
					filter( Q(beat=beat0) | Q(beat=beat1) ). \
					order_by('cdateTime')
		
	else:
		qs0 = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(cdateTime__lt=maxDate). \
					filter(beat=beat). \
					order_by('cdateTime')
				
	incidList = list(qs0)

	logline = 'username=%s downloadNCPC Beat=%s NIncid=%d' % (userName, beat,len(incidList))
	logger.info(logline)
				
	rpt = bldNCPCcsv(incidList)

	response = HttpResponse(rpt, content_type="text/csv")
	response['Content-Disposition'] = 'attachment; filename="NCPC_%s_%s-%s.csv"' % (beat,minDateDigit,maxDateDigit)
	return response

@login_required	
def incidRpt(request,opd_rd):
	qs = OakCrime.objects.filter(opd_rd=opd_rd)
	incidList = list(qs)

	userName = request.user.get_username()
	logline = 'username=%s incidRpt OPD_RD=%s NIncid=%d' % (userName, opd_rd,len(incidList))
	logger.info(logline)

	context = {}
	context['incid'] = incidList[0]

	return render(request, 'dailyIncid/incidRpt.html', context)
	
def majorCrimeCatP(incid):
	'''distinguish major, minor and dailyLog-only incidents
	'''
	
	majCC = ["HOMICIDE","SEX_RAPE","WEAPONS"]
	majCCPrefix = ["ROBBERY","ASSAULT"]
	
	cc = incid.crimeCat
	majorP = cc in majCC or \
				any([cc.startswith(pre) for pre in majCCPrefix]) or \
				incid.gswP or (incid.weapon and incid.weapon.find('gun') != -1)

	# if incid.source.startswith("DLog"):
	if incid.source.find('SOC_') == -1:
		return 'DLog'
	else:
		# HACK: mapbox-gl-js match expression requires strings (:
		majorPstr = str(bool(majorP))
		return majorPstr

def jitterCoord(ylat,xlng):
	# viz overlapping markers
	JitterScale = 3.0e-4;
	jlat = ylat + JitterScale * (random.random() - 0.5);
	jlng = xlng + JitterScale * (random.random() - 0.5);
	return [jlat,jlng];

		
def docView(request):

	userName = request.user.get_username()
	logline = 'username=%s docView' % (userName)
	
	nincid = OakCrime.objects.count()
	
	# NB: filter absurd dates
	nowDT =  awareDT(datetime.now())
	maxDate =OakCrime.objects.filter(cdateTime__lt=nowDT).aggregate(Max('cdateTime'))['cdateTime__max']
	
	minDate =OakCrime.objects.all().aggregate(Min('cdateTime'))['cdateTime__min']
	maxModDate = OakCrime.objects.all().aggregate(Max('lastModDateTime'))['lastModDateTime__max']
	
	maxDateStr = maxDate.strftime('%b %d %Y')
	minDateStr = minDate.strftime('%b %d %Y')
	maxModDateStr = maxModDate.strftime('%b %d %Y')
	
	return render(request, 'dailyIncid/doc.html', {'nincid': nincid, 
													'maxDate': maxDateStr, 
													'minDate': minDateStr,
													'maxModDate': maxModDateStr})
			

# ViewSet classes are almost the same thing as View classes, except that
# they provide operations such as read, or update, and not method
# handlers such as get or put.

# The example above would generate the following URL patterns:
# 
#	 URL pattern: ^diAPI/$ Name: 'dailyIncid-list'
#	 URL pattern: ^diAPI/{pk}/$ Name: 'dailyIncid-detail'
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
		nowDT = awareDT(datetime.now())

		minDate = nowDT - timedelta(days=730)
		beat = self.kwargs['beat']
		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
						filter(beat__iexact=beat). \
						order_by('opd_rd')
		
		nresult = len(queryset)
		elapTime = awareDT(datetime.now()) - nowDT
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
		begTime = awareDT(datetime.now())
		minDate = begTime - timedelta(days=180)

		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
					filter(point__distance_lte=(pt, D(m=closeRadius))). \
					order_by('cdateTime')

		nresult = len(queryset)
		elapTime = awareDT(datetime.now()) - begTime
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
		begTime = awareDT(datetime.now())
		# restrict to last two years
		minDate = begTime - timedelta(days=180)

		queryset = OakCrime.objects.filter(cdateTime__gt=minDate). \
						filter(crimeCat__iexact=crimeCat). \
						order_by('opd_rd')

		nresult = len(queryset)
		elapTime = awareDT(datetime.now()) - begTime
		userName = self.request.user.get_username()
		logger.info('user=%s CrimeCatAPI cc=%s nresult=%d (%6.2f sec)' % (userName,crimeCat,nresult,elapTime.total_seconds()))

		return queryset


def health(_):
    """ Returns a simplified view of the health of this application.
    Checks the database connection. Use this for load balancer health checks.

    https://github.com/clintonb/cookiecutter-django/blob/6a5840ed79f607b7d70eab80f4815799cb29eaff/%7B%7B%20cookiecutter.project_slug%20%7D%7D/%7B%7B%20cookiecutter.project_slug%20%7D%7D/apps/core/views.py
    """
    def status_fmt(ok):
        return 'OK' if ok else 'UNAVAILABLE'

    try:
        cursor = connection.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        database_ok = True
    except DatabaseError:
        database_ok = False

    overall_ok = all((database_ok,))

    data = {
        'timestamp': timezone.now(),
        'overall_status': status_fmt(overall_ok),
        'detailed_status': {
            'database_status': status_fmt(database_ok),
        },
    }

    status = 200 if overall_ok else 503

    return JsonResponse(data, status=status)
