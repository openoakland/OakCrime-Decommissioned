OakCrime
========

Code supporting citizen analysis of crime in Oakland, CA

Primary bits involve:

* importing data from Oakland Police Department (OPD), an early data set from Urban Strategies Council, and Alameda County

* crimeCat: software defining and building an ontology of crime types useful with OPD data and perhaps beyond!

* showCrime, a django site for visualization of historical crime data

* stopData, visualization of discretionary stop data

## Working on showCrime (django app)

### Setup a virtualenv for python dependencies:

```bash
python3 -m venv showCrime/oakcrime_venv
```

### Activate the virtualenv to start work:

```bash
source showCrime/oakcrime_venv/bin/activate
cd showCrime
```

### Install dependencies:
```bash
pip install -r requirements.txt
# install system packages. for ubuntu:
sudo apt-get install python3-tk
sudo apt-get install libpq-dev
sudo apt-get install libgdal-dev
```

### Start local postgres database:

Uses docker:

```bash
# initial run, creates container named showCrimeDB
docker run --name showCrimeDB -e POSTGRES_PASSWORD=oakCrime -e POSTGRES_USER=oakCrime -p 5432:5432 -d mdillon/postgis
# stop the container
docker stop showCrimeDB
# start the container 
docker start showCrimeDB
```

### Extra setup steps:

```bash
# run database migrations
./manage.py migrate
# create yourself an admin user to login with
./manage.py createsuperuser
```

### Loading OPD data

First retrieve a csv file from http://data.openoakland.org/dataset/crime-reports in csv file format

Then use the dropSource4django.py script (not commited at present) to convert to another csv file suitable for use in our db. You will need to edit the file paths in this script to reflect where you currently have the data.

```bash
# Connect via psql to docker-contained db.
psql -h localhost -U oakCrime # You will be prompted for password.

# Then, inside the psql session
\copy crime_main_oakcrime FROM OPD_FILENAME DELIMITER ',' CSV HEADER
update crime_main_oakcrime SET latlong = ST_SetSRID(ST_MakePoint(long, lat), 4326)
```


### Run dev server:

```bash
./manage.py runserver
# visit localhost:8000 to view site
```

### Example Distance Queries

See the geodjango project for more: https://docs.djangoproject.com/en/1.10/ref/contrib/gis/

```bash
./manage.py shell
```

In the shell:
```python
from crime_main.models import OakCrime
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D

pnt = GEOSGeometry('POINT(-122.251646 37.843534)', srid=4326)

recs = OakCrime.objects.filter(latlong__distance_lte=(pnt, D(km=1)))
```
