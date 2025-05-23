# Flow - Web Performance Analysis Tool
.PHONY: help install test report apply clean

help:
	@echo "Flow - Web Performance Analysis Tool"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          Install all dependencies"
	@echo "  make report URL=...   Generate performance report for a URL"
	@echo "  make apply REPORT=... Apply suggestions from a report"
	@echo "  make test            Run tests"
	@echo "  make clean           Clean generated files"

install:
	@echo "Installing JavaScript dependencies..."
	cd report && npm install
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	cd agent && uv sync
	@echo "Setting up Playwright..."
	playwright install chromium

# Example: make report URL=https://example.com
report:
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL is required. Usage: make report URL=https://example.com"; \
		exit 1; \
	fi
	python run.py report --url $(URL) --device mobile

# Example: make apply REPORT=reports/example.md URL=https://example.com
apply:
	@if [ -z "$(REPORT)" ] || [ -z "$(URL)" ]; then \
		echo "Error: REPORT and URL are required. Usage: make apply REPORT=reports/example.md URL=https://example.com"; \
		exit 1; \
	fi
	python run.py apply --report $(REPORT) --url $(URL) --headless

# Full pipeline: generate report and apply suggestions
pipeline:
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL is required. Usage: make pipeline URL=https://example.com"; \
		exit 1; \
	fi
	@echo "Step 1: Generating report..."
	python run.py report --url $(URL) --device mobile
	@echo "Step 2: Applying suggestions..."
	@REPORT=$$(ls -t reports/*.summary.md | head -1); \
	python run.py apply --report $$REPORT --url $(URL) --headless

test:
	@echo "Running tests..."
	cd agent && python test_azure.py

clean:
	@echo "Cleaning generated files..."
	rm -rf output/*
	rm -rf .cache/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 