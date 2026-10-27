.PHONY: setup up down status check test capture
setup:
	./scripts/setup.sh
up:
	docker compose up -d --build
status:
	docker compose ps
check:
	./scripts/smoke-test.sh
test:
	python3 -m pytest -q tests
capture:
	docker compose --profile capture up -d capture
down:
	docker compose down
.PHONY: analyze ghidra gate-plan doctor experiments
analyze:
	bash scripts/analyze-now.sh
ghidra:
	docker compose --profile ghidra up -d --build ghidra
gate-plan:
	@echo 'Usage: scripts/gateway-dns.sh plan TARGET_IP LAB_GATEWAY_IP'
doctor:
	python3 scripts/validate-project.py
	python3 scripts/check-mcp.py
experiments:
	python3 scripts/labctl.py list
