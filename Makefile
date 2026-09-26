# Freqtrade helper commands (run via Docker)
STRATEGY  ?= EmaRsiTrendStrategy
TIMERANGE ?= 20250101-
PAIRS_TF  ?= 1h 4h
EPOCHS    ?= 200

FT = docker compose run --rm freqtrade

.PHONY: help env pull download backtest hyperopt up down logs list-strategies

help:
	@echo "make env             - create .env from .env.example"
	@echo "make pull            - pull the freqtrade docker image"
	@echo "make download        - download historical candles ($(PAIRS_TF)) for TIMERANGE=$(TIMERANGE)"
	@echo "make backtest        - backtest $(STRATEGY) on TIMERANGE"
	@echo "make hyperopt        - optimise strategy parameters (EPOCHS=$(EPOCHS))"
	@echo "make up / down       - start / stop the bot (dry-run by default)"
	@echo "make logs            - follow bot logs"

env:
	@test -f .env || cp .env.example .env && echo ".env ready - edit it"

pull:
	docker compose pull

download:
	$(FT) download-data --config /freqtrade/user_data/config.json \
		--timerange $(TIMERANGE) --timeframes $(PAIRS_TF)

backtest:
	$(FT) backtesting --config /freqtrade/user_data/config.json \
		--strategy $(STRATEGY) --timerange $(TIMERANGE) --breakdown month

hyperopt:
	$(FT) hyperopt --config /freqtrade/user_data/config.json \
		--strategy $(STRATEGY) --timerange $(TIMERANGE) \
		--hyperopt-loss SharpeHyperOptLossDaily --spaces buy sell -e $(EPOCHS)

list-strategies:
	$(FT) list-strategies --config /freqtrade/user_data/config.json

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f freqtrade
