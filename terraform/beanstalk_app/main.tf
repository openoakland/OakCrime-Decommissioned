resource "aws_route53_zone" "default" {
  name = "${var.dns_zone}"
}

resource "aws_elastic_beanstalk_application" "default" {
  name = "${var.app_name}"

  // Retain the recent application versions/deploys
  appversion_lifecycle {
    service_role          = "aws-elasticbeanstalk-service-role"
    max_count             = "${var.appversion_lifecycle_max_count}"
    delete_source_from_s3 = "${var.delete_source_from_s3}"
  }
}
