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

variable "dns_zone_name" {
  description = "DNS zone (name) to use for beanstalk application."
}

variable "dns_zone_id" {
  description = "DNS zone (id) to use for beanstalk application."
}

variable "secret_key" {}

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

variable "default_beanstalk_environment_settings" {
  description = "Default beanstalk settings to apply in addition to user settings."
  type = "list"
  // NOTE: See https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options-general.html for more settings.
  // NOTE: The RDS settings do not work
  default = [
  {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = "aws-elasticbeanstalk-ec2-role"
  },

  // Use an Application Load Balancer (ALB) instead of the default Classic ELB
  {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "LoadBalancerType"
    value     = "application"
  },

  {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = "aws-elasticbeanstalk-service-role"
  },

  {
    namespace = "aws:elbv2:listener:443"
    name      = "Protocol"
    value     = "HTTPS"
  },

  // Stream logs to Cloudwatch, and hold them for 90 days
  {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
  },

  {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "RetentionInDays"
    value     = "90"
  },

  {
    namespace = "aws:elasticbeanstalk:hostmanager"
    name      = "LogPublicationControl"
    value     = "true"
  },

  {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  },

  {
    namespace = "aws:autoscaling:updatepolicy:rollingupdate"
    name      = "RollingUpdateEnabled"
    value     = "true"
  },
  ]
}

variable "environment_variables" {
  description = "Map of environment variables to set for this beanstalk environment."
  type = "map"
  default = {}
}
