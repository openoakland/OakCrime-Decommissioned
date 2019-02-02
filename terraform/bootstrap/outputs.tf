output "ci_access_key_id" {
  value = "${aws_iam_access_key.ci.id}"
  sensitive = true
}

output "ci_secret_access_key" {
  value = "${aws_iam_access_key.ci.secret}"
  sensitive = true
}
