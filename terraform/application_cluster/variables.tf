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

variable "server_email" {
  description = "Django's SERVER_EMAIL setting. The email address to send admin email."
  default = "root@localhost"
}

variable "email_url" {
  description = "Django's EMAIL_URL setting. The url for the SMTP server, username, password, etc."
  default = "smtp://user@:password@localhost:25"
}
