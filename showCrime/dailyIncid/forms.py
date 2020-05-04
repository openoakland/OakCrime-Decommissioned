from django import forms

from .models import TargetPlace

BeatChoices = ( ('01X','01X'), ('02X','02X'), ('02Y','02Y'), ('03X','03X'), ('03Y','03Y'), ('04X','04X'), 
	('05X','05X'), ('05Y','05Y'), ('06X','06X'), ('07X','07X'), ('08X','08X'), ('09X','09X'), ('10X','10X'), 
	('10Y','10Y'), ('11X','11X'), ('12X','12X'), ('12Y','12Y'), ('13X','13X'), ('13Y','13Y'), ('13Z','13Z'), 
	('14X','14X'), ('14Y','14Y'), ('15X','15X'), ('16X','16X'), ('16Y','16Y'), ('17X','17X'), ('17Y','17Y'), 
	('18X','18X'), ('18Y','18Y'), ('19X','19X'), ('20X','20X'), ('21X','21X'), ('21Y','21Y'), ('22X','22X'), 
	('22Y','22Y'), ('23X','23X'), ('24X','24X'), ('24Y','24Y'), ('25X','25X'), ('25Y','25Y'), ('26X','26X'), 
	('26Y','26Y'), ('27X','27X'), ('27Y','27Y'), ('28X','28X'), ('29X','29X'), ('30X','30X'), ('30Y','30Y'), 
	('31X','31X'), ('31Y','31Y'), ('31Z','31Z'), ('32X','32X'), ('32Y','32Y'), ('33X','33X'), ('34X','34X'), 
	('35X','35X'), ('35Y','35Y') )

CrimeCatChoices = (
	('ARSON','ARSON'),
	('ASSAULT','ASSAULT'),
	('ASSAULT_BATTERY','ASSAULT_BATTERY'),
	('ASSAULT_FIREARM','ASSAULT_FIREARM'),
	('ASSAULT_KNIFE','ASSAULT_KNIFE'),
	('ASSAULT_MISDEMEANOR','ASSAULT_MISDEMEANOR'),
	('ASSAULT_OTHER-WEAPON','ASSAULT_OTHER'),
	('ASSAULT_THREATS','ASSAULT_THREATS'),
	('COURT','COURT'),
	('COURT_CUSTODY','COURT_CUSTODY'),
	('COURT_MISDEMEANOR','COURT_MISDEMEANOR'),
	('COURT_ORDER','COURT_ORDER'),
	('COURT_PAROLE','COURT_PAROLE'),
	('COURT_PROBATION','COURT_PROBATION'),
	('COURT_WARRANT','COURT_WARRANT'),
	('DOM-VIOL','DOM-VIOL'),
	('DOM-VIOL_BATTERY','DOM-VIOL_BATTERY'),
	('DOM-VIOL_BATTERY-SPOUSE','DOM-VIOL_BATTERY-SPOUSE'),
	('DOM-VIOL_CHILD','DOM-VIOL_CHILD'),
	('HOMICIDE','HOMICIDE'),
	('HOMICIDE_UNEXPLAINED','HOMICIDE_UNEXPLAINED'),
	('KIDNAPPING','KIDNAPPING'),
	('LARCENY','LARCENY'),
	('LARCENY_BURGLARY','LARCENY_BURGLARY'),
	('LARCENY_BURGLARY_AUTO','LARCENY_BURGLARY_AUTO'),
	('LARCENY_BURGLARY_COMMERCIAL','LARCENY_BURGLARY_COMMERCIAL'),
	('LARCENY_BURGLARY_OTHER','LARCENY_BURGLARY_OTHER'),
	('LARCENY_BURGLARY_RESIDENTIAL','LARCENY_BURGLARY_RESIDENTIAL'),
	('LARCENY_EMBEZZLEMENT','LARCENY_EMBEZZLEMENT'),
	('LARCENY_FORGERY-COUNTERFEIT','LARCENY_FORGERY'),
	('LARCENY_FRAUD','LARCENY_FRAUD'),
	('LARCENY_POSSESSION','LARCENY_POSSESSION'),
	('LARCENY_RECEIVED','LARCENY_RECEIVED'),
	('LARCENY_THEFT','LARCENY_THEFT'),
	('LARCENY_THEFT_GRAND','LARCENY_THEFT_GRAND'),
	('LARCENY_THEFT_PETTY','LARCENY_THEFT_PETTY'),
	('LARCENY_THEFT_VEHICLE','LARCENY_THEFT_VEHICLE'),
	('LARCENY_THEFT_VEHICLE_ATTEMPTED','LARCENY_THEFT_VEHICLE_ATTEMPTED'),
	('LARCENY_THEFT_VEHICLE_AUTO','LARCENY_THEFT_VEHICLE_AUTO'),
	('LARCENY_THEFT_VEHICLE_CAR-JACKING','LARCENY_THEFT_VEHICLE_CAR'),
	('OTHER','OTHER'),
	('OTHER_RECOVERED','OTHER_RECOVERED'),
	('OTHER_RUNAWAY','OTHER_RUNAWAY'),
	('QUALITY','QUALITY'),
	('QUALITY_DISORDERLY-CONDUCT','QUALITY_DISORDERLY'),
	('QUALITY_DRUG','QUALITY_DRUG'),
	('QUALITY_DRUG_POSSESSION','QUALITY_DRUG_POSSESSION'),
	('QUALITY_DRUG_POSSESSION_MARIJUANA','QUALITY_DRUG_POSSESSION_MARIJUANA'),
	('QUALITY_DRUG_SALE-MFCTR','QUALITY_DRUG_SALE'),
	('QUALITY_LIQUOR','QUALITY_LIQUOR'),
	('QUALITY_TELEPHONE','QUALITY_TELEPHONE'),
	('QUALITY_TRESPASS','QUALITY_TRESPASS'),
	('RAPE','RAPE'),
	('ROBBERY','ROBBERY'),
	('ROBBERY_ATTEMPTED','ROBBERY_ATTEMPTED'),
	('ROBBERY_FIREARM','ROBBERY_FIREARM'),
	('ROBBERY_INHABITED-DWELLING','ROBBERY_INHABITED'),
	('ROBBERY_KNIFE','ROBBERY_KNIFE'),
	('ROBBERY_OTHER-WEAPON','ROBBERY_OTHER'),
	('ROBBERY_STRONG-ARM','ROBBERY_STRONG'),
	('SEX','SEX'),
	('SEX_CHILD','SEX_CHILD'),
	('SEX_OTHER','SEX_OTHER'),
	('SEX_PROSTITUTION','SEX_PROSTITUTION'),
	('TRAFFIC','TRAFFIC'),
	('TRAFFIC_DUI','TRAFFIC_DUI'),
	('TRAFFIC_HIT-RUN','TRAFFIC_HIT'),
	('TRAFFIC_MISDEMEANOR','TRAFFIC_MISDEMEANOR'),
	('TRAFFIC_OTHER','TRAFFIC_OTHER'),
	('TRAFFIC_TOWED-VEHICLE','TRAFFIC_TOWED'),
	('VANDALISM','VANDALISM'),
	('WEAPONS','WEAPONS') )

