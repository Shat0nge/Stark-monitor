# STARK COUNTRY 2000 INV MAX Monitor — V2

## Восстановительный документ проекта

Актуальное состояние: 31.08.2026.

Этот README2 является дополнительным документом восстановления.
Он содержит архитектуру, назначение файлов, конфигурацию и текущее
подтверждённое состояние проекта.

---

## 1. Назначение

Проект предназначен для мониторинга инвертора:

**STARK COUNTRY 2000 INV MAX**

Платформа:

- Raspberry Pi
- Python 3
- SQLite
- HTTP Web UI
- RS232 / USB-Serial
- SSH для удалённой синхронизации базы

---

## 2. Архитектура

Инвертор
    |
    | RS232
    |
USB-Serial / PL2303
    |
    | /dev/ttyUSB0
    |
Raspberry Pi
    |
    +-- monitor.py
    |     основной процесс
    |
    +-- inverter.py
    |     связь с инвертором
    |
    +-- parser.py
    |     разбор QPIGS
    |
    +-- database.py
    |     локальная SQLite
    |
    +-- web.py
    |     HTTP :8080
    |
    +-- db_sync.py
          синхронизация SQLite по SSH

---

## 3. Systemd

Основной сервис:

    stark-monitor-v2.service

Запускает:

    /usr/bin/python3 -u /home/pi/stark-monitor-v2/monitor.py

Сервис включён в автозапуск.

Проверка:

    systemctl status stark-monitor-v2.service

Логи:

    journalctl -u stark-monitor-v2.service -n 50 --no-pager

## 4. Каталоги

Git/source проект:

    /home/pi/stark-monitor

Исходники V2:

    /home/pi/stark-monitor/v2

Установленная рабочая копия:

    /home/pi/stark-monitor-v2

Основной установленный запуск:

    /home/pi/stark-monitor-v2/monitor.py

Конфигурация:

    /home/pi/stark-monitor-v2/config.env
    /home/pi/stark-monitor-v2/config.py

---

## 5. Основные файлы V2

### monitor.py

Главный процесс.

Отвечает за:

- запуск Web-сервера;
- запуск DB Sync;
- опрос инвертора;
- передачу данных в parser;
- обновление текущего состояния;
- сохранение измерений;
- очистку старых данных.

При отключённом инверторе модуль `inverter` не импортируется
до момента фактического включения опроса.

---

### inverter.py

Связь с STARK через последовательный порт.

Используется:

    /dev/ttyUSB0

Параметры:

    2400 baud
    8N1

Основной запрос:

    QPIGS

Рабочий пакет QPIGS:

    51 50 49 47 53 B7 A9 0D

CRC подтверждён экспериментально.

---

### parser.py

Разбирает ответ QPIGS и преобразует его в структурированные
значения для Web UI и SQLite.

---

### database.py

Работает с локальной SQLite базой.

Хранит измерения инвертора.

В базе предусмотрена автоматическая очистка старых записей
через `CLEANUP_INTERVAL`.

---

### web.py

Локальный HTTP Web UI.

Адрес:

    http://<IP_RASPBERRY_PI>:8080

Сервис слушает:

    0.0.0.0:8080

---

### db_sync.py

Дополнительная функция.

Предназначена для передачи новых строк локальной SQLite базы
на удалённый сервер по SSH.

Синхронизация выполняется только при:


## 6. Конфигурация

Файл:

    /home/pi/stark-monitor-v2/config.env

Основные переключатели:

    STARK_INVERTER_ENABLED=false
    STARK_DB_SYNC_ENABLED=false

---

## 7. STARK_INVERTER_ENABLED

Текущее значение:

    false

При `false` опрос инвертора полностью отключён.

В логах:

    INVERTER POLLING: DISABLED (STARK_INVERTER_ENABLED=false)

При этом Web UI продолжает работать.

Чтобы включить опрос:

    STARK_INVERTER_ENABLED=true

После изменения конфигурации необходимо перезапустить сервис:

    sudo systemctl restart stark-monitor-v2.service

При успешном включении ожидается:

    INVERTER POLLING: ENABLED

---

## 8. STARK_DB_SYNC_ENABLED

Текущее значение:

    false

При `false` синхронизация базы не запускается.

Ожидаемый лог:

    DB SYNC: DISABLED (STARK_DB_SYNC_ENABLED=false)

Для включения:


После изменения требуется:

    sudo systemctl restart stark-monitor-v2.service

DB Sync использует SSH к:

    pi@10.10.0.1:22

Интервал текущей конфигурации:

    3600 секунд

---

## 9. Важное правило включения модулей

Оба механизма являются независимыми.

Можно иметь:

    INVERTER_ENABLED=true
    DB_SYNC_ENABLED=false

или:

    INVERTER_ENABLED=false
    DB_SYNC_ENABLED=true

или включить оба.

При выключенном DB Sync не должен выполняться SSH-синхронизатор.

При выключенном inverter не должен выполняться опрос `/dev/ttyUSB0`.

---

## 10. Память и фоновые процессы

Проект не использует отдельный постоянно работающий процесс
для каждого компонента.

Основной процесс:

    monitor.py

Внутри него используются только необходимые daemon threads:

- Web server
- DB Sync, если включён

SQLite хранится локально.

Очистка старых измерений выполняется через `database.cleanup()`
с заданным `CLEANUP_INTERVAL`.

Отключённые функции не должны постоянно опрашивать оборудование.

---

## 11. Ошибка Host key verification failed

Ранее DB Sync пытался подключаться к:

    10.10.0.1

и получил:

    Host key verification failed.

После этого DB Sync был отключён:

    STARK_DB_SYNC_ENABLED=false

Это сделано намеренно до отдельной настройки SSH host key.

## 12. Текущее подтверждённое состояние

На 31.08.2026:

    stark-monitor-v2.service = active (running)

Конфигурация:

    STARK_INVERTER_ENABLED=false
    STARK_DB_SYNC_ENABLED=false

Web:

    enabled
    :8080

Inverter polling:

    disabled

DB Sync:

    disabled

Последний нормальный запуск:

    STARK monitor starting
    CONFIG: inverter_enabled=False, db_sync_enabled=False
    DB SYNC: DISABLED (STARK_DB_SYNC_ENABLED=false)
    INVERTER POLLING: DISABLED (STARK_INVERTER_ENABLED=false)
    STARK WEB: http://0.0.0.0:8080

---

## 13. Важная информация для восстановления

Не считать старые экспериментальные процессы частью архитектуры V2.

Основной сервис:

    stark-monitor-v2.service

Основная рабочая директория:

    /home/pi/stark-monitor-v2

Git/source:

    /home/pi/stark-monitor

Исходный код V2:

    /home/pi/stark-monitor/v2

При восстановлении сначала проверять:

    systemctl status stark-monitor-v2.service

    cat /home/pi/stark-monitor-v2/config.env

    journalctl -u stark-monitor-v2.service -n 50 --no-pager

---

## 14. Git

README2 хранится отдельно от основного README.

Цель README2 — служить дополнительной точкой восстановления,
если основной контекст проекта будет потерян.

Конфигурационные секреты и содержимое локальной базы
не должны помещаться в Git.

---

## 15. Следующий этап проекта

После восстановления базового состояния:

1. Проверить SSH host key для DB Sync.
2. Отдельно протестировать DB Sync.
3. При необходимости включить `STARK_DB_SYNC_ENABLED`.
4. Подключить инвертор и включить `STARK_INVERTER_ENABLED`.
5. Проверить QPIGS и корректность parser.
6. Проверить сохранение SQLite.
7. Проверить автоматическую очистку базы.
8. Проверить Web UI.
