from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES = ("ru", "uk", "en")
DEFAULT_LANGUAGE = "ru"


TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "prize_places": "Призовые места",
        "place": "место",
        "sponsors": "Спонсоры",
        "participation_condition": "Условие участия",
        "youtube_required": "Необходимо подписаться на YouTube канал:",
        "subscribe_channel": "Подписаться на канал →",
        "subscription_required_days": "Требуется подписка минимум на {days} {unit}",
        "day_one": "день",
        "day_few": "дня",
        "day_many": "дней",
        "end_date": "Дата окончания",
        "register": "Зарегистрироваться",
        "results_title": "Результаты конкурса: {title}",
        "results_generic": "Результаты конкурса",
        "winners": "Победители",
        "winner": "Победитель",
        "not_specified": "не указан",
        "view_results": "Посмотреть результаты",
        "winner_notification": "Поздравляем! Вы выиграли {place} место в конкурсе \"{title}\"!",
        "your_prize": "Ваш приз",
        "main_channel": "Основной канал",
        "sponsor_channel": "Канал спонсора",
        "youtube_channel": "YouTube канал",
        "tiktok_channel": "TikTok канал",
        "contest_not_active": "Конкурс не активен",
        "telegram_required": "Необходимо подписаться на все каналы",
        "youtube_auth_required": "Для участия в конкурсе необходимо авторизоваться через YouTube",
        "youtube_channel_unknown": "Не удалось определить ваш YouTube канал",
        "youtube_channel_duplicate": "Этот YouTube канал уже используется другим пользователем для участия в этом конкурсе",
        "youtube_subscribe_days_required": "Необходимо быть подписанным на YouTube канал не менее {days} {unit}",
        "youtube_subscribe_required": "Необходимо быть подписанным на указанный YouTube канал",
        "tiktok_auth_required": "Для участия в конкурсе необходимо авторизоваться через TikTok",
        "tiktok_follow_unverified": "Не удалось подтвердить фолловинг TikTok-канала. Откройте TikTok ещё раз и попробуйте позже.",
        "tiktok_follow_required": "Необходимо фолловить указанный TikTok-канал",
        "captcha_required": "Подтвердите капчу перед регистрацией",
        "captcha_invalid": "Неверный ответ капчи. Попробуйте ещё раз.",
        "already_registered": "Вы уже зарегистрированы в этом конкурсе",
        "register_in_contest": "Зарегистрироваться в конкурсе",
        "registration_title": "Регистрация в конкурсе",
        "registration_hint": "Нажмите кнопку ниже, чтобы открыть форму регистрации:",
        "results_hint": "Нажмите кнопку ниже, чтобы посмотреть результаты:",
    },
    "uk": {
        "prize_places": "Призові місця",
        "place": "місце",
        "sponsors": "Спонсори",
        "participation_condition": "Умова участі",
        "youtube_required": "Необхідно підписатися на YouTube канал:",
        "subscribe_channel": "Підписатися на канал →",
        "subscription_required_days": "Потрібна підписка щонайменше на {days} {unit}",
        "day_one": "день",
        "day_few": "дні",
        "day_many": "днів",
        "end_date": "Дата завершення",
        "register": "Зареєструватися",
        "results_title": "Результати конкурсу: {title}",
        "results_generic": "Результати конкурсу",
        "winners": "Переможці",
        "winner": "Переможець",
        "not_specified": "не вказано",
        "view_results": "Переглянути результати",
        "winner_notification": "Вітаємо! Ви виграли {place} місце в конкурсі \"{title}\"!",
        "your_prize": "Ваш приз",
        "main_channel": "Основний канал",
        "sponsor_channel": "Канал спонсора",
        "youtube_channel": "YouTube канал",
        "tiktok_channel": "TikTok канал",
        "contest_not_active": "Конкурс не активний",
        "telegram_required": "Необхідно підписатися на всі канали",
        "youtube_auth_required": "Для участі в конкурсі необхідно авторизуватися через YouTube",
        "youtube_channel_unknown": "Не вдалося визначити ваш YouTube канал",
        "youtube_channel_duplicate": "Цей YouTube канал уже використовується іншим користувачем для участі в цьому конкурсі",
        "youtube_subscribe_days_required": "Необхідно бути підписаним на YouTube канал щонайменше {days} {unit}",
        "youtube_subscribe_required": "Необхідно бути підписаним на вказаний YouTube канал",
        "tiktok_auth_required": "Для участі в конкурсі необхідно авторизуватися через TikTok",
        "tiktok_follow_unverified": "Не вдалося підтвердити фолловинг TikTok-каналу. Відкрийте TikTok ще раз і спробуйте пізніше.",
        "tiktok_follow_required": "Необхідно фолловити вказаний TikTok-канал",
        "captcha_required": "Підтвердьте капчу перед реєстрацією",
        "captcha_invalid": "Неправильна відповідь капчі. Спробуйте ще раз.",
        "already_registered": "Ви вже зареєстровані в цьому конкурсі",
        "register_in_contest": "Зареєструватися в конкурсі",
        "registration_title": "Реєстрація в конкурсі",
        "registration_hint": "Натисніть кнопку нижче, щоб відкрити форму реєстрації:",
        "results_hint": "Натисніть кнопку нижче, щоб переглянути результати:",
    },
    "en": {
        "prize_places": "Prize places",
        "place": "place",
        "sponsors": "Sponsors",
        "participation_condition": "Participation condition",
        "youtube_required": "You need to subscribe to the YouTube channel:",
        "subscribe_channel": "Subscribe to the channel →",
        "subscription_required_days": "Subscription required for at least {days} {unit}",
        "day_one": "day",
        "day_few": "days",
        "day_many": "days",
        "end_date": "End date",
        "register": "Register",
        "results_title": "Contest results: {title}",
        "results_generic": "Contest results",
        "winners": "Winners",
        "winner": "Winner",
        "not_specified": "not specified",
        "view_results": "View results",
        "winner_notification": "Congratulations! You won {place} place in \"{title}\"!",
        "your_prize": "Your prize",
        "main_channel": "Main channel",
        "sponsor_channel": "Sponsor channel",
        "youtube_channel": "YouTube channel",
        "tiktok_channel": "TikTok channel",
        "contest_not_active": "The contest is not active",
        "telegram_required": "You need to subscribe to all channels",
        "youtube_auth_required": "You need to authorize with YouTube to join the contest",
        "youtube_channel_unknown": "Could not detect your YouTube channel",
        "youtube_channel_duplicate": "This YouTube channel is already used by another user in this contest",
        "youtube_subscribe_days_required": "You need to be subscribed to the YouTube channel for at least {days} {unit}",
        "youtube_subscribe_required": "You need to be subscribed to the specified YouTube channel",
        "tiktok_auth_required": "You need to authorize with TikTok to join the contest",
        "tiktok_follow_unverified": "Could not confirm the TikTok channel follow. Open TikTok again and try later.",
        "tiktok_follow_required": "You need to follow the specified TikTok channel",
        "captcha_required": "Complete the captcha before registration",
        "captcha_invalid": "Invalid captcha answer. Try again.",
        "already_registered": "You are already registered for this contest",
        "register_in_contest": "Register for the contest",
        "registration_title": "Contest registration",
        "registration_hint": "Tap the button below to open the registration form:",
        "results_hint": "Tap the button below to view the results:",
    },
}


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = language.strip().lower()
    return normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def translate(language: str | None, key: str, **kwargs: Any) -> str:
    lang = normalize_language(language)
    template = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(
        key,
        TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key),
    )
    return template.format(**kwargs) if kwargs else template


def day_unit(language: str | None, days: int) -> str:
    lang = normalize_language(language)
    if lang == "en":
        return translate(lang, "day_one" if days == 1 else "day_many")
    if days == 1:
        return translate(lang, "day_one")
    if 2 <= days <= 4:
        return translate(lang, "day_few")
    return translate(lang, "day_many")
