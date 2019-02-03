resource "aws_s3_bucket" "terraform" {
  bucket = "oakcrime.terraform"

  tags {
    Name = "OakCrime terraform State Store"
  }

  versioning {
    enabled = true
  }
}

resource "aws_dynamodb_table" "terraform" {
  name           = "terraform_oakcrime"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}


resource "aws_iam_user" "ci" {
  name = "oakcrime-ci"
}

resource "aws_iam_access_key" "ci" {
  user = "${aws_iam_user.ci.name}"
}

resource "aws_iam_user_policy" "ci" {
  name = "eb-deploy"
  user = "${aws_iam_user.ci.name}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ElasticBeanstalkReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "elasticbeanstalk:Check*",
        "elasticbeanstalk:Describe*",
        "elasticbeanstalk:List*",
        "elasticbeanstalk:RequestEnvironmentInfo",
        "elasticbeanstalk:RetrieveEnvironmentInfo",
        "ec2:Describe*",
        "elasticloadbalancing:Describe*",
        "autoscaling:Describe*",
        "cloudwatch:Describe*",
        "cloudwatch:List*",
        "cloudwatch:Get*",
        "s3:Get*",
        "s3:List*",
        "sns:Get*",
        "sns:List*",
        "cloudformation:Describe*",
        "cloudformation:Get*",
        "cloudformation:List*",
        "cloudformation:Validate*",
        "cloudformation:Estimate*",
        "rds:Describe*",
        "sqs:Get*",
        "sqs:List*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ElasticBeanstalkDeployAccess",
      "Effect": "Allow",
      "Action": [
        "autoscaling:SuspendProcesses",
        "autoscaling:ResumeProcesses",
        "autoscaling:UpdateAutoScalingGroup",
        "cloudformation:UpdateStack",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "elasticloadbalancing:RegisterTargets",
        "elasticbeanstalk:CreateStorageLocation",
        "elasticbeanstalk:CreateApplicationVersion",
        "elasticbeanstalk:CreateConfigurationTemplate",
        "elasticbeanstalk:UpdateApplicationVersion",
        "elasticbeanstalk:UpdateConfigurationTemplate",
        "elasticbeanstalk:UpdateEnvironment",
        "elasticbeanstalk:ValidateConfigurationSettings",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
EOF
}

