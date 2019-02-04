# Terraform

[Terraform](https://www.terraform.io/) is used to provision resources in AWS to
host and deploy OakCrime as an [AWS
Beanstalk](https://aws.amazon.com/elasticbeanstalk/) application.

## Usage

### Prerequisites

You'll need to install these.

- [Terraform](https://www.terraform.io/downloads.html) v0.11+

### Setup

Initialize terraform.

    $ make setup

Set your AWS access key.

    $ export AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
    $ export AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>

Create a `terraform.tfvars` containing secret variables and replace these with
secure, random values.

    $ cp terraform.example.tfvars terraform.tfvars


### Lint your templates

    $ make lint


## First time setup

The very very first time this is setup, you'll need to bootstrap the Terraform
state. The S3 terraform state bucket needs to be created, as well as an IAM user
for automated deployment. This is done using `/bootstrap` and only needs to be
done if the S3 bucket used for Terraform state has not been created.

    $ cd bootstrap
    $ terraform init
    $ terraform apply

In the output, you'll receive the IAM user and AWS Access Key.

    $ terraform output
    ci_access_key_id = <AWS_ACCESS_KEY_ID>
    ci_secret_access_key = <AWS_SECRET_ACCESS_KEY>
    ci_username = oakcrime-ci

You'll want to add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment
variables to
[CircleCI](https://circleci.com/gh/openoakland/OakCrime/edit#env-vars).
