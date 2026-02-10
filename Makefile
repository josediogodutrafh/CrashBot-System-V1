# ============================================
# CRASHBOT SYSTEM - MAKEFILE
# ============================================
# Comandos úteis para desenvolvimento
#
# Uso: make <comando>
# Ex: make install, make test, make format

.PHONY: help install install-dev test lint format clean run docs

# Cores para output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Variáveis
PYTHON := python
PIP := pip
PYTEST := pytest
BLACK := black
ISORT := isort
RUFF := ruff
PRE_COMMIT := pre-commit

# ============================================
# HELP
# ============================================

help: ## Mostra esta mensagem de ajuda
	@echo "$(BLUE)CrashBot System - Comandos Disponíveis:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================
# INSTALAÇÃO
# ============================================

install: ## Instala dependências de produção
	@echo "$(BLUE)Instalando dependências...$(NC)"
	$(PIP) install -r CrashBot-System-V1/CrashBot/requirements.txt
	@echo "$(GREEN)✓ Dependências instaladas!$(NC)"

install-dev: install ## Instala dependências de desenvolvimento
	@echo "$(BLUE)Instalando dependências de desenvolvimento...$(NC)"
	$(PIP) install pytest pytest-cov pytest-asyncio pytest-xdist
	$(PIP) install black isort ruff mypy
	$(PIP) install pre-commit bandit detect-secrets
	$(PIP) install --upgrade pip setuptools wheel
	@echo "$(GREEN)✓ Dependências de desenvolvimento instaladas!$(NC)"

pre-commit-install: ## Instala pre-commit hooks
	@echo "$(BLUE)Instalando pre-commit hooks...$(NC)"
	$(PRE_COMMIT) install
	$(PRE_COMMIT) install --hook-type commit-msg
	@echo "$(GREEN)✓ Pre-commit hooks instalados!$(NC)"

# ============================================
# FORMATAÇÃO E LINTING
# ============================================

format: ## Formata código com Black e isort
	@echo "$(BLUE)Formatando código Python...$(NC)"
	$(BLACK) CrashBot-System-V1/CrashBot/ scripts/ tests/
	$(ISORT) CrashBot-System-V1/CrashBot/ scripts/ tests/
	@echo "$(GREEN)✓ Código formatado!$(NC)"

lint: ## Executa linting com Ruff
	@echo "$(BLUE)Executando linting...$(NC)"
	$(RUFF) check CrashBot-System-V1/CrashBot/ scripts/ tests/
	@echo "$(GREEN)✓ Linting concluído!$(NC)"

lint-fix: ## Executa linting e corrige problemas automaticamente
	@echo "$(BLUE)Executando linting com auto-fix...$(NC)"
	$(RUFF) check --fix CrashBot-System-V1/CrashBot/ scripts/ tests/
	@echo "$(GREEN)✓ Linting com auto-fix concluído!$(NC)"

type-check: ## Executa type checking com MyPy
	@echo "$(BLUE)Executando type checking...$(NC)"
	mypy CrashBot/ Crash/ crashbot-platform/api/
	@echo "$(GREEN)✓ Type checking concluído!$(NC)"

security: ## Verifica vulnerabilidades de segurança
	@echo "$(BLUE)Verificando vulnerabilidades...$(NC)"
	bandit -r CrashBot/ Crash/ crashbot-platform/api/ -c pyproject.toml
	@echo "$(GREEN)✓ Verificação de segurança concluída!$(NC)"

check-all: format lint type-check security ## Executa todas as verificações
	@echo "$(GREEN)✓ Todas as verificações concluídas!$(NC)"

# ============================================
# TESTES
# ============================================

test: ## Executa todos os testes
	@echo "$(BLUE)Executando testes...$(NC)"
	$(PYTEST) -v

test-unit: ## Executa apenas testes unitários
	@echo "$(BLUE)Executando testes unitários...$(NC)"
	$(PYTEST) -v -m unit

test-integration: ## Executa apenas testes de integração
	@echo "$(BLUE)Executando testes de integração...$(NC)"
	$(PYTEST) -v -m integration

