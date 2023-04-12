class ApiAnswerError(Exception):
    """Некорректный ответ от API."""

    pass


class BotMessageError(Exception):
    """Отправка сообщения ботов невозможна."""

    pass


class ParseStatusError(Exception):
    """Ошибка в функции `parse_status`."""

    pass
