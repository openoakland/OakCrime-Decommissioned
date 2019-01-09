Show Crime
==========

`Below are notes for each file in showCrime that can help when understanding the codebase for Show Crime. (This is still incomplete please fill in the blanks, correct mistakes, or change format for better readability.)
 Also, documentation for understanding the data can be found at the following link: http://rikiwiki.electronicartifacts.com/opd-crime-statistics/its-showcrime
`

- admin.py

Purpose: ? (Some sort of bootstrap which calls admin from django.contri package)

Contains OakCrimeAdmin class, which calls admin.site.register(OakCrime, OakCrimeAdmin).

This OakCrimeAdmin class contains fieldsets, list_display, and list_filter.

- forms.py

Purpose: Contains forms for the UI.

Contains simpleQ and twoTypeQ class. These are two different types of forms used by the frontend.

They are populated using BeatChoices and CrimeCatChoices

- models.py

Purpose: Contains the model(s) for showCrime. Documentation for understanding the data can be found at this link http://rikiwiki.electronicartifacts.com/opd-crime-statistics/its-showcrime

Contains OakCrime model whose schema is defined below:

- idx = models.IntegerField(primary_key=True) // index
- opd_rd = models.CharField(max_length=10) // oakland police department rd? what is rd?
- oidx = models.IntegerField() // what is oidx; o index?
- cdate = models.DateField() // cdate; what is c?
- ctime = models.TimeField() // ctime; what is c?
- ctype = models.CharField(max_length=50,blank=True,null=True) // ctype; what is c?
- desc = models.CharField(max_length=200,blank=True,null=True) // description
- beat = models.CharField(max_length=20,blank=True,null=True) // beat; a beat corresponds to a small fraction of Oakland city
- addr = models.CharField(max_length=100,blank=True,null=True) // address 
- lat = models.FloatField(null=True) // latitude
- long = models.FloatField(null=True) // longitude
- ucr = models.CharField(max_length=5,blank=True,null=True) // what is ucr?
- statute = models.CharField(max_length=50,blank=True,null=True) // statute; a written law passed by a legislative body.
- crimeCat = models.CharField(max_length=50,blank=True,null=True) // crime category. You can find many of this category in forms.py under CrimeCatChoices.

- urls.py

Not sure what this does.

- urlpatterns = patterns('',
- url(r'^$', views.index, name='index'),
- url(r'^tstImage.JPG$', views.showImage, name='showImage'),
- url(r'^query/$', views.getQuery, name='query'),
- url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+).png$', views.plotResults, name='plotResults' ),
- url(r'^plots/(?P<beat>\w+)\+(?P<crimeCat>[\w_-]+)\+(?P<crimeCat2>[\w_-]+).png$', views.plotResults, name='plotResult2' ),
-)

- views.py

Contains request handling for application. For example:

def index(request):

def showImage(request):

Also, views.py captures user input via form/dropdown and helps create the query needed to generate a plot with
input given from the user. (Uses twoTypeQ from forms.py)


views.py also contains a matlib helper on the bottom.

which contains 

def monthIdx(cdate):

def monthIdx1(dateStr):

def plotResults(request,beat,crimeCat,crimeCat2=None):








