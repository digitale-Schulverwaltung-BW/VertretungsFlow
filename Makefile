.PHONY: help up down restart rebuild

COMPOSE = "docker compose"  # projektspezifisch anpassen, z.B. docker-compose -f docker-compose.prod.yml

help: ## Verfügbare Befehle anzeigen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Container starten
	$(COMPOSE) up -d

down: ## Container stoppen
	$(COMPOSE) down

restart: ## Container neu starten
	$(COMPOSE) restart

rebuild: ## Container stoppen, neu bauen und starten
	$(COMPOSE) down
	$(COMPOSE) build
	$(COMPOSE) up -d

frontend-restart: ## Frontend neu starten nach Update
	cd wordpress-plugin
	npm install
	npm run build
