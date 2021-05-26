## Project status: DECOMMISSIONED

This project has been decommissioned and is no longer maintained. It presents policing-related data from OPD without appropriate context, which may result in viewers misunderstanding or mischaracterizing data in ways that potentially impact historically marginalized and oppressed groups, particularly communities of color. If you're interested in revising this project, please contact OpenOakland's Steering Committee at [steering@openoakland.org](mailto:steering@openoakland.org). Let us know why you're interested and what you hope to accomplish. Consider using the [Project Exploration Worksheet](https://docs.google.com/document/d/1k24P9JiAUEzJLPFRDjVh7aRZexax6NUhfPFLSI3R80M/edit?usp=sharing) to realign this project with OpenOakland's mission and values.


OakCrime
========
[![CircleCI](https://circleci.com/gh/openoakland/OakCrime.svg?style=svg)](https://circleci.com/gh/openoakland/OakCrime)

Code supporting citizen analysis of crime in Oakland, CA

Primary bits involve:

* importing data from Oakland Police Department (OPD), an early data set from Urban Strategies Council, and Alameda County

* crimeCat: software defining and building an ontology of crime types useful with OPD data and perhaps beyond!

* showCrime, a django site for visualization of historical crime data

* stopData, visualization of discretionary stop data


## Prequisites

We assume you already have these installed:

- [Docker Compose](https://docs.docker.com/compose/) v1.x
- [Docker](https://www.docker.com/) v18.x
- [Make](https://www.gnu.org/software/make/)
- [Postgres](https://www.postgresql.org/) v10.x
- [Python](https://www.python.org/) 3.6+

_MacOS users: you'll find most of these tools in [Homebrew](https://brew.sh)._


## Setup

The main project is the django application. Please follow the instructions in
[showCrime/README](showCrime/README.md).


## Continuous integration

We're using [CircleCI](https://circleci.com/) for continuous integration (CI).
Continuous integration automatically tests that any new changes work correctly
before they are fully integrated. This provides a faster feedback loop and helps
prevent bugs or mistakes from getting caught late in development.


## Continuous delivery

We use continuous delivery (CD) to automatically deploy our application. This
reduces the risk of human error and makes sure the latest version of the
application is deployed correctly.

Any commits to the `master` branch are deployed automatically to [AWS Elastic
Beanstalk](https://aws.amazon.com/elasticbeanstalk/) courtesy of [Open
Oakland](http://openoakland.org/).


## Contributing

Thank you for considering a contribution to our project! Please see
[CONTRIBUTING.md](CONTRIBUTING.md) on how the OakCrime team works and how you
can contribute.
