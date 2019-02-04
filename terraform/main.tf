module "app_oakcrime" {
  source = "./beanstalk_app"

  app_name = "${var.app_name}"
  dns_zone = "${var.dns_zone}"
}

module "env_production" {
  source = "./beanstalk_env"

  app_instance      = "production"
  app_name = "${var.app_name}"
  db_name          = "${var.app_name}"
  db_password      = "${var.db_password}"
  db_username      = "${var.db_username}"
  dns_zone_id = "${module.app_oakcrime.dns_zone_id}"
  dns_zone_name = "${module.app_oakcrime.dns_zone}"

  environment_variables = {
    SECRET_KEY = "${var.django_secret_key}"
    SERVER_EMAIL = "root@localhost"
    EMAIL_URL = "smtp://localhost"
  }
}
