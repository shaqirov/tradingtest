"""NostalgiaForInfinityX7 with Russian Telegram notifications (see ru_notifications.py)
and protections that stop a losing streak from repeating."""
from NostalgiaForInfinityX7 import NostalgiaForInfinityX7
from ru_notifications import RussianNotificationsMixin


class NostalgiaForInfinityX7Ru(RussianNotificationsMixin, NostalgiaForInfinityX7):
    @property
    def protections(self):
        return [
            # A pair that just closed with a loss of more than 3% is locked for 2 days,
            # so the bot does not buy the same falling coin again.
            {
                "method": "LowProfitPairs",
                "lookback_period": 2880,
                "trade_limit": 1,
                "stop_duration": 2880,
                "required_profit": -0.03,
            },
            # If closed trades lost more than 4% of the balance within 2 days, pause all new
            # entries for 12 hours (open trades are still managed).
            {
                "method": "MaxDrawdown",
                "lookback_period": 2880,
                "trade_limit": 2,
                "stop_duration": 720,
                "max_allowed_drawdown": 0.04,
            },
        ]
