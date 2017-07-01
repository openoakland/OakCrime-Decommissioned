"""showCrime.dailyIncid.models.py:

updated 23 Mar 17: include GIS, 
updated 20 Jun 17: combine dateTime, add source
"""

__author__ = "rik@electronicArtifacts.com", "actionspeakslouder@gmail.com"
__version__ = "0.3"

from django.contrib.gis.db import models

class OakCrime(models.Model):
	# non-NULL fields
	idx = models.AutoField(primary_key=True)
	opd_rd = models.CharField(max_length=10,db_index=True)
	oidx = models.IntegerField()
	cdateTime = models.DateTimeField(db_index=True)
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
	

