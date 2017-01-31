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

### Run dev server:

```bash
./manage.py runserver
# visit localhost:8000 to view site
```


