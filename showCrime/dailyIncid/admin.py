from django.contrib import admin
from django.contrib.gis.admin import GeoModelAdmin

from .models import OakCrime

# admin.site.register(OakCrime)

#You'll follow this pattern - create a model admin object, 
#then pass it as the second argument to admin.site.register() 
#any time you need to change the admin options for an object.

# NB: use GeoModelAdmin
class OakCrimeAdmin(GeoModelAdmin):
#    fields = ['idx', 'opd_rd', 'oidx', 'cdate', 'ctype', 'desc', \
#              'beat', 'addr', 'ylat', 'xlng', 'ucr', 'statute', 'crimeCat']
    
    fieldsets = [
        ('Meta',    {'fields': ['idx', 'oidx']}),
        ('OPD',     {'fields': ['opd_rd','cdateTime', 'source', 'ctype', 'desc','beat', 'addr']}),
        ('Inferred', {'fields': ['ylat', 'xlng', 'point', 'ucr', 'statute', 'crimeCat']}),
    ]
    
    list_display = ('opd_rd','cdateTime', 'beat', 'crimeCat')
    list_filter = ['crimeCat','beat']
    
    # 2d0:  search seems kinda broken?
    # search_fields = ['opd_rd','desc','addr']
    
    # 2do:  make cdate conformant
    # date_hierarchy = 'pub_date'


admin.site.register(OakCrime, OakCrimeAdmin)
