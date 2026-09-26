# tradingtest — крипто-бот на Freqtrade

Торговый бот для спота на базе [Freqtrade](https://www.freqtrade.io/) с трендовой стратегией
`EmaRsiTrendStrategy`. По умолчанию работает в **dry-run** (бумажная торговля, 1000 USDT виртуального баланса).

> ⚠️ Торговля криптовалютой связана с высоким риском. Стратегия — стартовая точка, а не гарантия прибыли.
> Обязательно проведите бэктест, hyperopt и несколько недель dry-run перед использованием реальных денег.

## Структура

```
.
├── docker-compose.yml          # запуск бота в Docker (образ freqtradeorg/freqtrade:stable)
├── Makefile                    # короткие команды: download / backtest / hyperopt / up
├── .env.example                # шаблон секретов (API-ключи, Telegram, пароль FreqUI)
└── user_data/
    ├── config.json             # основной конфиг: биржа, пары, dry-run, API-сервер
    └── strategies/
        └── EmaRsiTrendStrategy.py
```

## Стратегия `EmaRsiTrendStrategy`

| | |
|---|---|
| Таймфрейм | 1h (+ 4h как фильтр тренда) |
| Вход | EMA12 > EMA50, цена > EMA200 на 4h, ADX > 20, RSI пересекает 45 снизу вверх, объём выше среднего за 20 свечей |
| Выход | RSI пересекает 75 снизу вверх **или** EMA12 пересекает EMA50 сверху вниз |
| Стоп-лосс | −6 %, трейлинг 1.5 % после +3 % прибыли |
| ROI | 10 % сразу, 5 % через 6 ч, 2 % через 24 ч, 0 % через 48 ч |
| Защиты | Cooldown 2 свечи; пауза после 3 стопов за 24 ч; пауза при просадке > 15 % |

Пороговые значения (`ema_fast`, `ema_slow`, `buy_rsi`, `buy_adx`, `volume_factor`, `sell_rsi`)
оптимизируются через hyperopt.

## Быстрый старт (Docker)

Нужны Docker и Docker Compose.

```bash
make env          # создаёт .env из шаблона — заполните пароль FreqUI и JWT-секрет
make pull         # скачивает образ freqtrade
make download     # история свечей 1h и 4h с 2025-01-01
make backtest     # бэктест стратегии с разбивкой по месяцам
make up           # запуск бота в dry-run
make logs         # логи
```

FreqUI (веб-интерфейс) доступен на http://127.0.0.1:8080 — логин/пароль из `.env`.

Параметры Makefile можно переопределять:

```bash
make download TIMERANGE=20240101-
make backtest TIMERANGE=20250601-20260101
make hyperopt EPOCHS=500
```

Результат hyperopt сохраняется в `user_data/strategies/EmaRsiTrendStrategy.json` и
автоматически подхватывается стратегией. Проверьте его повторным бэктестом на **другом** периоде,
чтобы не переобучиться.

## Без Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install freqtrade
freqtrade download-data -c user_data/config.json --userdir user_data --timerange 20250101- --timeframes 1h 4h
freqtrade backtesting  -c user_data/config.json --userdir user_data --strategy EmaRsiTrendStrategy
freqtrade trade        -c user_data/config.json --userdir user_data --strategy EmaRsiTrendStrategy
```

## Переход на реальную торговлю

1. Создайте на бирже API-ключ **только с правами на торговлю** (без вывода средств), ограничьте его по IP.
2. Впишите ключ и секрет в `.env` (`FREQTRADE__EXCHANGE__KEY`, `FREQTRADE__EXCHANGE__SECRET`).
   Переменные вида `FREQTRADE__A__B` переопределяют значения `config.json`, поэтому секреты не попадают в git.
3. В `user_data/config.json` выставьте `"dry_run": false` и при необходимости ограничьте
   `stake_amount` фиксированной суммой (например, `50`).
4. `make down && make up`.

## Telegram-уведомления

Создайте бота через [@BotFather](https://t.me/BotFather), узнайте свой chat id
(например, через @userinfobot) и заполните в `.env`:

```
FREQTRADE__TELEGRAM__ENABLED=true
FREQTRADE__TELEGRAM__TOKEN=...
FREQTRADE__TELEGRAM__CHAT_ID=...
```

## Смена биржи

По умолчанию — Binance. Для другой биржи (Bybit, OKX, Kraken и т.д.) поменяйте
`exchange.name` в `config.json` и проверьте, что пары из `pair_whitelist` на ней торгуются.
Список поддерживаемых бирж: `freqtrade list-exchanges`.

## Популярные стратегии сообщества

В `user_data/strategies/` лежат копии известных стратегий (лицензия GPL-3):

| Стратегия | Таймфрейм | Источник |
|---|---|---|
| `NostalgiaForInfinityX7` | 5m (+15m/1h/4h/1d) | [iterativv/NostalgiaForInfinity](https://github.com/iterativv/NostalgiaForInfinity) |
| `Supertrend`, `TrendRiderStrategy` | 1h | [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) |
| `MultiMa` | 4h | freqtrade-strategies |
| `CombinedBinHAndCluc`, `ClucMay72018`, `Strategy005` | 5m | freqtrade-strategies |

Сравнение простых стратегий (по группам с одинаковым таймфреймом):

```bash
docker compose run --rm freqtrade download-data --config /freqtrade/user_data/config.json --timerange 20250101- --timeframes 5m 15m 1h 4h 1d
# --strategy-list needs one common timeframe, so strategies are grouped by timeframe
docker compose run --rm freqtrade backtesting --config /freqtrade/user_data/config.json --timerange 20250101- --timeframe 1h --strategy-list EmaRsiTrendStrategy Supertrend TrendRiderStrategy
docker compose run --rm freqtrade backtesting --config /freqtrade/user_data/config.json --timerange 20250101- --timeframe 5m --strategy-list CombinedBinHAndCluc ClucMay72018 Strategy005
docker compose run --rm freqtrade backtesting --config /freqtrade/user_data/config.json --timerange 20250101- --strategy MultiMa
```

NostalgiaForInfinity требует свои настройки ордеров — добавьте второй конфиг `config-nfi.json`.
Стратегия тяжёлая по памяти, начинайте с короткого периода:

```bash
docker compose run --rm freqtrade backtesting --config /freqtrade/user_data/config.json --config /freqtrade/user_data/config-nfi.json --strategy NostalgiaForInfinityX7 --timerange 20260601-
```

> NFI не использует классический стоп-лосс (`stoploss = -0.99`) и докупает позиции при просадке (DCA),
> поэтому сделки могут висеть в минусе неделями. Смотрите на максимальную просадку, а не только на прибыль.
