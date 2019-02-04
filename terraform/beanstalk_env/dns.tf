resource "aws_route53_record" "environment" {
  zone_id = "${var.dns_zone_id}"
  name    = "${var.app_name}-${var.app_instance}"
  type    = "CNAME"
  ttl     = 300
  records = ["${aws_elastic_beanstalk_environment.environment.cname}"]
}

// Create an SSL/TLS certificate for the domain
resource "aws_acm_certificate" "environment" {
  domain_name       = "${var.app_name}-${var.app_instance}.${var.dns_zone_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

// Configure a DNS record for ACM certificate verification
resource "aws_route53_record" "cert_validation" {
  name    = "${aws_acm_certificate.environment.domain_validation_options.0.resource_record_name}"
  type    = "${aws_acm_certificate.environment.domain_validation_options.0.resource_record_type}"
  zone_id = "${var.dns_zone_id}"
  records = ["${aws_acm_certificate.environment.domain_validation_options.0.resource_record_value}"]
  ttl     = 60
}

// Complete certificate verification with ACM
resource "aws_acm_certificate_validation" "environment" {
  certificate_arn         = "${aws_acm_certificate.environment.arn}"
  validation_record_fqdns = ["${aws_route53_record.cert_validation.fqdn}"]
}
