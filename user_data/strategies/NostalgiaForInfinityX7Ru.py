"""NostalgiaForInfinityX7 with Russian Telegram notifications (see ru_notifications.py)."""
from NostalgiaForInfinityX7 import NostalgiaForInfinityX7
from ru_notifications import RussianNotificationsMixin


class NostalgiaForInfinityX7Ru(RussianNotificationsMixin, NostalgiaForInfinityX7):
    pass
