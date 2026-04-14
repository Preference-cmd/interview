.PHONY: help
.PHONY: backend-install backend-dev backend-test backend-run backend-clean backend-lint backend-fmt
.PHONY: frontend-install frontend-dev frontend-build
.PHONY: test clean

help:
	@echo "Multi-Agent Ops - Available commands:"
	@echo ""
	@echo "Backend (uv + FastAPI):"
	@echo "  make backend-install    Install backend dependencies"
	@echo "  make backend-dev        Run backend in development mode (port 8000)"
	@echo "  make backend-test       Run backend tests"
	@echo "  make backend-run        Run backend (production)"
	@echo "  make backend-lint       Lint backend with ruff"
	@echo "  make backend-fmt        Format backend with ruff"
	@echo "  make backend-clean      Clean backend artifacts"
	@echo ""
	@echo "Frontend (Next.js):"
	@echo "  make frontend-install    Install frontend dependencies (pnpm)"
	@echo "  make frontend-dev        Run frontend dev server (port 3000)"
	@echo "  make frontend-build      Build frontend"
	@echo ""
	@echo "All:"
	@echo "  make test     Run backend tests"
	@echo "  make clean    Clean all artifacts"

# Backend
backend-install:
	cd backend && uv sync

backend-dev:
	cd backend && uv run uvicorn main:app --reload --port 8000

backend-test:
	cd backend && uv run pytest ../tests/ -v

backend-run:
	cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000

backend-lint:
	cd backend && uv run ruff check .

backend-fmt:
	cd backend && uv run ruff format .

backend-clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f backend/*.db backend/*.db-journal

# Frontend
frontend-install:
	cd frontend && pnpm install

frontend-dev:
	cd frontend && pnpm run dev

frontend-build:
	cd frontend && pnpm run build

# Shortcuts
test: backend-test
clean: backend-clean
