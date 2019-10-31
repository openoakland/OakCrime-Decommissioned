"""showCrime.dailyIncid.models.py:

updated 23 Mar 17: include GIS, 
updated 20 Jun 17: combine dateTime, add source
updated 17 Oct 17: incorporate dailyLog incident data
updated 14 Jul 18: add OPDBeats, CensusTracts
"""

__author__ = "rik@electronicArtifacts.com", "actionspeakslouder@gmail.com"
__version__ = "0.4"

from django.contrib.gis.db import models

## Stick global variables in models
DateFormat = '%Y-%m-%d'
TimeFormat = '%H:%M:%S'
MinDateStr = '2007-01-01'
MaxDateStr = '2017-12-31'

class OakCrime(models.Model):
	# non-NULL fields
	idx = models.AutoField(primary_key=True)
	opd_rd = models.CharField(max_length=10,db_index=True)
	oidx = models.IntegerField()
	cdateTime = models.DateTimeField(db_index=True)
	# list of all source_date in chron order, separated by +
	source = models.CharField(max_length=500)

	# NULL ok fields
	ctype = models.CharField(max_length=100,blank=True,null=True)
	desc = models.CharField(max_length=200,blank=True,null=True)
	# beat from OPD (vs. geobeat determined by geo query)
	beat = models.CharField(max_length=20,blank=True,null=True)
	addr = models.CharField(max_length=100,blank=True,null=True)
	xlng = models.FloatField(null=True)
	ylat = models.FloatField(null=True)
	# Defaults to SRID=4326 (aka WGS84) 
	# units are in degrees of longitude and latitude
	point = models.PointField(null=True)
	
	ucr = models.CharField(max_length=5,blank=True,null=True)
	statute = models.CharField(max_length=50,blank=True,null=True)
	crimeCat = models.CharField(max_length=50,blank=True,null=True,db_index=True)
	
	lastModDateTime = models.DateTimeField(auto_now=True)
	
	# derived geo attributes
	zip = models.CharField(max_length=5,blank=True,null=True)
	# beat as determined by geo query (vs. beat from OPD)
	# 2do 
	geobeat = models.CharField(max_length=3,blank=True,null=True)
	# full geoid = 06001423300, name=4233, tracttce=423300
	# (CA-AlamedaCty-specific) longest census tract name < 10 char, eg "4062.01"
	ctractGeoID = models.CharField(max_length=11,blank=True,null=True)
	
	# Precincts_AlamedaCounty range from 200100-880600
	precinct = models.IntegerField(blank=True,null=True)
	
	## dailyLog fields
	dlogData = models.NullBooleanField(blank=True,null=True)			# indicating data from dailyLog
	lossList = models.CharField(max_length=200,blank=True,null=True)	# list of lost items
	gswP = models.NullBooleanField(blank=True,null=True)				# gun shot wound
	weapon = models.CharField(max_length=50,blank=True,null=True)
	callout = models.CharField(max_length=50,blank=True,null=True)	# 'yes:' + reg
	ncustody = models.IntegerField(blank=True,null=True)
	nsuspect = models.IntegerField(blank=True,null=True)
	nvictim = models.IntegerField(blank=True,null=True)
	nhospital = models.IntegerField(blank=True,null=True)
	roList = models.CharField(max_length=200,blank=True,null=True)
	pcList = models.CharField(max_length=200,blank=True,null=True)
	
	def __unicode__(self):
		return '%d:%s' % (self.idx,self.opd_rd)

class CrimeCat(models.Model):
	idx = models.AutoField(primary_key=True)
	ctypeDesc = models.CharField(max_length=100,db_index=True)
	crimeCat = models.CharField(max_length=100)
	
class TargetPlace(models.Model):
	'''specific places to be selected for crimes nearby
	'''
	placeType = models.CharField(max_length=20)
	ylat = models.FloatField()
	xlng = models.FloatField()
	name = models.CharField(max_length=254)
	desc = models.CharField(max_length=254)

	def __unicode__(self):
		return '%s' % (self.desc)

# 170329
# python manage.py ogrinspect /Data/sharedData/c4a_oakland/OAK_data/maps_oakland/tl_2010_06_zcta510/tl_2010_06_zcta510.shp Zip5Geo --multi --mapping

class Zip5Geo(models.Model):
	statefp10 = models.CharField(max_length=2)
	zcta5ce10 = models.CharField(max_length=5)
	geoid10 = models.CharField(max_length=7)
	classfp10 = models.CharField(max_length=2)
	mtfcc10 = models.CharField(max_length=5)
	funcstat10 = models.CharField(max_length=1)
	aland10 = models.FloatField()
	awater10 = models.FloatField()
	intptlat10 = models.CharField(max_length=11)
	intptlon10 = models.CharField(max_length=12)
	partflg10 = models.CharField(max_length=1)
	geom = models.MultiPolygonField(srid=4326)

	def __str__(self):			  # __unicode__ on Python 2
		return 'zcta5ce10: %s' % self.zcta5ce10

