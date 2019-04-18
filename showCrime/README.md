# ShowCrime: Visualizing Oakland Police Department Daily Incident data

# showCrime django app


## Setup

We use [Docker Compose](https://docs.docker.com/compose/) to ease development.
Each component (django app, http server, and database) are each in their own
container.

All instructions assume you're running from the `showCrime` directory.

    cd showCrime

Build the containers.

    make docker.build

Run the database migrations.

    docker-compose run --rm app make migrate

Build static files.

    docker-compose run --rm app make static

Start the containers.

    make docker.up

Open your web browser to [localhost:8000](http://localhost:8000).

### Make commands


#### make docker.build

Build/rebuild the container images.

#### make docker.pull

Pull the latest container images from the Docker registry.


#### make docker.down

Stop and remove the containers.


#### make docker.shell

Open a shell in the application container.


#### make docker.up

Start the containers and show the application logs.


### Extra setup steps

Create an admin user to login with.

    make docker.shell
    ./manage.py createsuperuser


### Loading OPD data

Older OakCrime datasets in (CSV, JSON and sqlite formats) remain
available http://data.openoakland.org/dataset/crime-reports in csv
file formats, but these have not been updated since late 2016.


## Harvest jobs

This section describes the various harvest jobs that fetch and process data that
powers OakCrime.


### harvestSocrata

_TODO: describe what this job does, what kind of data it harvests, and any
command line arguments or configuration._

    $ docker-compose run --rm app python manage.py harvestSocrata


## Docker containers

This section describes the different docker containers we use in development.


### app

This is the main container that runs the Django application. By default it runs
the app as a web service and listens on port 8000.

You also use this container to run harvest jobs by specifying an alternative
command.


### db

The database container houses postgresql. If you need to connect to the database
directly with `psql` or other tool, uncomment the `port` lines in
`docker-compose.yml`. The connection string is similar to:

    postgresql://postgres:postgres@localhost:5432/oakcrime


### web

This container houses nginx, which is only used in development to debug the
nginx configuration for production. Nginx proxies to Django/gunicorn and serves
static files in production. Connect over port `8080`.
