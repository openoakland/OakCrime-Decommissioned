from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from forms import *
from models import *

def index(request):
    template = loader.get_template('showCrime/index.html')
    context = Context({})
    return HttpResponse(template.render(context))

def testPage(request):
    return HttpResponse("Hello, world. You're at showCrime test.")

def showImage(request):
    
    imagePath = "/Users/rik/Code/eclipse/djOakData/showCrime/tstImage.png"
    from PIL import Image
    Image.init()
    i = Image.open(imagePath)
    
    response = HttpResponse(mimetype='image/png')
    
    i.save(response,'png')
    return response

@login_required
def getQuery(request):
    
    # import pdb; pdb.set_trace()
    if request.method == 'POST':
        qform = twoTypeQ(request.POST)
        if qform.is_valid():
            qryData = qform.cleaned_data
            if qryData['crimeCat2']:
                qurl = '/showCrime/plots/%s+%s+%s.png' % (qryData['beat'],qryData['crimeCat'],qryData['crimeCat2'])
            else:
                qurl = '/showCrime/plots/%s+%s.png' % (qryData['beat'], qryData['crimeCat']) 
            return HttpResponseRedirect(qurl)
    else:
        qform = twoTypeQ()
        
    return render(request, 'showCrime/getQuery.html', {'form': qform})
       
import pylab as p
import os

import matplotlib
# Force matplotlib to not use any Xwindows backend.
# changed in webapps/django/lib/python2.7/matplotlib/mpl-data/matplotlibrc
# matplotlib.use('Agg')

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
from datetime import datetime,timedelta,date
import matplotlib.dates as mdates


# 2do:  reconcile djOakData code with c4a
MinYear = 2007
MaxYear = 2012
C4A_date_string = '%y%m%d_%H:%M:%S'

# local
# PlotPath = "/Users/rik/Code/eclipse/djOakData/plots/"
# WebFaction
PlotPath = "/home/rik/webapps/eastatic/oakDataPlots/"


def monthIdx(cdate):
    mon = cdate.month+12*(cdate.year - MinYear) - 1
    return mon

def monthIdx1(dateStr):
    cdate = datetime.strptime( dateStr, C4A_date_string)
    mon = cdate.month+12*(cdate.year - MinYear) - 1
    return mon    

def plotResults(request,beat,crimeCat,crimeCat2=None):
 
    ## build data vectors
    
    # 2do precompute, cache city-wide stats for all crimeCat
    
    if crimeCat2=='None':
        fname = '%s+%s' % (beat,crimeCat)
    else:
        fname = '%s+%s+%s' % (beat,crimeCat,crimeCat2)
    
    # Alternative: cache precomputed plots?
    
