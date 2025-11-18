.PHONY: all build clean test lint proto help deps deps-update dev-node dev-client docker-build docker-up docker-down docker-clean

# Default target
all: build

## help: Display this help message
help:
	@echo "Available targets:"
	@echo "  build         - Build node server and client"
	@echo "  clean         - Remove build artifacts"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linters"
	@echo "  proto         - Generate code from proto files"
	@echo "  deps          - Download dependencies"
	@echo "  deps-update   - Update dependencies to latest versions"
	@echo "  dev-node      - Run node server in development mode"
	@echo "  dev-client    - Run client in development mode"
	@echo "  docker-build  - Build Docker images"
	@echo "  docker-up     - Start Docker containers"
	@echo "  docker-down   - Stop Docker containers"
	@echo "  docker-clean  - Remove Docker containers and images"
	@echo "  help          - Display this help message"

## build: Build node server and client binaries
build:
	@echo "Building node server..."
	@go build -o bin/node ./cmd/node
	@echo "Building client..."
	@go build -o bin/client ./cmd/client
	@echo "Build complete!"

## clean: Remove build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf bin/
	@go clean
	@echo "Clean complete!"

## test: Run all tests
test:
	@echo "Running tests..."
	@go test -v ./...

## lint: Run linters
lint:
	@echo "Running linters..."
	@go fmt ./...
	@go vet ./...
	@echo "Lint complete!"

## proto: Generate Go code from proto files
proto:
	@echo "Generating protobuf code..."
	@protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		proto/*.proto
	@echo "Proto generation complete!"

## deps: Download dependencies
deps:
	@echo "Downloading dependencies..."
	@go mod download
	@go mod tidy
	@echo "Dependencies downloaded!"

## deps-update: Update dependencies to latest versions
deps-update:
	@echo "Updating dependencies..."
	@go get -u ./...
	@go mod tidy
	@echo "Dependencies updated!"

## dev-node: Run node server in development mode
dev-node: build
	@echo "Starting node server in development mode..."
	@./bin/node

## dev-client: Run client in development mode
dev-client: build
	@echo "Starting client in development mode..."
	@./bin/client

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