test-fast: ## Executa testes rápidos (sem slow)
	@echo "$(BLUE)Executando testes rápidos...$(NC)"
	$(PYTEST) -v -m "not slow"

test-cov: ## Executa testes com cobertura
	@echo "$(BLUE)Executando testes com cobertura...$(NC)"
	$(PYTEST) --cov=CrashBot-System-V1/CrashBot --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Relatório de cobertura gerado em htmlcov/index.html$(NC)"

test-parallel: ## Executa testes em paralelo
	@echo "$(BLUE)Executando testes em paralelo...$(NC)"
	$(PYTEST) -n auto

# ============================================
# EXECUÇÃO
# ============================================

run-bot: ## Executa o bot (CrashBot v3.0)
	@echo "$(BLUE)Iniciando CrashBot...$(NC)"
	cd CrashBot-System-V1/CrashBot && $(PYTHON) main.py

run-bot-headless: ## Executa o bot em modo headless
	@echo "$(BLUE)Iniciando CrashBot (headless)...$(NC)"
	cd CrashBot-System-V1/CrashBot && $(PYTHON) main.py --headless

run-api: ## Executa a API
	@echo "$(BLUE)Iniciando API...$(NC)"
	cd crashbot-platform/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Executa o frontend Next.js
	@echo "$(BLUE)Iniciando frontend...$(NC)"
	cd crashbot-platform/loja && npm run dev

# ============================================
# LIMPEZA
# ============================================

clean: ## Remove arquivos temporários e cache
	@echo "$(BLUE)Limpando arquivos temporários...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf build/ 2>/dev/null || true
	rm -rf dist/ 2>/dev/null || true
	@echo "$(GREEN)✓ Limpeza concluída!$(NC)"

clean-all: clean ## Remove tudo incluindo venv e node_modules
	@echo "$(BLUE)Limpeza completa...$(NC)"
	rm -rf .venv/ venv/ 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Limpeza completa concluída!$(NC)"

# ============================================
# DOCUMENTAÇÃO
# ============================================

docs: ## Gera documentação
	@echo "$(BLUE)Gerando documentação...$(NC)"
	@echo "$(YELLOW)TODO: Configurar Sphinx ou MkDocs$(NC)"

# ============================================
# PRE-COMMIT
# ============================================

pre-commit: ## Executa pre-commit em todos os arquivos
	@echo "$(BLUE)Executando pre-commit...$(NC)"
	$(PRE_COMMIT) run --all-files

pre-commit-update: ## Atualiza versões dos hooks
	@echo "$(BLUE)Atualizando pre-commit hooks...$(NC)"
	$(PRE_COMMIT) autoupdate

# ============================================
# BUILD
# ============================================

build-bot: ## Compila o bot para executável
	@echo "$(BLUE)Compilando bot...$(NC)"
	cd CrashBot-System-V1/Crash && $(PYTHON) build_deploy.py
	@echo "$(GREEN)✓ Bot compilado!$(NC)"

# ============================================
# DOCKER (se configurado)
# ============================================

docker-build: ## Build da imagem Docker
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t crashbot-system .

docker-up: ## Sobe containers Docker
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker-compose up -d

docker-down: ## Derruba containers Docker
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down

docker-logs: ## Mostra logs dos containers
	docker-compose logs -f

# ============================================
# GIT
# ============================================

git-clean: ## Remove branches mergeadas
	@echo "$(BLUE)Limpando branches mergeadas...$(NC)"
	git branch --merged | grep -v "\*" | xargs -n 1 git branch -d

# ============================================
# INFO
# ============================================

info: ## Mostra informações do ambiente
	@echo "$(BLUE)Informações do Ambiente:$(NC)"
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Working directory: $$(pwd)"
	@echo "Git branch: $$(git branch --show-current 2>/dev/null || echo 'N/A')"
	@echo "Git status:"
	@git status --short 2>/dev/null || echo "Not a git repository"

# ============================================
# DEFAULT
# ============================================

.DEFAULT_GOAL := help
