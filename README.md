OakCrime
========

Code supporting citizen analysis of crime in Oakland, CA

Primary bits involve:

* importing data from Oakland Police Department (OPD), an early data set from Urban Strategies Council, and Alameda County

* crimeCat: software defining and building an ontology of crime types useful with OPD data and perhaps beyond!

* showCrime, a django site for visualization of historical crime data

* stopData, visualization of discretionary stop data

## Working on showCrime (django app)

Setup a virtualenv for python dependencies:

```bash
python3 -m venv showCrime/oakcrime_venv
```

Activate the virtualenv to start work:

```bash
source showCrime/oakcrime_venv/bin/activate
cd showCrime
```

Install dependencies:
```bash
pip install -r requirements.txt
# install system packages. for ubuntu:
sudo apt-get install python3-tk
```


