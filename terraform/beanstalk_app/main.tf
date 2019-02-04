data "aws_iam_role" "beanstalk_service" {
  name = "aws-elasticbeanstalk-service-role"
}

resource "aws_route53_zone" "default" {
  name = "${var.dns_zone}"
}

resource "aws_elastic_beanstalk_application" "default" {
  name = "${var.app_name}"

  // Retain the recent application versions/deploys
  appversion_lifecycle {
    service_role          = "${data.aws_iam_role.beanstalk_service.arn}"
    max_count             = "${var.appversion_lifecycle_max_count}"
    delete_source_from_s3 = "${var.delete_source_from_s3}"
  }
}
