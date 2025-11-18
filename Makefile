.PHONY: all install clean test lint proto help deps deps-update dev-node dev-client docker-build docker-up docker-down docker-clean

# Default target
all: install

## help: Display this help message
help:
	@echo "Available targets:"
	@echo "  install       - Install Python package and dependencies"
	@echo "  clean         - Remove build artifacts"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linters"
	@echo "  proto         - Generate code from proto files"
	@echo "  deps          - Install dependencies"
	@echo "  deps-update   - Update dependencies to latest versions"
	@echo "  dev-node      - Run node server in development mode"
	@echo "  dev-client    - Run client in development mode"
	@echo "  docker-build  - Build Docker images"
	@echo "  docker-up     - Start Docker containers"
	@echo "  docker-down   - Stop Docker containers"
	@echo "  docker-clean  - Remove Docker containers and images"
	@echo "  help          - Display this help message"

## install: Install Python package and dependencies
install:
	@echo "Installing dependencies with Poetry..."
	@poetry install
	@echo "Installation complete!"

## clean: Remove build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@poetry env remove --all 2>/dev/null || true
	@echo "Clean complete!"

## test: Run all tests
test:
	@echo "Running tests..."
	@poetry run pytest -v

## lint: Run linters
lint:
	@echo "Running linters..."
	@poetry run flake8 src/ || true
	@poetry run pylint src/ || true
	@echo "Lint complete!"

## proto: Generate Python code from proto files
proto:
	@echo "Generating protobuf code..."
	@poetry run python -m grpc_tools.protoc -I. \
		--python_out=. \
		--grpc_python_out=. \
		proto/*.proto
	@echo "Proto generation complete!"

## deps: Install dependencies
deps:
	@echo "Installing dependencies with Poetry..."
	@poetry install
	@echo "Dependencies installed!"

## deps-update: Update dependencies to latest versions
deps-update:
	@echo "Updating dependencies..."
	@poetry update
	@echo "Dependencies updated!"

## dev-node: Run node server in development mode
dev-node:
	@echo "Starting node server in development mode..."
	@poetry run python -m src.node.main

## dev-client: Run client in development mode
dev-client:
	@echo "Starting client in development mode..."
	@poetry run python -m src.client.main

## docker-build: Build Docker images
docker-build:
	@echo "Building Docker images..."
	@docker compose build
	@echo "Docker images built!"

## docker-up: Start Docker containers
docker-up:
	@echo "Starting Docker containers..."
	@docker compose up -d
	@echo "Docker containers started!"

## docker-down: Stop Docker containers
docker-down:
	@echo "Stopping Docker containers..."
	@docker compose down
	@echo "Docker containers stopped!"

## docker-clean: Remove Docker containers and images
docker-clean:
	@echo "Cleaning Docker resources..."
	@docker compose down -v --rmi all
	@echo "Docker resources cleaned!"
