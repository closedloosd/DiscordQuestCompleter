# Discord Quest Completer

Десктопное приложение для автоматического выполнения квестов Discord и получения орбов.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.7-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Возможности

- Автоматическое выполнение квестов (`WATCH_VIDEO`, `PLAY_ON_DESKTOP`, `STREAM_ON_DESKTOP`, `PLAY_ACTIVITY`)
- Отображение баланса орбов и статистики
- История выполненных заданий
- Сохранение сессии (автовход)
- Плавные анимации и тёмная тема в стиле Discord

## Установка

**Требования:** Python 3.10+

```bash
git clone https://github.com/YOUR_USERNAME/QuestComliterForDiscord.git
cd QuestComliterForDiscord
pip install -r requirements.txt
python main.py
```

## Как получить токен

1. Откройте Discord в браузере или приложении и нажмите **Ctrl+Shift+I**
2. Перейдите во вкладку **Network**
3. В поле **Filter** введите `api` и перезагрузите страницу (**Ctrl+F5**)
4. Найдите запрос **science** в списке и кликните на него
5. Откройте вкладку **Headers**
6. Напротив заголовка **authorization** — ваш токен

> ⚠️ **Никому не передавайте токен!** Он даёт полный доступ к вашему аккаунту.

## Зависимости

| Пакет | Версия |
|-------|--------|
| PyQt6 | 6.7.0 |
| aiohttp | 3.9.5 |
| qasync | 0.27.1 |
| certifi | latest |

## Дисклеймер

Данный инструмент использует неофициальный API Discord. Использование на свой страх и риск. Автор не несёт ответственности за возможную блокировку аккаунта.

## Лицензия

MIT
