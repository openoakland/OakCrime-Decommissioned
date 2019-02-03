module "app_oakcrime" {
  source = "./beanstalk_app"

  app_name = "${var.app_name}"
  dns_zone = "${var.dns_zone}"
}

module "env_development" {
  source = "./beanstalk_env"

  application_name = "${var.app_name}"
  db_name          = "${var.app_name}"
  environment      = "${var.app_instance}"
  db_username      = "${var.db_username}"
  db_password      = "${var.db_password}"
  dns_zone_name = "${module.app_oakcrime.dns_zone}"
  dns_zone_id = "${module.app_oakcrime.dns_zone_id}"
  secret_key       = "${var.django_secret_key}"
  deletion_protection = false
}
