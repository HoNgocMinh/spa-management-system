"""Các cột DATETIME lưu giờ địa phương của spa (UTC+7)."""
from datetime import datetime, timedelta, timezone

SPA_TZ = timezone(timedelta(hours=7))


def now_vn():
    return datetime.now(SPA_TZ).replace(tzinfo=None)
