variable "application_name" {}
variable "db_name" {}
variable "db_username" {}
variable "db_password" {}
variable "environment" {}

variable "health_check_path" {
  default = "/health/"
}

variable "instance_type" {
  default = "t3.micro"
}

variable "route_53_zone_id" {}
variable "secret_key" {}
variable "ssl_cert_arn" {}

variable "deletion_protection" {
  description = "Enable deletion protection on various components."
  default = true
}
