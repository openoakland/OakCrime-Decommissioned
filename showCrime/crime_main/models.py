"""djOakData.showCrime.models.py: """

__author__ = "rik@electronicArtifacts.com"
__version__ = "0.1"

from django.contrib.gis.db import models

class OakCrime(models.Model):
    idx = models.IntegerField(primary_key=True)
    opd_rd = models.CharField(max_length=10)
    oidx = models.IntegerField()
    # 2do: make this a datetime object, to exploit great widgets
    # cf. .../django-docs-1.5-en/intro/tutorial01.html
    cdate = models.DateField()
    ctime = models.TimeField()
    ctype = models.CharField(max_length=100,blank=True,null=True)
    desc = models.CharField(max_length=200,blank=True,null=True)
    beat = models.CharField(max_length=20,blank=True,null=True)
    addr = models.CharField(max_length=100,blank=True,null=True)
    lat = models.FloatField(null=True)
    long = models.FloatField(null=True)
    latlong = models.PointField(null=True)
    ucr = models.CharField(max_length=5,blank=True,null=True)
    statute = models.CharField(max_length=50,blank=True,null=True)
    crimeCat = models.CharField(max_length=50,blank=True,null=True)
    
    def __unicode__(self):
        return '%d:%s' % (self.idx,self.opd_rd)
