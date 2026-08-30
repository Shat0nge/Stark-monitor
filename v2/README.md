# STARK Monitor V2

Мониторинг инвертора **STARK COUNTRY 2000 INV MAX** через RS232 с Raspberry Pi.

V2 предназначена для автономной работы на Raspberry Pi без графического интерфейса. Данные от инвертора читаются через USB-RS232 адаптер, сохраняются в SQLite и отображаются через встроенный Web-интерфейс.

## Как это работает

STARK COUNTRY 2000 INV MAX -> RS232 -> USB-RS232 (PL2303) -> /dev/ttyUSB0 -> monitor.py -> SQLite + Web

## Основные возможности

- опрос инвертора по RS232
- работа с протоколом Voltronic/Axpert
- команда QPIGS с CRC
- разбор ответа инвертора
- периодический опрос
- сохранение истории в SQLite
- автоматическое удаление старых записей
- встроенный Web-интерфейс
- запуск как systemd-сервис
- автоматический перезапуск после ошибки
- работа без подключённого RS232 адаптера
- конфигурация без изменения Python-кода

## Структура

`monitor.py` — основной процесс мониторинга.
`inverter.py` — работа с последовательным портом и командами инвертора.
`parser.py` — разбор ответов QPIGS.
`database.py` — SQLite и история измерений.
`web.py` — встроенный Web-интерфейс.
`config.py` — загрузка конфигурации из config.env.
`config.env.example` — пример конфигурации.
`deploy.sh` — автоматическая установка V2.
`stark-monitor.service` — systemd unit.

## Конфигурация

Перед запуском используется файл `config.env`.

Он создаётся автоматически из `config.env.example` при установке.

Основные параметры:

- `STARK_SERIAL_PORT` — последовательный порт, обычно `/dev/ttyUSB0`.
- `STARK_SERIAL_BAUD` — скорость RS232, для STARK используется 2400.
- `STARK_SERIAL_TIMEOUT` — таймаут ответа.
- `STARK_POLL_INTERVAL` — интервал опроса.
- `STARK_DB_SAVE_INTERVAL` — интервал записи в SQLite.
- `STARK_CLEANUP_INTERVAL` — интервал очистки истории.
- `STARK_DB_PATH` — путь к базе данных.
- `STARK_RETENTION_DAYS` — срок хранения истории.
- `STARK_WEB_HOST` — адрес Web-интерфейса.
- `STARK_WEB_PORT` — TCP-порт Web-интерфейса.

## Установка

Клонируйте репозиторий и перейдите в каталог V2:

git clone https://github.com/Shat0nge/Stark-monitor.git
cd Stark-monitor/v2

Запустите установщик:

sudo ./deploy.sh

Установщик создаёт каталог `/home/pi/stark-monitor-v2`, копирует файлы V2, создаёт `config.env` из примера, проверяет Python и устанавливает systemd-сервис.

## Systemd

После установки монитор запускается автоматически при загрузке Raspberry Pi.

Проверить состояние:

`systemctl status stark-monitor-v2.service`

Посмотреть журнал:

`journalctl -u stark-monitor-v2.service -f`

Перезапустить:

`sudo systemctl restart stark-monitor-v2.service`

Остановить:

`sudo systemctl stop stark-monitor-v2.service`

## Web-интерфейс

По умолчанию Web-интерфейс доступен на TCP-порту 8080:

`http://IP_RASPBERRY_PI:8080`

Параметры порта и адреса можно изменить через `config.env`.
