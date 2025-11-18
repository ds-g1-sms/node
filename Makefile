.PHONY: all build clean test lint proto help

# Default target
all: build

## help: Display this help message
help:
	@echo "Available targets:"
	@echo "  build    - Build node server and client"
	@echo "  clean    - Remove build artifacts"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linters"
	@echo "  proto    - Generate code from proto files"
	@echo "  help     - Display this help message"

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
	@echo "Dependencies updated!"
