# ShowCrime: Visualizing Oakland Police Department Daily Incident data

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

Older OakCrime datasets in (CSV, JSON and sqlite formats) remain
available http://data.openoakland.org/dataset/crime-reports in csv
file formats, but these have not been updated since late 2016.

### Environment Variables for Dev
```
export DATABASE_URL=postgis://oakCrime:oakCrime@localhost:5432/postgres?connect_timeout=60
export DEBUG=true
export LOG_FILE_PATH=/logs/showCrime
export PLOT_PATH=/plots
export PUBLIC_ROOT=/public/showCrime
export SITE_URL=http://localhost:8000
export SECRET_KEY="Change me in the real world"
```
