variable "app_name" {
  description = "Slugified name of the beanstalk application."
}

variable "db_name" {
  description = "Name of the RDS database to create for the application."
}

variable "db_username" {
  description = "RDS username to create for the application."
}

variable "db_password" {
  description = "RDS password to create for the application."
}

variable "app_instance" {
  description = "Name of this beanstalk environment e.g. (dev, staging, production, etc)."
}

variable "health_check_path" {
  description = "App endpoint to check the health of the instance."
  default     = "/health/"
}

variable "instance_type" {
  description = "EC2 instance type to use for beanstalk instances."
  default     = "t3.micro"
}

variable "dns_zone_name" {
  description = "DNS zone (name) to use for beanstalk application."
}

variable "dns_zone_id" {
  description = "DNS zone (id) to use for beanstalk application."
}

variable "deletion_protection" {
  description = "Enable deletion protection on various components."
  default     = true
}

variable "environment_variables" {
  description = "Map of environment variables to set for this beanstalk environment."
  type        = "map"
  default     = {}
}
