# -----------------------------
# Comfy Model Daemon Makefile
# -----------------------------

PYTHON := python3

.PHONY: run
run:
	$(PYTHON) -m daemon

.PHONY: format
format:
	black daemon
	isort daemon

.PHONY: lint
lint:
	flake8 daemon
	mypy daemon

.PHONY: docker-build
docker-build:
	docker compose build

.PHONY: docker-up
docker-up:
	docker compose up

.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f daemon/cache/state.json

