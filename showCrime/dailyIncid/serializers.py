''' serializers
Created on Mar 26, 2017

@author: rik
'''

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from dailyIncid.models import OakCrime

class IncidSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OakCrime
        fields = ('opd_rd', 'cdate', 'ctime', 'beat', 'ylat', 'xlng' ,'crimeCat')
        
