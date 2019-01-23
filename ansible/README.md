# Ansible

We use [Ansible](https://www.ansible.com/) playbooks for deploying OakCrime. You
can repeat the steps outlined in this README in order to spin up your own
instance of OakCrime.


## Development

This section explains how to develop on the Ansible playbooks. These
instructions assume you're working from the `ansible/` directory.


### Prerequisites

- [Docker](https://www.docker.com/)
- [Python](https://www.python.org/) 3.6+
- [virtualenv](https://virtualenv.pypa.io/en/stable/)

We recommend creating a new virtualenv separate from your OakCrime virtualenv.


### Setup

Install the python dependencies.

    $ make setup

Run the tests.

    $ make test

### Working with molecule

[Molecule](https://molecule.readthedocs.io/en/latest/) is a tool used to test
Ansible roles and playbooks.

Converge (apply) a particular role.

    $ molecule converge 

