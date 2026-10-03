# SpecID Makefile (TRD v1.1 Appendix B). Run from Git Bash, WSL, Linux or macOS (needs `sh` and Docker).
# Python and Node run inside containers; no host toolchain needed beyond Docker, git and make.
# Targets not built yet print their phase and exit 1, so nothing looks done when it is not.

GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
export GIT_COMMIT

SEED ?= 7
CI := sh backend/scripts/ci_local.sh

define stub
	@echo "make $@: not built yet (Implementation Plan Phase $(1))"; exit 1
endef

.PHONY: help models up down seed demo-data test test-ml eval bench offline-check snapshot restore \
        doctor lint purge-real

help:
	@echo "Targets: models up down seed demo-data test test-ml eval bench offline-check snapshot"
	@echo "         restore doctor lint purge-real   (see TRD Appendix B)"

## (online, once) download MiniLM, train category_clf-v1, write models/manifest.json
models:
	$(call stub,5)

## start / stop the stack (GIT_COMMIT exported for the api service, DECISIONS.md DEC-02)
up: .env
	docker compose up -d --build

down:
	docker compose down

.env:
	@echo "missing .env: run 'cp .env.example .env' and set local values"; exit 1

## CPSEs, demo users, templates, dictionaries (Backend Schema 12); seed-7 synthetic data arrives in Phases 4-5
seed:
	docker compose exec -T api python -m app.db.seed

## regenerate synthetic files and manifest (SEED=$(SEED))
demo-data:
	$(call stub,4)

## CI test set, run locally in containers (mirror of .github/workflows/ci.yml, lint included)
test:
	$(CI) all

## ML-dependent tests (embeddings, FAISS), TRD TR-CI-02
test-ml:
	$(call stub,5)

## evaluation run + Markdown/JSON report (SEED=$(SEED))
eval:
	$(call stub,7)

## TR-TST-11 stage timings and search latency
bench:
	$(call stub,10)

## TR-TST-10. Phase 1 checks only the internal network; the egress counter check needs Phase 5
offline-check:
	@internal=$$(docker network inspect specid_backend --format '{{.Internal}}' 2>/dev/null); \
	echo "specid_backend Internal: $${internal:-network not found (run make up)}"; \
	test "$$internal" = "true" || exit 1; \
	echo "PARTIAL: blocked_egress_attempts check is added with /system/airgap in Phase 5"

## TR-OPS-07 pg_dump / pg_restore of the demo database
snapshot:
	$(call stub,11)

restore:
	$(call stub,11)

## tool, library, model and template versions; .env check
doctor:
	@echo "git commit:   $(GIT_COMMIT)"
	@echo "make:         $$(make --version | head -1)"
	@echo "docker:       $$(docker --version)"
	@echo "compose:      $$(docker compose version)"
	@if [ -f .env ]; then \
	  for k in DB_PASSWORD JWT_SECRET CONSENT_MODE EMBEDDINGS_ENABLED; do \
	    grep -q "^$$k=" .env && echo ".env:         $$k set" || echo ".env:         $$k MISSING"; \
	  done; \
	else echo ".env:         MISSING (cp .env.example .env)"; fi
	@if [ -f models/manifest.json ]; then echo "models:       manifest.json present"; \
	  else echo "models:       none yet (make models, Phase 5)"; fi
	@echo "templates:    $$(ls templates/*.yaml 2>/dev/null | wc -l | tr -d ' ') YAML file(s)"
	@echo "backend lock: $$(grep -c '==' backend/requirements.lock) core pins, $$(grep -c '==' backend/requirements-ml.lock) ML pins"

## ruff, black --check, mypy core, eslint (+ prettier)
lint:
	$(CI) lint

## delete non-synthetic batches (TRD 7.4)
purge-real:
	$(call stub,5)