#    if os.path.isfile(PlotPath+fname+'.png'):
#        # 2do:  how to get figure from file?
#        img = getImage(PlotPath+fname+'.png')
#        canvas = FigureCanvas(img)
#        response = HttpResponse(content_type='image/png')
#        canvas.print_png(response)
#        return response

    nbins = 12 * ((MaxYear-MinYear)+1)
    cityFreq = [0 for m in range(nbins) ]
    beatFreq = [0 for m in range(nbins) ]
      
    # NB: using regexp comparison with crimeCat prefix for cheapo hierarchy!
    
    # NB: need to include primary key (idx), cuz of deferred status from raw() ?
    
    # http://stackoverflow.com/questions/3105249/python-sqlite-parameter-substitution-with-wildcards-in-like
    startsCC = '^%s' % crimeCat

    # local
    # qryStr = "SELECT idx, cdate, beat FROM showCrime_oakcrime where crimeCat regexp %s"
    # WebFaction
    qryStr = 'SELECT idx, cdate, beat FROM "showCrime_oakcrime" where "crimeCat" ~ %s'

    begQTime = datetime.now()
    for c in OakCrime.objects.raw(qryStr,[startsCC]):
    # for c in OakCrime.objects.raw(qryStrBAD):
        cd = c.cdate
        cb = c.beat
        mi = monthIdx(cd)
        if mi < 0 or mi > len(cityFreq):
            continue
        cityFreq[mi] += 1
        if beat==cb:
            beatFreq[mi] += 1

    if crimeCat2!='None':
        cityFreq2 = [0 for m in range(nbins) ]
        beatFreq2 = [0 for m in range(nbins) ]
            
        startsCC2 = '^%s' % crimeCat2
    
        # local
        qryStr2 = "SELECT idx, cdate, beat FROM showCrime_oakcrime where crimeCat regexp %s"
        # WebFaction
        # qryStr = 'SELECT idx, cdate, beat FROM "showCrime_oakcrime" where "crimeCat" ~ %s'
    
        for c in OakCrime.objects.raw(qryStr2,[startsCC2]):
        # for c in OakCrime.objects.raw(qryStrBAD):
            cd = c.cdate
            cb = c.beat
            mi = monthIdx(cd)
            if mi < 0 or mi > len(cityFreq):
                continue
            cityFreq2[mi] += 1
            if beat==cb:
                beatFreq2[mi] += 1
                
    qryTime = datetime.now()-begQTime
        
    NGoodBeats = 57 # cf opd.GoodBeats
    avgFreq = [float(cityFreq[m])/NGoodBeats for m in range(nbins)]
    
    totBeat = sum(beatFreq)
    totCity = sum(cityFreq)
    
    ## plot data
    
    f1 = p.figure()
    ax=f1.add_subplot(111)
        
    datemin = date(MinYear, 1, 1)
    datemax = date(MaxYear, 12, 1)
    dates = []
    for yr in range(MinYear,MaxYear+1):
        for mon in range(12):
            dates.append( date(yr,mon+1,1) )
    
    years    = mdates.YearLocator()   # every year
    months   = mdates.MonthLocator()  # every month
    yearsFmt = mdates.DateFormatter('%Y')
    
    # format the ticks
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(yearsFmt)
    ax.xaxis.set_minor_locator(months)
    ax.set_xlim(datemin, datemax)
   
    ### PLOT
    
    if crimeCat2=='None':
        ax.plot(dates,beatFreq,label=('Beat %s' % beat))
        ax.plot(dates,avgFreq,label='BeatAvg (OPD total/57)')
    else:
        totBeat2 = sum(beatFreq2)
        totCity2 = sum(cityFreq2)
        avgFreq2 = [float(cityFreq2[m])/NGoodBeats for m in range(nbins)]

        ax.plot(dates,beatFreq,'b',label=('%s - Beat %s' % (crimeCat, beat)))
        ax.plot(dates,avgFreq,'b:',label='%s - BeatAvg (OPD total/57)' % (crimeCat))

        ax.plot(dates,beatFreq2,'g',label=('%s - Beat %s' % (crimeCat2, beat)))
        ax.plot(dates,avgFreq2,'g:',label='%s - BeatAvg' % (crimeCat2))
                
    runTime = str(datetime.now())
    runTime = runTime[:runTime.index(' ')] # HACK: drop time
    
    plotName = fname.replace('+',' ')
    if crimeCat2=='None':
        lbl = ('OPD Monthly Crime: %s (Total %d / %d)' % (plotName,totBeat, totCity))
    else:
        lbl = ('OPD Monthly Crime: %s\n(Total %d / %d ; %d / %d)' % (plotName,totBeat, totCity,totBeat2, totCity2))
        
    p.title(lbl,fontsize=10)
    p.legend(loc='upper left',fontsize=8)

    annote = 'rik@electronicArtifacts.com'+' - '+runTime+\
        '\nOpenOakland.org -- a CodeForAmerica.org Brigade'
    p.text(0.65, 0.93,annote, \
                  horizontalalignment='left',verticalalignment='bottom', transform = ax.transAxes, \
                  fontsize=6 )
    
    f1.autofmt_xdate()
    
    figDPI=200
    fullPath = PlotPath+fname+'_'+runTime+'.png'
    print 'plotting %d/%d (%6.2f sec) to %s' % (totBeat,totCity,qryTime.total_seconds(),fullPath)
    f1.savefig(fullPath,dpi=figDPI)

    canvas = FigureCanvas(f1)
    response = HttpResponse(content_type='image/png')

    canvas.print_png(response)
    return response
