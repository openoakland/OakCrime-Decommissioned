""" loadAncil:  load additional files: CrimeCat, TargetPlaces
Created on Jun 29, 2017

@author: rik
"""

from django.core.management.base import BaseCommand
from postgres_copy import CopyMapping

from dailyIncid.models import *


class Command(BaseCommand):
    help = 'load target places (BART, parks, ...)'

    def add_arguments(self, parser):
        parser.add_argument('crimeCatPath', nargs='?')
        parser.add_argument('targetPlacePath', nargs='?')

    def handle(self, *args, **kwargs):
        ccpath = kwargs['crimeCatPath']
        tppath = kwargs['targetPlacePath']

        print('loadAncil: crimeCat from %s...' % (ccpath))

        c1 = CopyMapping(
            CrimeCat,
            ccpath,
            # And a dict mapping the  model fields to CSV headers
            # CSV header = CType, CC
            dict(ctypeDesc='CType', crimeCat='CC')
        )
        c1.save()
        print('loadAncil: NCrimeCat=%d' % (CrimeCat.objects.all().count()))
        print('loadAncil: targetPlace from %s ...' % (tppath))

        c2 = CopyMapping(
            TargetPlace,
            tppath,
            # And a dict mapping the  model fields to CSV headers
            # CSV header = placeType, ylat, xlng, name, desc
            dict(placeType='placeType', ylat='ylat', xlng='xlng', name='name', desc='desc')
        )
        c2.save()
        print('loadAncil: NTargetPlace=%d' % (TargetPlace.objects.all().count()))
