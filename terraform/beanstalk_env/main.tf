data "aws_elastic_beanstalk_solution_stack" "docker" {
  most_recent = true
  name_regex  = "^64bit Amazon Linux (.*) running Docker (.*)$"
}

resource "aws_security_group" "application" {
  name = "${var.app_name}-${var.app_instance}-app"

  // Allow HTTP connections from the load balancer
  ingress {
    from_port = 80
    to_port   = 80
    protocol  = "tcp"

    security_groups = [
      "${aws_security_group.application-load-balancer.id}",
    ]
  }

  // Allow SSH access from anywhere
  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "0.0.0.0/0",
    ]
  }
}

resource "aws_security_group" "application-load-balancer" {
  name = "${var.app_name}-${var.app_instance}-load-balancer"

  // Allow HTTP and HTTPS connections from anywhere
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "database" {
  name = "${var.app_name}-${var.app_instance}-db"

  // Allow HTTP connections from the application
  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"

    security_groups = [
      "${aws_security_group.application.id}",
    ]
  }
}

resource "aws_db_instance" "database" {
  allocated_storage         = 20
  storage_type              = "gp2"
  engine                    = "postgres"
  engine_version            = "10.5"
  instance_class            = "db.t2.micro"
  deletion_protection       = "${var.deletion_protection}"
  identifier                = "${var.app_name}-${var.app_instance}"
  final_snapshot_identifier = "${var.app_name}-${var.app_instance}-final"
  name                      = "${var.db_name}"
  username                  = "${var.db_username}"
  password                  = "${var.db_password}"
  publicly_accessible       = "false"
  backup_retention_period   = "7"
  backup_window             = "10:00-10:30"

  vpc_security_group_ids = [
    "${aws_security_group.database.id}",
  ]
}

resource "aws_elastic_beanstalk_environment" "environment" {
  name                = "${var.app_name}-${var.app_instance}"
  application         = "${var.app_name}"
  solution_stack_name = "${data.aws_elastic_beanstalk_solution_stack.docker.name}"

  // NOTE: See https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options-general.html for more settings.
  // NOTE: The RDS settings do not work!
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "${var.instance_type}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = "${aws_security_group.application.name}"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = "aws-elasticbeanstalk-ec2-role"
  }

  // Use an Application Load Balancer (ALB) instead of the default Classic ELB
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "LoadBalancerType"
    value     = "application"
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = "aws-elasticbeanstalk-service-role"
  }

  // Use our custom path for health checks since not all projects have an active root path
  setting {
    namespace = "aws:elasticbeanstalk:environment:process:default"
    name      = "HealthCheckPath"
    value     = "${var.health_check_path}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application"
    name      = "Application Healthcheck URL"
    value     = "${var.health_check_path}"
  }

  setting {
    namespace = "aws:elbv2:loadbalancer"
    name      = "SecurityGroups"
    value     = "${aws_security_group.application-load-balancer.id}"
  }

  // Update the ELB/ALB to terminate SSL
  setting {
    namespace = "aws:elbv2:listener:443"
    name      = "Protocol"
    value     = "HTTPS"
  }

  setting {
    namespace = "aws:elbv2:listener:443"
    name      = "SSLCertificateArns"
    value     = "${aws_acm_certificate.environment.arn}"
  }

  // Stream logs to Cloudwatch, and hold them for 90 days
  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "RetentionInDays"
    value     = "90"
  }

  setting {
    namespace = "aws:elasticbeanstalk:hostmanager"
    name      = "LogPublicationControl"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  }

  setting {
    namespace = "aws:autoscaling:updatepolicy:rollingupdate"
    name      = "RollingUpdateEnabled"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_URL"
    value     = "postgis://${var.db_username}:${var.db_password}@${aws_db_instance.database.endpoint}/${var.db_name}"
  }

  # Define environment variables for the application.
  # TODO Terraform v0.12 introduces dynamic nested blocks to make this better
  # https://www.hashicorp.com/blog/hashicorp-terraform-0-12-preview-for-and-for-each#dynamic-nested-blocks
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 0)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 0),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 1)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 1),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 2)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 2),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 3)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 3),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 4)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 4),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 5)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 5),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 6)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 6),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 7)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 7),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 8)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 8),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 9)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 9),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 10)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 10),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 11)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 11),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 12)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 12),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 13)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 13),"")}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "${element(keys(var.environment_variables), 14)}"
    value     = "${lookup(var.environment_variables, element(keys(var.environment_variables), 14),"")}"
  }

  depends_on = ["aws_acm_certificate_validation.environment"]
}
