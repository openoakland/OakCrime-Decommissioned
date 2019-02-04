plan:
	terraform plan -out=plan.tfplan

apply: plan.tfplan
	terraform apply $^

destroy:
	terraform destroy

lint:
	terraform validate

setup:
	terraform init


.PHONY: apply destroy lint plan setup
