# pragma pylint: disable=missing-docstring, invalid-name
"""
EmaRsiTrendStrategy — трендовая стратегия для спота.

Логика:
  * Тренд: быстрая EMA выше медленной EMA, цена выше EMA200 старшего таймфрейма (4h).
  * Сила тренда: ADX выше порога.
  * Вход: откат — RSI пересекает снизу вверх уровень `buy_rsi` при восходящем тренде
    и объёме выше среднего.
  * Выход: RSI перегрет или быстрая EMA пересекает медленную сверху вниз (`use_ema_exit`).
    Выход по EMA почти всегда закрывает сделку в небольшой минус, но без него те же сделки
    доходят до стоп-лосса: на бэктесте 2025-2026 итог -20% против -7.6%.
  * Риск: фиксированный стоп + трейлинг-стоп, ROI-таблица, защиты от серии убытков.

Параметры, помеченные *Parameter, можно оптимизировать через hyperopt.
"""
from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import (
    BooleanParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    informative,
)


class EmaRsiTrendStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "1h"
    process_only_new_candles = True
    startup_candle_count = 250

    # --- Risk management -------------------------------------------------
    minimal_roi = {
        "0": 0.10,
        "360": 0.05,
        "1440": 0.02,
        "2880": 0.0,
    }
    stoploss = -0.06

    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # --- Hyperoptable parameters -----------------------------------------
    ema_fast = IntParameter(8, 30, default=12, space="buy")
    ema_slow = IntParameter(30, 100, default=50, space="buy")
    buy_rsi = IntParameter(30, 55, default=45, space="buy")
    buy_adx = IntParameter(15, 35, default=20, space="buy")
    volume_factor = DecimalParameter(0.5, 2.0, default=1.0, decimals=1, space="buy")

    sell_rsi = IntParameter(65, 90, default=75, space="sell")
    use_ema_exit = BooleanParameter(default=True, space="sell")

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 5,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.15,
            },
        ]

    # --- Indicators ------------------------------------------------------
    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Compute all EMA lengths in the hyperopt range so hyperopt can pick any of them.
        for period in set(self.ema_fast.range) | set(self.ema_slow.range):
            dataframe[f"ema_{period}"] = ta.EMA(dataframe, timeperiod=period)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["volume_mean"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_fast = dataframe[f"ema_{self.ema_fast.value}"]
        ema_slow = dataframe[f"ema_{self.ema_slow.value}"]

        dataframe.loc[
            (ema_fast > ema_slow)
            & (dataframe["close"] > dataframe["ema200_4h"])
            & (dataframe["adx"] > self.buy_adx.value)
            & qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)
            & (dataframe["volume"] > dataframe["volume_mean"] * self.volume_factor.value)
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_trend_rsi_pullback")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_fast = dataframe[f"ema_{self.ema_fast.value}"]
        ema_slow = dataframe[f"ema_{self.ema_slow.value}"]

        dataframe.loc[
            qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value)
            & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_overbought")

        if self.use_ema_exit.value:
            dataframe.loc[
                qtpylib.crossed_below(ema_fast, ema_slow) & (dataframe["volume"] > 0),
                ["exit_long", "exit_tag"],
            ] = (1, "ema_cross_down")
        return dataframe

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        # Skip the entry if price already ran more than 1% above the signal candle close.
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return True
        last_close = dataframe.iloc[-1]["close"]
        return rate <= last_close * 1.01
