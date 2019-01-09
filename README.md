[![CircleCI](https://circleci.com/gh/rbelew/OakCrime.svg?style=svg)](https://circleci.com/gh/rbelew/OakCrime)

OakCrime
========

Code supporting citizen analysis of crime in Oakland, CA

Primary bits involve:

* importing data from Oakland Police Department (OPD), an early data set from Urban Strategies Council, and Alameda County

* crimeCat: software defining and building an ontology of crime types useful with OPD data and perhaps beyond!

* showCrime, a django site for visualization of historical crime data

* stopData, visualization of discretionary stop data


## Prequisites

We assume you already have these installed:

- [Python](https://www.python.org/) 3.6+
- [Postgres](https://www.postgresql.org/)


## Continuous integration

We're using [CircleCI](https://circleci.com/) for continuous integration (CI).
Continuous integration automatically tests that any new changes work correctly
before they are fully integrated. This provides a faster feedback loop and helps
prevent bugs or mistakes from getting caught late in development.


## Contributing

Thank you for considering a contribution to our project! Please see
[CONTRIBUTING.md](CONTRIBUTING.md) on how the OakCrime team works and how you
can contribute.
