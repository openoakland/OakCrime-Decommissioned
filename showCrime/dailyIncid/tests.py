from django.test import TestCase

from .models import OakCrime
from .management.commands import harvestSocrata

class TestDailyIncid(TestCase):

    def test_model_oakcrime(self):
        # This isn't much of a test since the import worked
        assert OakCrime

    def test_harvest_socrata_cleanOPDtext(self):
        assert harvestSocrata.cleanOPDtext(' input ') == 'input', 'white space should be striped'
        assert harvestSocrata.cleanOPDtext('one two') == 'one_two', 'spaces should be converted'
