.PHONY: test test-operator test-helm test-all lint install-tools

install-tools:
	@echo "Installing test dependencies..."
	helm plugin list | grep unittest || helm plugin install https://github.com/helm-unittest/helm-unittest

test-operator:
	@echo "Running operator unit tests..."
	cd operator && uv run pytest -v --cov=operator --cov-report=term-missing

test-integration:
	@echo "Running operator integration tests..."
	cd operator && uv run pytest test_integration.py -v

test-helm:
	@echo "Running Helm chart tests..."
	helm unittest . -v

lint-helm:
	@echo "Linting Helm chart..."
	helm lint .

template-helm:
	@echo "Testing Helm template rendering..."
	helm template test-release .

test-all: test-operator test-integration test-helm lint-helm

test: test-all

help:
	@echo "Available targets:"
	@echo "  install-tools     - Install required testing tools"
	@echo "  test-operator     - Run operator unit tests"
	@echo "  test-integration  - Run operator integration tests"
	@echo "  test-helm         - Run Helm chart tests"
	@echo "  lint-helm         - Lint Helm chart"
	@echo "  template-helm     - Test Helm template rendering"
	@echo "  test-all          - Run all tests"
	@echo "  test              - Alias for test-all"
