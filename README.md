# Структура каталога UG_Telecom

Материал Bitrix24-задач 1877 и 2406, собран 02.10.2026.

```
UG_Telecom/
├── audit/               79 отчётов аудита из задачи 1877, разложены по группам
│   ├── 01-billing-core/       Биллинг-ядра BGBilling (5)
│   ├── 02-billing-radius/     RADIUS / AAA (5)
│   ├── 03-proxysql/           ProxySQL (5)
│   ├── 04-nginx-proxy/        nginx-прокси (6)
│   ├── 05-callcenter/         Call-центры (6)
│   ├── 06-mail-dns/           Почта / DNS (4)
│   ├── 07-k3s-docker/         K3s и Docker-сервисы (9)
│   ├── 08-monitoring/         Мониторинг (5)
│   ├── 09-vpn-access/         VPN и доступ (5)
│   ├── 10-storage-backup/     Хранилища и бэкапы (3)
│   ├── 11-no-access/          Без доступа к ОС (6)
│   ├── 12-windows-appliance/  Windows / appliance (2)
│   ├── 13-svobodnyh/          Прочие узлы (16)
│   └── 99-svobodnye/          Сводные отчёты + perimeter-dashboard.html
│
├── reports/
│   ├── audit-summary.md   Выжимка для печати: 5–7 страниц
│   ├── hosts-table.md     Полная таблица 77 хостов
│   └── hosts.json         Машиночитаемые данные (IP, роль, ОС, порты, находки)
│
├── schemes/
│   ├── connection-scheme.md   Схема подключения — только по данным аудита
│   └── perimeter-dashboard.html  Дашборд периметра из задачи 1877
│
├── findings/
│   └── risks.md           Риски и приоритеты
│
├── raw/
│   ├── 1877/              Исходники задачи 1877
│   └── 2406/              network-scheme.html из задачи 2406
│
└── templates/
```

## С чего читать

1. **`reports/audit-summary.md`** — короткая выжимка, помещается на handful страниц при печати.
2. **`findings/risks.md`** — риски по приоритету.
3. **`reports/hosts-table.md`** — если нужен конкретный хост.
4. **`schemes/connection-scheme.md`** — как связаны узлы.

## Источники

| Задача | URL | Что взято |
|---|---|---|
| 1877 | `/tasks/task/view/1877/` | 91 вложение, все скачаны в `audit/` |
| 2406 | `/tasks/task/view/2406/` | `network-scheme.html`, в `raw/2406/` |

## Важно

- 11 файлов вида `... (1).txt` — побайтовые дубли, удалены. Было 91, стало 79 уникальных.
- `schemes/connection-scheme.md` построен **только** по отчётам аудита. Вики и `network-scheme.html` из задачи 2406 не использовались как источник фактов.
- Секреты из отчётов (пароли, ключи, токены) намеренно не цитируются.