.PHONY: setup install dev test lint format clean

setup:
	@echo "Setting up full project..."
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

install: setup

dev:
	@echo "Starting development servers..."
	@echo "To run individually use 'make dev-backend' or 'make dev-frontend'"
	@echo "Note: it's often better to run them in separate terminal tabs."
	$(MAKE) -C backend dev & $(MAKE) -C frontend dev & wait

dev-backend:
	$(MAKE) -C backend dev

dev-frontend:
	$(MAKE) -C frontend dev

test:
	@echo "Running all tests..."
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

lint:
	@echo "Running linters..."
	$(MAKE) -C backend lint
	$(MAKE) -C frontend lint

format:
	@echo "Running formatters..."
	$(MAKE) -C backend format
	$(MAKE) -C frontend format

clean:
	@echo "Cleaning project..."
	$(MAKE) -C backend clean
	$(MAKE) -C frontend clean
