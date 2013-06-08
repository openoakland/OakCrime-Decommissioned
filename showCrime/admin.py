from django.contrib import admin
from models import OakCrime

# admin.site.register(OakCrime)

#You'll follow this pattern - create a model admin object, 
#then pass it as the second argument to admin.site.register() 
#any time you need to change the admin options for an object.

class OakCrimeAdmin(admin.ModelAdmin):
#    fields = ['idx', 'opd_rd', 'oidx', 'cdate', 'ctype', 'desc', \
#              'beat', 'addr', 'lat', 'long', 'ucr', 'statute', 'crimeCat']
    
    fieldsets = [
        ('Meta',    {'fields': ['idx', 'oidx']}),
        ('OPD',     {'fields': ['opd_rd','cdate', 'ctype', 'desc','beat', 'addr']}),
        ('Inferred', {'fields': ['lat', 'long', 'ucr', 'statute', 'crimeCat']}),
    ]
    
    list_display = ('cdate', 'beat', 'desc')
    list_filter = ['crimeCat']
    
    # 2d0:  search seems kinda broken?
    # search_fields = ['opd_rd','desc','addr']
    
    # 2do:  make cdate conformant
    # date_hierarchy = 'pub_date'


admin.site.register(OakCrime, OakCrimeAdmin)