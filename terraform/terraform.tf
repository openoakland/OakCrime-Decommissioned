terraform {
  backend "s3" {
    bucket         = "oakcrime.terraform"
    key            = "terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform_oakcrime"
  }
}
