''' opdConstant:  constants assumed by opdata
Created on Nov 15, 2016

@author: rik
'''
import datetime
import re

MinYear = 2007
MaxYear = 2016
     
Desc2CatTbl = None
Statute2DescTbl = None
Desc2statTbl = None
LigandZeroSuffix = False

whitespace_pat = re.compile(r'\s+')

MinFreq = 10
MaxGoogleReq =  1 # 1000 # 2500

# DataDir = '/Data/corpora/c4a_oakland/'

OPD_date_string = '%Y-%m-%d %H:%M:%S'
OPD_PRR_date_string = '%m/%d/%Y %H:%M' # 3/22/2007 16:09
USC_date_string = '%m/%d/%Y'
C4A_dateTime_string = '%y%m%d_%H:%M:%S'
C4A_date_string = '%Y-%m-%d'
C4A_time_string = '%H:%M:%S'
C4A_dateTime_string2 = C4A_date_string+'_'+C4A_time_string

Socrata_date_string = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
DefaultDate = datetime.datetime(1999,1,1)
DefaultYear = 1999

CrimeLexTbl = {# categories
			   'murder' : ['MURDER'],
			   'rape' : ['RAPE'],
			   'kidnap' : ['KIDNAPPING'],
			   'assault' : ['ASSAULT'],
			   # NB, robbery \in burglary 
			   'robbery' : ['ROBBERY', 'GRAND THEFT'],
			   'burglary' : ['BURGLARY', 'THEFT'], 
			   'vandal' : ['VANDALISM'],
			   'court'  : ['COURT', 'WARRANT', 'PAROLE', 'PROBATION'],
			   # attributes
			   'firearm' : ['FIREARM', 'F/ARM', 'GUN', 'SHOOT'],
			   'drugs' : ['SUBSTANCE', 'METH', 'COCAINE', 'NARCOTIC', 'DRUG'],
			   'pot' : ['MARIJUANA', 'CANNABIS'],
			   'booz' : ['ALCOHOL', 'DUI'],
			   'auto' : ['AUTO', 'VEHICLE'],
			   'minor' : ['MINOR', 'JUVENILE', 'CHILD', 'UNDER 14']
			   }

AddrGeoFileTbl = {'address-geocode_maxo.csv':	 ['_id','_rev','ADDR','CID[0]','NCID','latitude','longitude'], 
				  'address-geocode_140331.csv': ['ADDR','CID[0]','NCID','latitude','longitude'], 

				  'CS_geo_2008_01.csv':		[ 'OrigAddr','NewAddr','Zip','Lat','Lng','Accuracy'],
				  
				  'CS_geo.csv':				['OrigAddr','NewAddr','Zip','Lat','Lng','Accuracy'], 

				  'CS_geo_new_150118.csv':	 [ 'OrigAddr','NewAddr','Zip','Lat','Lng','Accuracy'], 
				  'CS_geo_new_150221.csv':	 [ 'OrigAddr','NewAddr','Zip','Lat','Lng','Accuracy'] }


KnownBadAddr = ['','O/S','NOT GIVEN','UNKNOWN LOCATION', \
			'UNKNOWN ADDRESS','UNKNOWN LOCATION IN OAKLAND',
			'UNKNOWN, OAKLAND, CA,']

OaklandMinLong,OaklandMinLat = (-122.335895, 37.4716609849)
OaklandMaxLong,OaklandMaxLat = (-121.7269551349, 37.9011911424)

CT2StatThresh = 0.95
Stat2UCRThresh = 0.95

Beat2DistrictTbl = {
	'01X':1, '02X':1, '02Y':1, '03X':1, '03Y':1, '04X':1,'05X':1, '05Y':1, '06X':1, '07X':1,
	'08X':2, '09X':2, '10X':2, '10Y':2, '11X':2, '12X':2, '12Y':2,'13X':2, '13Y':2, '13Z':2,
	'14X':3, '14Y':3, '15X':3, '16X':3, '16Y':3, '17X':3, '17Y':3,'18X':3, '18Y':3, '19X':3, '20X':3, '21X':3, '21Y':3, '22X':3,'22Y':3,
	'23X':4, '24X':4, '24Y':4, '25X':4, '25Y':4, '26X':4, '26Y':4,'27X':4, '27Y':4, '28X':4,
	'29X':5, '30X':5, '30Y':5, '31X':5, '31Y':5, '31Z':5, '32X':5,'32Y':5, '33X':5, '34X':5, '35X':5, '35Y':5
	}


GoodBeats = ['01X', '02X', '02Y', '03X', '03Y', '04X', '05X', '05Y', '06X', '07X',
			'08X', '09X', '10X', '10Y', '11X', '12X', '12Y', '13X', '13Y', '13Z',
			'14X', '14Y', '15X', '16X', '16Y', '17X', '17Y', '18X', '18Y', '19X',
			'20X', '21X', '21Y', '22X', '22Y', '23X', '24X', '24Y', '25X', '25Y',
			'26X', '26Y', '27X', '27Y', '28X', '29X', '30X', '30Y', '31X', '31Y',
			'31Z', '32X', '32Y', '33X', '34X', '35X', '35Y']

OPD_HierCat = ['OPD_ARSON',
		  'OPD_ASSAULT',
		  'OPD_DRUG',
		  'OPD_HOMICIDE',
		  'OPD_LARCENY',
		  'OPD_LARCENY_THEFT',
		  'OPD_RAPE',
		  'OPD_ROBBERY',
		  'OPD_OTHER']

OPD_MiscCat = ['OPD_CURFEW',
		'OPD_DISORDERLY-CONDUCT',
		'OPD_LIQUOR',
		'OPD_PROSTITUTION-VICE',
		'OPD_SEX',
		'OPD_VANDALISM',
		'OPD_WEAPONS']

# 01/10/14,11:15:00 PM
CM_date_string = '%m/%d/%Y'
CM_dateTime_string = '%m/%d/%Y %I:%M %p'
