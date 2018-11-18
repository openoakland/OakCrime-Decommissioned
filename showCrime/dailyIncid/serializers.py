''' serializers
Created on Mar 26, 2017

@author: rik
'''

from dailyIncid.models import OakCrime
from rest_framework import serializers


class IncidSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OakCrime
        fields = ('opd_rd', 'cdateTime', 'beat', 'xlng', 'ylat', 'crimeCat')
