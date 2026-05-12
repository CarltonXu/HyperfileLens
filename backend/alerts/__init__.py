"""Global alert center app."""


def get_manager():
    from .manager import alert_manager

    return alert_manager
