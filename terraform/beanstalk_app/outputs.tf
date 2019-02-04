output "dns_zone" {
  description = "DNS zone name."
  value       = "${aws_route53_zone.default.name}"
}

output "dns_zone_id" {
  description = "DNS zone_id created."
  value       = "${aws_route53_zone.default.zone_id}"
}
