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

Prepare for any database migrations

    docker-compose run --rm app makemigrations

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


## Harvest jobs

This section describes the various harvest jobs that fetch and process data that
powers OakCrime.


### harvestSocrata

OPD provides updated data through a Socrata API about every day.  This
job queries the API to check for any new and/or modified data, and
updates the database accordingly.

    $ docker-compose run --rm app python manage.py harvestSocrata

### harvestPatrolLogs

OPD provides PDF reports concerning major (FBI UCR "Part 1") crimes,
approximately once a week via files on Box.com.  This job queries this
resource daily, harvests any new PDFs, parses the PDFs and merges this
data to match with existing daily incident reports.

    $ docker-compose run --rm app python manage.py harvestPatrolLog


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
