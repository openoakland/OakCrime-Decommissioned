variable "app_name" {
  description = "Name of the Elastic Beanstalk application to create."
  type        = "string"
}

variable "dns_zone" {
  description = "DNS Zone name to create where beanstalk environments will be hosted."
  type        = "string"
}

variable "delete_source_from_s3" {
  description = "When old application versions are removed, the source should also be deleted from S3."
  default     = "true"
}

variable "appversion_lifecycle_max_count" {
  description = "Maximum number of appversions to retain."
  default     = 32
}
