# Чек-лист покрытия Veeam — все хосты инфраструктуры

Источник: `UG_Telecom/reports/hosts.json` (77 хостов аудита). Заполняется вручную по консоли Veeam.

Колонки: `Прио` — порядок проверки (1 — критично: хранилища/бэкап-хосты/vCenter, 2 — биллинг/БД/GitLab, 3 — RADIUS/AAA/K3s/DNS, 4 — колл-центры/хранилища, 5 — мониторинг, 6 — прочее).

Заполнить: `ВМ?` (да/нет — есть ли в vCenter), `Джоб Veeam` (имя джоба или `—`), `Статус` (`ok` / `НЕ ПОКРЫТ` / `исключена`), `Последняя точка` (дата), `Риск` (крит/выс/средний/нет), `Комментарий` (причина, если не покрыта).

> Если колонка `ВМ?` = нет, а `Статус` = `НЕ ПОКРЫТ` → это физический сервер: в Veeam он покрывается только джобом типа *Physical Machine / Entire Computer*. Проверь `Backup Infrastructure → Physical Machines`.

| Прио | IP | Hostname | Роль | ВМ? | Джоб Veeam | Статус | Последняя точка | Риск | Комментарий |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 172.16.100.24 | rocket-bg-core.rocket.local | БИЛЛИНГ-ЯДРО BGBilling домена rocket (4-й bg-core) |  |  |  |  |  |  |
| 6 | 172.16.100.25 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 4 | 172.16.100.26 | ProxySQL, домен rocket | ProxySQL — прокси MySQL перед БД BGBilling домена rocket (rocketcom), |  |  |  |  |  |  |
| 3 | 172.16.100.27 | rocket-bg-radius.rocket.local | RADIUS/AAA-сервер интернет-абонентов (BGBilling Inet), домен rocket |  |  |  |  |  |  |
| 6 | 172.16.100.45 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 4 | 172.16.100.54 | CALLCENTERROCKET | Телефонная платформа call-центра ITGRIX (Asterisk + web), домен rocket. |  |  |  |  |  |  |
| 2 | 192.168.110.7 | bg-core-flash.flash.local | БИЛЛИНГ-ЯДРО BGBilling |  |  |  |  |  |  |
| 3 | 192.168.110.8 | bg-radius-flash.flash.local | RADIUS/AAA-сервер абонентов на базе BGBilling Inet |  |  |  |  |  |  |
| 6 | 192.168.110.17 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 4 | 192.168.110.20 | proxysql-flash.flash.local | ProxySQL 2.4.4 — прокси/балансировщик MySQL перед БД BGBilling домена flash |  |  |  |  |  |  |
| 4 | 192.168.110.29 | CALLCENTERFLASH | Телефонная платформа call-центра ITGRIX (Asterisk + web), домен flash. |  |  |  |  |  |  |
| 4 | 192.168.110.30 | CALLCENTERRTC | Телефонная платформа call-центра ITGRIX (Asterisk + web), домен rtc. |  |  |  |  |  |  |
| 6 | 192.168.110.110 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 6 | 192.168.155.253 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 6 | 192.168.160.6 | office.omicron.online |  |  |  |  |  |  |  |
| 4 | 192.168.160.11 | Samba file server | Хранилище бэкапов конфигов сетевых устройств + ключей. |  |  |  |  |  |  |
| 5 | 192.168.160.19 | grafana | Сервер мониторинга Grafana. Контейнер grafana/grafana:13.0.1-security-01 |  |  |  |  |  |  |
| 2 | 192.168.160.31 | erp.360pro.online | ERP-система BGERP (ERP-модуль BGBilling, Java). Front nginx + MySQL 8.0.28 |  |  |  |  |  |  |
| 4 | 192.168.160.35 | call-center | Телефонная АТС call-центра — Asterisk (брендинг "Line24_PBX") + FreePBX |  |  |  |  |  |  |
| 5 | 192.168.160.45 | prometheus | Сервер метрик Prometheus 2.54.1 + Alertmanager + экспортеры (пара к grafana |  |  |  |  |  |  |
| 2 | 192.168.160.54 | bg-core-omiplat.omicron.local | БИЛЛИНГ-ЯДРО BGBilling (BiTel) домена omiplat |  |  |  |  |  |  |
| 3 | 192.168.160.55 | bg-radius-omiplat.omicron.local | RADIUS/AAA-сервер интернет-абонентов на базе BGBilling Inet, домен omiplat |  |  |  |  |  |  |
| 6 | 192.168.160.68 | oms | NOC/управление сетью. Observium (мониторинг по SNMP: nginx+php-fpm+MariaDB, |  |  |  |  |  |  |
| 4 | 192.168.160.70 | proxysql-omiplat.omicron.local | ProxySQL 2.4.4 — прокси MySQL перед БД BGBilling домена omiplat |  |  |  |  |  |  |
| 2 | 192.168.160.87 | rtc-bg-core.rtc.local | БИЛЛИНГ-ЯДРО BGBilling домена rtc (rocket-telecom), 5-й bg-core |  |  |  |  |  |  |
| 3 | 192.168.160.88 | rtc-bg-radius.rtc.local | RADIUS/AAA-сервер интернет-абонентов (BGBilling Inet), домен rtc (rocket-telecom) |  |  |  |  |  |  |
| 4 | 192.168.160.89 | rtc-bg-proxy.rtc.local | ProxySQL 2.4.7 — прокси MySQL перед БД BGBilling домена rtc/rocket-telecom |  |  |  |  |  |  |
| 3 | 192.168.160.100 | wiki2 | Wiki-сервис (веб-приложение в Docker за nginx; 2 контейнера + backend :8080). |  |  |  |  |  |  |
| 2 | 192.168.160.101 | omicron-bg-core.omicron.local | БИЛЛИНГ-ЯДРО BGBilling домена omicron (аналог bg-core-flash 192.168.110.7) |  |  |  |  |  |  |
| 3 | 192.168.160.102 | omicron-bg-radius.omicron.local | RADIUS/AAA-сервер интернет-абонентов на базе BGBilling Inet, домен omicron |  |  |  |  |  |  |
| 4 | 192.168.160.103 | omicron-bg-proxy.omicron.local | ProxySQL 2.5.1 — прокси/балансировщик MySQL перед БД BGBilling домена omicron |  |  |  |  |  |  |
| 5 | 192.168.160.104 | zabbix-core.omicron.local | Сервер мониторинга Zabbix (zabbix_server + nginx/php-frontend + PostgreSQL). |  |  |  |  |  |  |
| 6 | 192.168.160.110 | bitrix.360pro.online | self-hosted Битрикс24 (BitrixVM/Bitrix Environment). |  |  |  |  |  |  |
| 3 | 192.168.160.118 | msVPN.360pro.online | похоже, Windows VPN-шлюз (msVPN) — RRAS/SSTP (443) + удалённое управление. |  |  |  |  |  |  |
| 3 | 192.168.160.119 | n8n.360pro.online | n8n — платформа автоматизации воркфлоу/iPaaS (в Docker): n8n(node) + |  |  |  |  |  |  |
| 1 | 192.168.160.135 | db-backup1.loc | Сервер бэкапов БД. Приём дампов от СУБД-серверов по доменам |  |  |  |  |  |  |
| 1 | 192.168.160.136 | db-backup2.loc | Второй сервер бэкапов БД (приём дампов по доменам flash/omiplat/rocket/ |  |  |  |  |  |  |
| 1 | 192.168.160.202 | vcenter.esxi.loc |  |  |  |  |  |  |  |
| 6 | 192.168.160.215 | katan.360pro.online |  |  |  |  |  |  |  |
| 4 | 192.168.160.217 | CALLCENTEROMIPLAT | Телефонная платформа call-центра ITGRIX (Asterisk + web), домен omiplat. |  |  |  |  |  |  |
| 4 | 192.168.160.219 | callcenter-deb2 | Телефонная платформа call-центра на базе ITGRIX (Asterisk + web). |  |  |  |  |  |  |
| 6 | 192.168.161.4 | voiceops | Ops/управляющий узел голосового контура. Прикладных служб НЕ запущено |  |  |  |  |  |  |
| 6 | 192.168.161.5 | netbox | NetBox — система документирования сети (IPAM/DCIM): полный инвентарь сети, |  |  |  |  |  |  |
| 6 | 192.168.161.6 | nginx | Центральный EDGE reverse/stream-прокси. Публикует наружу множество служб |  |  |  |  |  |  |
| 2 | 192.168.161.7 | git | GitLab (self-hosted, omnibus) — хранилище исходного кода. Компоненты: |  |  |  |  |  |  |
| 3 | 192.168.161.8 | rustdesk | Self-hosted RustDesk server (удалённый доступ): hbbs + hbbr (нативно, |  |  |  |  |  |  |
| 6 | 192.168.161.11 | fop2.360pro.online | FOP2 (Flash Operator Panel 2) — панель оператора/супервизора Asterisk. |  |  |  |  |  |  |
| 3 | 192.168.161.12 | sv1.360pro.online | Крупный МНОГОСЕРВИСНЫЙ Docker-хост (~27 контейнеров) — dev/staging окружение |  |  |  |  |  |  |
| 4 | 192.168.161.13 | CALLCENTERUTK | Телефонная платформа call-центра ITGRIX (Asterisk + web), домен UTK |  |  |  |  |  |  |
| 3 | 192.168.161.15 | commerce.360pro.online | Контейнеризированная веб-платформа (Docker). В контейнерах: nginx + |  |  |  |  |  |  |
| 3 | 192.168.161.17 | voice1 | Голосовая платформа / voice-analytics (Docker, ~13 контейнеров): микросервисы |  |  |  |  |  |  |
| 3 | 192.168.161.18 | ns1.omicron.online | Авторитетный DNS-сервер (PowerDNS, pdns_server) для omicron.online. |  |  |  |  |  |  |
| 3 | 192.168.161.19 | ns2.omicron.online | Авторитетный DNS-сервер PowerDNS (реплика ns1) для omicron.online. |  |  |  |  |  |  |
| 3 | 192.168.161.26 | OpenVPN | Корпоративный VPN-шлюз. OpenVPN (UDP:1194, 2 инстанса server.conf), |  |  |  |  |  |  |
| 6 | 192.168.161.32 | relay1.360pro.online | Почтовый сервер/релей — Postfix (с postscreen anti-spam) + SOGo (groupware/ |  |  |  |  |  |  |
| 6 | 192.168.161.33 | relay2.360pro.online | Второй почтовый сервер/релей — Postfix (postscreen) + SOGo (nginx) + IMAPS. |  |  |  |  |  |  |
| 6 | 192.168.161.42 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 3 | 192.168.161.45 | voice2 | Голосовая платформа/voice-analytics (Docker, ~13 контейнеров) — второй узел, |  |  |  |  |  |  |
| 6 | 192.168.161.46 | nomoney-rocketcom | Captive-портал "нет средств" для абонентов rocketcom с нулевым балансом. |  |  |  |  |  |  |
| 3 | 192.168.161.48 | speedtest / speedtest.360pro.online | Внутренний speedtest-сервис (nginx фронт + apache2 backend). docker активен. |  |  |  |  |  |  |
| 2 | 192.168.161.49 | bitrix-to-erp-integrade | интеграция Bitrix24 <-> ERP (по имени хоста). На момент аудита |  |  |  |  |  |  |
| 6 | 192.168.161.55 | fwatcher | ДВОЙНАЯ — (1) Flussonic Watcher 26.02 (видеонаблюдение/стриминг + flussonic-central, |  |  |  |  |  |  |
| 6 | 192.168.161.56 | fstreamer |  |  |  |  |  |  |  |
| 6 | 192.168.161.71 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 6 | 192.168.161.72 | ЧАСТИЧНО — нет доступа к ОС |  |  |  |  |  |  |  |
| 3 | 192.168.161.96 | tacacs.360pro.online | TACACS+ сервер (tac_plus, TCP:49) — AAA для администрирования сетевых |  |  |  |  |  |  |
| 3 | 192.168.161.100 | MultiFactorRA | Агент двухфакторной аутентификации MultiFactor — RADIUS-adapter (.NET/dotnet, |  |  |  |  |  |  |
| 3 | 192.168.161.110 | k3s-node1 | Узел кластера K3s (Kubernetes) — CONTROL-PLANE/server (k3s.service active, |  |  |  |  |  |  |
| 3 | 192.168.161.120 | k3s-node2 | Узел кластера K3s — CONTROL-PLANE/server (k3s.service active, k3s-agent |  |  |  |  |  |  |
| 3 | 192.168.161.130 | k3s-node3 | Узел кластера K3s — CONTROL-PLANE/server (k3s active, k3s-agent inactive). |  |  |  |  |  |  |
| 3 | 192.168.161.135 | OPNsense firewall |  |  |  |  |  |  |  |
| 3 | 192.168.161.140 | k3s-node4 | Узел кластера K3s — CONTROL-PLANE/server (k3s active, k3s-agent inactive). |  |  |  |  |  |  |
| 6 | 192.168.161.172 | nginx-proxy-flash | Публичный API-шлюз (нативный nginx) для домена flash-telecom. |  |  |  |  |  |  |
| 6 | 192.168.161.173 | nginx-proxy-omiplat | Публичный web/API-шлюз (нативный nginx) домена omiplat. Vhosts: |  |  |  |  |  |  |
| 6 | 192.168.161.174 | nginx-proxy-rocket | Публичный web/API-шлюз (нативный nginx) домена rocket — но ПОКА НЕ НАСТРОЕН: |  |  |  |  |  |  |
| 6 | 192.168.161.175 | nginx-proxy-rtc | Публичный web/API-шлюз (нативный nginx) домена rocket-telecom (rtc). |  |  |  |  |  |  |
| 6 | 192.168.161.176 | nginx-proxy-utc | Публичный web/API-шлюз (нативный nginx) домена omicron.online. |  |  |  |  |  |  |

## ВМ vSphere отдельно (список взять из vCenter)

Служебные ВМ vCenter/ESXi/Veeam/NTP/стенды должны быть либо в джобе, либо в списке осознанных исключений:

- [ ] `192.168.160.202` vcenter.esxi.loc (vCenter 6.7, **EOL** — встроенного бэкапа vCenter в Veeam <12 нет, нужен отдельный файловый джоб)
- [ ] ESXi-хосты парка (список — из `12-vcenter-by-esxi.txt`)
- [ ] `192.168.160.14` сам Veeam-сервер
- [ ] тестовые/золотые образы стендов

## Отдельно проверить (не ВМ-бэкапом не покрывается)

| Объект | IP | Чем бэкапится сейчас | Комментарий |
|---|---|---|---|
| Дампы БД доменов flash/omiplat/rocket/rtc/utk | от `160.135`/`160.136` | Veeam-джоб на сами серверы БД? | по аудиту `/db-backups/*` **пусты** на обоих хостах |
| Дампы БД ERP | `160.31` | ? | лежат в `/opt` с правами 0644 (world-readable) |
| Конфиги MikroTik/BRAS/сетевого оборудования | `160.11` samba, `160.42` ansible-backup-net | Oxidized **выключен** 2026-03-06, плейбуки удалены | MikroTik 60 дн, BRAS 7 дн, offsite → REG.RU |
| Kubernetes (k3s-node1..4) | `161.110/120/130/140` | Velero — установлен **без schedule и TTL** | `snapshotsEnabled: false` |
| PowerDNS | `161.18` | дамп в `/opt/pdns/backups/` — только ручной запуск | нет автоматического расписания |
| Записи звонков | ? | по `network-scheme.html:173` — **не работает с 2025-11-09** | |
| OLT / SNR / Huawei / Nexus | ? | пробел в документе схемы (`network-scheme.html:168`) | бэкап не документирован |