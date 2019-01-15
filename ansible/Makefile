ROLES = oakcrime

TEST_ROLE_TARGETS = $(patsubst %, test-%, $(ROLES))

setup:
	pip install -r requirements.txt

test-%:
	cd roles/$* \
	&& molecule test

test: $(TEST_ROLE_TARGETS)

.PHONY: $(ROLES) setup
