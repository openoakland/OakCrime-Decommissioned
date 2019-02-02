module "dns" "dns" {
  source = "./dns"
  zone = "${var.dns_zone}"
}

// Create the Elastic Beanstalk application and environment, along with a database
module "application_cluster" "cluster" {
  source = "./application_cluster"

  application_name = "${var.app_name}"
  db_name          = "${var.app_name}"
  environment      = "${var.app_instance}"
  db_username      = "${var.db_username}"
  db_password      = "${var.db_password}"
  route_53_zone_id = "${module.dns.zone_id}"
  secret_key       = "${var.django_secret_key}"
  ssl_cert_arn     = "${module.dns.cert_arn}"
}