# Auto-generated `LayerMapping` dictionary for Zip5Geo model
Zip5Geozip5geo_mapping = {
		'statefp10' : 'STATEFP10',
		'zcta5ce10' : 'ZCTA5CE10',
		'geoid10' : 'GEOID10',
		'classfp10' : 'CLASSFP10',
		'mtfcc10' : 'MTFCC10',
		'funcstat10' : 'FUNCSTAT10',
		'aland10' : 'ALAND10',
		'awater10' : 'AWATER10',
		'intptlat10' : 'INTPTLAT10',
		'intptlon10' : 'INTPTLON10',
		'partflg10' : 'PARTFLG10',
		'geom' : 'MULTIPOLYGON',
}
	
# 180712
# python manage.py  ogrinspect /Data/c4a-Data/OAK_data/maps_oakland/beats-shp OPDBeatMap --srid=4326 --mapping --multi

class OPDBeatMap(models.Model):
	name = models.CharField(max_length=254)
	
# 	descriptio = models.CharField(max_length=254)
# 	timestamp = models.CharField(max_length=254)
# 	begin = models.CharField(max_length=254)
# 	end = models.CharField(max_length=254)
# 	altitudemo = models.CharField(max_length=254)
# 	tessellate = models.BigIntegerField() # constant=-1
# 	extrude = models.BigIntegerField() # constant=-1
# 	visibility = models.BigIntegerField() # constant=-1
# 	draworder = models.CharField(max_length=254)
# 	icon = models.CharField(max_length=254)
# 	name_1 = models.CharField(max_length=254)
	objectid = models.CharField(max_length=254)
	cp_beat = models.CharField(max_length=254)
	pol_beat = models.CharField(max_length=254)
	pol_dist = models.CharField(max_length=254)
	pol_sect = models.CharField(max_length=254)
	beatid = models.CharField(max_length=254)
	
# 	action = models.CharField(max_length=254) # constant="P"
# 	agency = models.CharField(max_length=254) # constant="OP"
# 	message = models.CharField(max_length=254) # constant="0"
# 	sourcethm = models.CharField(max_length=254) # constant="Pb"

	acres = models.CharField(max_length=254)
	shape_area = models.CharField(max_length=254)
	shape_len = models.CharField(max_length=254)
	geom = models.MultiPolygonField(srid=4326)

# Auto-generated `LayerMapping` dictionary for OPDBeatMap model
OPDBeatmap_mapping = {
	'name': 'Name',
# 	'descriptio': 'descriptio',
# 	'timestamp': 'timestamp',
# 	'begin': 'begin',
# 	'end': 'end',
# 	'altitudemo': 'altitudeMo',
# 	'tessellate': 'tessellate',
# 	'extrude': 'extrude',
# 	'visibility': 'visibility',
# 	'draworder': 'drawOrder',
# 	'icon': 'icon',
# 	'name_1': 'Name_1',
# 	'objectid': 'OBJECTID',
	'cp_beat': 'CP_BEAT',
	'pol_beat': 'POL_BEAT',
	'pol_dist': 'POL_DIST',
	'pol_sect': 'POL_SECT',
	'beatid': 'ID',
# 	'action': 'ACTION',
# 	'agency': 'AGENCY',
# 	'message': 'MESSAGE',
# 	'sourcethm': 'SOURCETHM',
	'acres': 'ACRES',
	'shape_area': 'SHAPE_AREA',
	'shape_len': 'SHAPE_LEN',
	'geom': 'MULTIPOLYGON',
}

# 180712
# python manage.py  ogrinspect /Data/c4a-Data/OAK_data/maps_oakland/cb_2015_06_tract_500k/cb_2015_06_tract_500k.shp CensusTract --srid=4269 --mapping --multi
class CensusTract(models.Model):
	statefp = models.CharField(max_length=2)
	countyfp = models.CharField(max_length=3)
	tractce = models.CharField(max_length=6)
	affgeoid = models.CharField(max_length=20)
	geoid = models.CharField(max_length=11)
	name = models.CharField(max_length=100)
	lsad = models.CharField(max_length=2)
	aland = models.BigIntegerField()
	awater = models.BigIntegerField()
	geom = models.MultiPolygonField(srid=4269)


# Auto-generated `LayerMapping` dictionary for CensusTract model
Censustract_mapping = {
	'statefp': 'STATEFP',
	'countyfp': 'COUNTYFP',
	'tractce': 'TRACTCE',
	'affgeoid': 'AFFGEOID',
	'geoid': 'GEOID',
	'name': 'NAME',
	'lsad': 'LSAD',
	'aland': 'ALAND',
	'awater': 'AWATER',
	'geom': 'MULTIPOLYGON',
}