class simpleQ(forms.Form):
	
	# idx = forms.IntegerField()
	beat = forms.ChoiceField(choices=BeatChoices)
	
	# 2do: replace with hierarchic widget
	## django-mptt, jquery, ...?
	crimeCat = forms.ChoiceField(choices=CrimeCatChoices)  
	
	def __unicode__(self):
		return '%s+%s' % (self.beat,self.crimeCat)


class twoTypeQ(forms.Form):
	
	# idx = forms.IntegerField()
	beat = forms.ChoiceField(choices=BeatChoices)
	
	# 2do: replace with hierarchic widget
	## django-mptt, jquery, ...?
	crimeCat = forms.ChoiceField(choices=CrimeCatChoices)  

	secondCatChoice = ( ('', '<none>'), ) + CrimeCatChoices
	
	crimeCat2 = forms.ChoiceField(choices=secondCatChoice,required=False)  
	
	def __unicode__(self):
		if not(self.crimeCat2 == None or self.crimeCat2 == ''):
			return '%s+%s+%s' % (self.beat,self.crimeCat,self.crimeCat2)
		else:
			return '%s+%s' % (self.beat,self.crimeCat)

class getLatLng(forms.Form):
	'''simple form to collect lat/long
	'''

	# Centroid of MCAR's three entrances
	# 37.828199, -122.265944 
	# 37 degrees 49'41.5"N 122 degrees 15'57.4"W
	MCAR_lat = 37.828199
	MCAR_lng = -122.265944
	
	minLng = -122.3; maxLat = 37.9 	# NW corner
	maxLng = -122.0; minLat = 37.65 # SE corner

	lat = forms.FloatField(initial=MCAR_lat,min_value=minLat,max_value=maxLat)
	lng = forms.FloatField(initial=MCAR_lng,min_value=minLng,max_value=maxLng)
	
	def __unicode__(self):
		return 'Lat:%f;Lng:%f' % (self.lat,self.lng)

class getPlaceList(forms.Form):
	'''get particular place's lat/lng
	'''
		
	placeList = forms.ModelChoiceField(queryset=None,
									# 'actionform.submit();' 'refresh()'
									widget=forms.Select(attrs={'onchange': 'submit()' }))
	
	def __init__(self, *args, **kwargs):
		# https://stackoverflow.com/a/5329761/1079688

		ptype = kwargs.pop('ptype', None)
		super(getPlaceList, self).__init__(*args, **kwargs)

		if ptype:
			qs = TargetPlace.objects.filter(placeType=ptype)
			# qsl = [ (tp.ylat,tp.xlng,tp.name,tp.desc) for tp in list(qs) ]
			
			self.fields['placeList'].queryset = qs

	def __unicode__(self):
		return '%s' % (self.placeList)


		
