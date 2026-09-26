"""
Russian Telegram notifications for trade fills.

Mix into a strategy (before the IStrategy base) to send Russian messages on every filled
entry/exit. The English entry/exit notifications are switched off in config.json
(telegram.notification_settings), and telegram.allow_custom_messages must be true.
"""
from datetime import datetime

from freqtrade.persistence import Order, Trade


EXIT_REASONS_RU = {
    "roi": "достигнута цель прибыли (ROI)",
    "trailing_stop_loss": "трейлинг-стоп",
    "stop_loss": "стоп-лосс",
    "stoploss_on_exchange": "стоп-лосс на бирже",
    "exit_signal": "сигнал стратегии",
    "force_exit": "принудительное закрытие",
    "emergency_exit": "аварийное закрытие",
    "liquidation": "ликвидация",
    "rsi_overbought": "RSI перегрет",
    "ema_cross_down": "пересечение EMA вниз",
}


def _exit_reason_ru(reason: str | None) -> str:
    if not reason:
        return "—"
    # Underscores would break Telegram Markdown, so unknown reasons are shown with spaces.
    return EXIT_REASONS_RU.get(reason, reason.replace("_", " "))


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ")


def _fmt_price(price: float) -> str:
    # Cheap coins need more decimals than BTC.
    if price >= 100:
        return _fmt(price, 2)
    if price >= 1:
        return _fmt(price, 4)
    return f"{price:.6g}"


class RussianNotificationsMixin:
    def bot_start(self, **kwargs) -> None:
        super().bot_start(**kwargs)
        mode = "бумажная торговля (dry-run)" if self.config.get("dry_run") else "РЕАЛЬНАЯ торговля"
        self.dp.send_msg(
            f"🤖 *Бот запущен*\n"
            f"Стратегия: {self.__class__.__name__}\n"
            f"Таймфрейм: {self.timeframe}\n"
            f"Режим: {mode}",
            always_send=True,
        )

    def order_filled(
        self, pair: str, trade: Trade, order: Order, current_time: datetime, **kwargs
    ) -> None:
        super().order_filled(pair, trade, order, current_time, **kwargs)
        try:
            self.dp.send_msg(self._order_filled_ru(trade, order), always_send=True)
        except Exception:  # noqa: BLE001 - a notification must never break trading
            pass

    def _order_filled_ru(self, trade: Trade, order: Order) -> str:
        currency = trade.stake_currency
        price = order.safe_price
        amount = order.safe_filled or order.safe_amount
        cost = price * amount

        if order.ft_order_side == trade.entry_side:
            if trade.nr_of_successful_entries <= 1:
                title = "🟢 *Покупка*"
            else:
                title = f"➕ *Докупка №{trade.nr_of_successful_entries - 1}*"
            return (
                f"{title} {trade.pair}\n"
                f"Цена: {_fmt_price(price)}\n"
                f"Сумма: {_fmt(cost)} {currency}\n"
                f"Всего в сделке: {_fmt(trade.stake_amount)} {currency}"
            )

        if trade.is_open:
            return (
                f"➖ *Частичная продажа* {trade.pair}\n"
                f"Цена: {_fmt_price(price)}\n"
                f"Сумма: {_fmt(cost)} {currency}\n"
                f"Зафиксировано прибыли: {_fmt(trade.realized_profit)} {currency}"
            )

        profit_ratio = trade.close_profit or 0.0
        profit_abs = trade.close_profit_abs or 0.0
        icon = "✅" if profit_abs >= 0 else "🔴"
        duration = (trade.close_date_utc or datetime.now(trade.open_date_utc.tzinfo)) - (
            trade.open_date_utc
        )
        hours, rem = divmod(int(duration.total_seconds()), 3600)
        return (
            f"{icon} *Продажа* {trade.pair}\n"
            f"Результат: {profit_ratio:+.2%} ({profit_abs:+.2f} {currency})\n"
            f"Цена входа: {_fmt_price(trade.open_rate)} → выхода: {_fmt_price(price)}\n"
            f"Причина: {_exit_reason_ru(trade.exit_reason)}\n"
            f"Длительность: {hours // 24} д {hours % 24} ч {rem // 60} мин"
        )
