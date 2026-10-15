| IP | hostname | Роль | ОС | Порты наружу | SSH |
|---|---|---|---|---|---|
| **Биллинг-ядро BGBilling** (5) | | | | | |
| 172.16.100.24 | rocket-bg-core.rocket.loca | БИЛЛИНГ-ЯДРО BGBilling домена rocket (4-й bg-cor | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.110.7 | bg-core-flash.flash.local | БИЛЛИНГ-ЯДРО BGBilling | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.54 | bg-core-omiplat.omicron.lo | БИЛЛИНГ-ЯДРО BGBilling (BiTel) домена omiplat | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.87 | rtc-bg-core.rtc.local | БИЛЛИНГ-ЯДРО BGBilling домена rtc (rocket-teleco | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.101 | omicron-bg-core.omicron.lo | БИЛЛИНГ-ЯДРО BGBilling домена omicron (аналог bg | Debian GNU/Linux 11 (bullseye) | — | 22 |
| **RADIUS / AAA** (5) | | | | | |
| 172.16.100.27 | rocket-bg-radius.rocket.lo | RADIUS/AAA-сервер интернет-абонентов (BGBilling  | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.110.8 | bg-radius-flash.flash.loca | RADIUS/AAA-сервер абонентов на базе BGBilling In | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.55 | bg-radius-omiplat.omicron. | RADIUS/AAA-сервер интернет-абонентов на базе BGB | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.88 | rtc-bg-radius.rtc.local | RADIUS/AAA-сервер интернет-абонентов (BGBilling  | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.102 | omicron-bg-radius.omicron. | RADIUS/AAA-сервер интернет-абонентов на базе BGB | Debian GNU/Linux 11 (bullseye) | — | 22 |
| **ProxySQL** (5) | | | | | |
| 172.16.100.26 | ProxySQL, домен rocket | ProxySQL — прокси MySQL перед БД BGBilling домен | — | — | — |
| 192.168.110.20 | proxysql-flash.flash.local | ProxySQL 2.4.4 — прокси/балансировщик MySQL пере | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.70 | proxysql-omiplat.omicron.l | ProxySQL 2.4.4 — прокси MySQL перед БД BGBilling | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.89 | rtc-bg-proxy.rtc.local | ProxySQL 2.4.7 — прокси MySQL перед БД BGBilling | Debian GNU/Linux 11 (bullseye) | — | 22 |
| 192.168.160.103 | omicron-bg-proxy.omicron.l | ProxySQL 2.5.1 — прокси/балансировщик MySQL пере | Debian GNU/Linux 11 (bullseye) | — | 22 |
| **nginx-прокси** (6) | | | | | |
| 192.168.161.6 | nginx | Центральный EDGE reverse/stream-прокси. Публикуе | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.172 | nginx-proxy-flash | Публичный API-шлюз (нативный nginx) для домена f | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.173 | nginx-proxy-omiplat | Публичный web/API-шлюз (нативный nginx) домена o | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.174 | nginx-proxy-rocket | Публичный web/API-шлюз (нативный nginx) домена r | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.175 | nginx-proxy-rtc | Публичный web/API-шлюз (нативный nginx) домена r | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.176 | nginx-proxy-utc | Публичный web/API-шлюз (нативный nginx) домена o | Debian GNU/Linux 13 (trixie) | — | 1221 |
| **Call-центры** (6) | | | | | |
| 172.16.100.54 | CALLCENTERROCKET | Телефонная платформа call-центра ITGRIX (Asteris | Debian GNU/Linux 12 (bookworm) | 1221, 8089, 5038, 8088, 1720, 10050… | 1221 |
| 192.168.110.29 | CALLCENTERFLASH | Телефонная платформа call-центра ITGRIX (Asteris | Debian GNU/Linux 12 (bookworm) | 1221, 3306, 5038, 8088, 1720, 10050… | 1221 |
| 192.168.110.30 | CALLCENTERRTC | Телефонная платформа call-центра ITGRIX (Asteris | Debian GNU/Linux 12 (bookworm) | 1221, 8089, 3306, 5038, 8088, 1720… | 1221 |
| 192.168.160.217 | CALLCENTEROMIPLAT | Телефонная платформа call-центра ITGRIX (Asteris | Debian GNU/Linux 12 (bookworm) | 1221, 8089, 5038, 8088, 1720, 10050… | 1221 |
| 192.168.160.219 | callcenter-deb2 | Телефонная платформа call-центра на базе ITGRIX  | Debian GNU/Linux 12 (bookworm) | 1221, 3306, 1720, 4445, 8088, 10050… | 1221 |
| 192.168.161.13 | CALLCENTERUTK | Телефонная платформа call-центра ITGRIX (Asteris | Debian GNU/Linux 12 (bookworm) | 1221, 8089, 5038, 8088, 1720, 10050… | 1221 |
| **Почта / DNS** (4) | | | | | |
| 192.168.161.18 | ns1.omicron.online | Авторитетный DNS-сервер (PowerDNS, pdns_server)  | Debian GNU/Linux 11 (bullseye) | — | 1221 |
| 192.168.161.19 | ns2.omicron.online | Авторитетный DNS-сервер PowerDNS (реплика ns1) д | Debian GNU/Linux 11 (bullseye) | — | 1221 |
| 192.168.161.32 | relay1.360pro.online | Почтовый сервер/релей — Postfix (с postscreen an | Debian GNU/Linux 12 (bookworm) | 10050 | 1221 |
| 192.168.161.33 | relay2.360pro.online | Второй почтовый сервер/релей — Postfix (postscre | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| **K3s и Docker-сервисы** (9) | | | | | |
| 192.168.160.100 | wiki2 | Wiki-сервис (веб-приложение в Docker за nginx; 2 | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.160.119 | n8n.360pro.online | n8n — платформа автоматизации воркфлоу/iPaaS (в  | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.5 | netbox | NetBox — система документирования сети (IPAM/DCI | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.161.7 | git | GitLab (self-hosted, omnibus) — хранилище исходн | Debian GNU/Linux 12 (bookworm) | 1221, 5000 | 1221 |
| 192.168.161.15 | commerce.360pro.online | Контейнеризированная веб-платформа (Docker). В к | Debian GNU/Linux 12 (bookworm) | 1221, 80 | 1221 |
| 192.168.161.110 | k3s-node1 | Узел кластера K3s (Kubernetes) — CONTROL-PLANE/s | Debian GNU/Linux 12 (bookworm) | 1221, 6443, 10250, 2379, 2380, 2112 | 1221 |
| 192.168.161.120 | k3s-node2 | Узел кластера K3s — CONTROL-PLANE/server (k3s.se | Debian GNU/Linux 12 (bookworm) | 1221, 6443, 10250, 2379, 2380, 2112 | 1221 |
| 192.168.161.130 | k3s-node3 | Узел кластера K3s — CONTROL-PLANE/server (k3s ac | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.140 | k3s-node4 | Узел кластера K3s — CONTROL-PLANE/server (k3s ac | Debian GNU/Linux 12 (bookworm) | 1221, 6443, 10250, 2112, 10050 | 1221 |
| **Мониторинг** (5) | | | | | |
| 192.168.160.19 | grafana | Сервер мониторинга Grafana. Контейнер grafana/gr | Debian GNU/Linux 12 (bookworm) | 22, 3000, 9100, 10050 | 22 |
| 192.168.160.45 | prometheus | Сервер метрик Prometheus 2.54.1 + Alertmanager + | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.160.68 | oms | NOC/управление сетью. Observium (мониторинг по S | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.160.104 | zabbix-core.omicron.local | Сервер мониторинга Zabbix (zabbix_server + nginx | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.161.48 | speedtest / speedtest.360p | Внутренний speedtest-сервис (nginx фронт + apach | Debian GNU/Linux 13 (trixie) | — | 1221 |
| **VPN и доступ** (5) | | | | | |
| 192.168.161.8 | rustdesk | Self-hosted RustDesk server (удалённый доступ):  | Debian GNU/Linux 12 (bookworm) | 22, 21115, 21117, 21118, 21119 | 22 |
| 192.168.161.26 | OpenVPN | Корпоративный VPN-шлюз. OpenVPN (UDP:1194, 2 инс | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.96 | tacacs.360pro.online | TACACS+ сервер (tac_plus, TCP:49) — AAA для адми | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.100 | MultiFactorRA | Агент двухфакторной аутентификации MultiFactor — | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.135 | OPNsense firewall |  | — | — | — |
| **Хранилища и бэкапы** (3) | | | | | |
| 192.168.160.11 | Samba file server | Хранилище бэкапов конфигов сетевых устройств + к | — | — | — |
| 192.168.160.135 | db-backup1.loc | Сервер бэкапов БД. Приём дампов от СУБД-серверов | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.160.136 | db-backup2.loc | Второй сервер бэкапов БД (приём дампов по домена | Debian GNU/Linux 12 (bookworm) | — | 22 |
| **Без доступа к ОС** (6) | | | | | |
| 172.16.100.25 | ЧАСТИЧНО — нет доступа к О |  | — | — | — |
| 192.168.110.17 | ЧАСТИЧНО — нет доступа к О |  | — | — | 1221 |
| 192.168.110.110 | ЧАСТИЧНО — нет доступа к О |  | — | — | — |
| 192.168.155.253 | ЧАСТИЧНО — нет доступа к О |  | — | — | — |
| 192.168.161.71 | ЧАСТИЧНО — нет доступа к О |  | — | — | 1221 |
| 192.168.161.72 | ЧАСТИЧНО — нет доступа к О |  | — | — | — |
| **Windows / appliance** (2) | | | | | |
| 192.168.160.202 | vcenter.esxi.loc |  | — | — | — |
| 192.168.160.215 | katan.360pro.online |  | — | — | — |
| **Прочие узлы** (16) | | | | | |
| 172.16.100.45 | ЧАСТИЧНО — нет доступа к О |  | — | — | 22 |
| 192.168.160.6 | office.omicron.online |  | — | — | — |
| 192.168.160.31 | erp.360pro.online | ERP-система BGERP (ERP-модуль BGBilling, Java).  | Debian GNU/Linux 11 (bullseye) | 1221, 3306, 33060, 9088, 9104, 10050 | 1221 |
| 192.168.160.35 | call-center | Телефонная АТС call-центра — Asterisk (брендинг  | CentOS Linux release 7.9.2009  | — | 1221 |
| 192.168.160.110 | bitrix.360pro.online | self-hosted Битрикс24 (BitrixVM/Bitrix Environme | CentOS Stream release 9   (акт | — | 1221 |
| 192.168.160.118 | msVPN.360pro.online | похоже, Windows VPN-шлюз (msVPN) — RRAS/SSTP (44 | — | — | — |
| 192.168.161.4 | voiceops | Ops/управляющий узел голосового контура. Приклад | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.11 | fop2.360pro.online | FOP2 (Flash Operator Panel 2) — панель оператора | Debian GNU/Linux 13 (trixie) | 1221, 4445 | 1221 |
| 192.168.161.12 | sv1.360pro.online | Крупный МНОГОСЕРВИСНЫЙ Docker-хост (~27 контейне | Debian GNU/Linux 12 (bookworm) | — | 22 |
| 192.168.161.17 | voice1 | Голосовая платформа / voice-analytics (Docker, ~ | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.42 | ЧАСТИЧНО — нет доступа к О |  | — | — | 1221 |
| 192.168.161.45 | voice2 | Голосовая платформа/voice-analytics (Docker, ~13 | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.46 | nomoney-rocketcom | Captive-портал "нет средств" для абонентов rocke | Debian GNU/Linux 12 (bookworm) | — | 1221 |
| 192.168.161.49 | bitrix-to-erp-integrade | интеграция Bitrix24 <-> ERP (по имени хоста). На | Debian GNU/Linux 13 (trixie) | — | 1221 |
| 192.168.161.55 | fwatcher | ДВОЙНАЯ — (1) Flussonic Watcher 26.02 (видеонабл | Debian GNU/Linux 12 (bookworm) | 1221, 554, 9019, 9020, 10050 | 1221 |
| 192.168.161.56 | fstreamer |  | Debian GNU/Linux 12 (bookworm) | — | 1221 |
