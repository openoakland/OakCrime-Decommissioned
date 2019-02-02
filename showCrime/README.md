# ShowCrime: Visualizing Oakland Police Department Daily Incident data

# showCrime django app


## Setup

We use [Docker Compose](https://docs.docker.com/compose/) to ease development.
Each component (django app, http server, and database) are each in their own
container.

All instructions assume you're running from the `showCrime` directory.

    cd showCrime

Start the containers.

    make local.up

Open your web browser to [localhost:8000](http://localhost:8000).

### Make commands


#### make docker.build

Build/rebuild the container images.

#### make docker.pull

Pull the latest container images from the Docker registry.


#### make local.down

Stop and remove the containers.


#### make local.restart

Restart the containers.


#### make local.shell

Open a shell in the application container.


#### make local.up

Start the containers.


### Extra setup steps

Create an admin user to login with.

    make local.shell
    ./manage.py createsuperuser


### Loading OPD data

Older OakCrime datasets in (CSV, JSON and sqlite formats) remain
available http://data.openoakland.org/dataset/crime-reports in csv
file formats, but these have not been updated since late 2016.
