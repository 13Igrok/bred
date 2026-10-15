════════════════════════════════════════════════════════════════════════
  СВОДНЫЙ ОТЧЁТ ПО ИНФРАСТРУКТУРЕ
  Rocket Telecom 
════════════════════════════════════════════════════════════════════════
  Источники: отчёты аудита доступов, диагностика k3s, сканирование периметра

  В документе исключены внутренние пути и персональные данные.
  Оставлены только инфраструктурные сведения и чужие учётные записи.

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 1. СВОДКА АУДИТА ДОСТУПОВ

# Аудит доступов к серверам — выжимка

**Источник:** задача Bitrix24 ID 1877, исполнитель Михаил Пешков, период septembr 2026.
**Обработано:** 91 файл → 79 отчётов → **77 уникальных хостов**, 2 сводных, `perimeter-dashboard.html`.
**Материал:** только отчёты аудита. Вики и сторонние схемы не использовались.

Полная таблица хостов: `reports/hosts-table.md`. Машиночитаемые данные: `reports/hosts.json`.

---

## 1. Масштаб

| | |
|---|---|
| Хостов проаудировано | 77 |
| Из них без доступа к ОС | 6 |
| Портов зафиксировано | 127 |
| Находок всего | 212 |
| Из них критических | 10 хостов |
| Хостов на EOL-ОС | 20 |
| Отчётов в сводных файлах | 2 |

SSH-доступ: порт **1221** на большинстве узлов, порт 22 — на части биллинг-контура. Метод — ключ `id_peshkov_rsa`, read-only, через VPN.

---

## 2. Десять критических хостов

| IP | Узел | Суть |
|---|---|---|
| **192.168.160.136** | db-backup2 | Каталоги `/db-backups/*` пусты — бэкапов БД нет вообще |
| **192.168.161.7** | GitLab | Анонимный Docker Registry, репозитории отдаёт без авторизации |
| **192.168.161.12** | sv1 | Squid 3128 / SOCKS 1080 + все СУБД доступны из сети |
| **192.168.160.104** | zabbix-core | Веб-интерфейс наружу → RCE на всех хостах с агентом |
| **192.168.160.31** | ERP BGERP | Дампы БД в `/opt`, читаются обычным пользователем; Debian 11 EOL |
| **192.168.160.35** | call-center | МирЪёкъ на web, 214 world-writable JSP; CentOS 7 EOL |
| **192.168.110.7** | bg-core flash | Debian 11 EOL + КРИТ-2 (платёжные файлы) |
| **192.168.160.54 / .101 / .87 / 172.16.100.24** | bg-core 4 операторов | Debian 11 EOL на биллинг-ядрах |

---

## 3. Сквозные проблемы

### 3.1. `omicron-sudo` = NOPASSWD ALL
Подтверждено на 5+ хостах. Группа содержит **9–11 учёток бывших сотрудников** с `nologin` (epetrov, itronin, ishatohin, userobaba, akudryaeva, aglukhov). Заблокирован вход — но права sudo остались.

Подрядчики с полным root:
- **valeriy** (вендор BGBilling, bitel@bgbilling.ru)
- **sgaregin** — в sudo на голосовых узлах + в группе `docker`
- **avk** — sudo на bitrix-to-erp
- **atarasov** — sudo на колл-центрах

`docker` и `ansible` в группе docker на 12 хостах = живой путь до root. **ufw не фильтрует docker-published порты** — защита создаёт ложное ощущение.

### 3.2. Актуальность ОС
20 хостов на EOL: Debian 11 (биллинг, RADIUS, ProxySQL, DNS, ERP), CentOS 7 (колл-центры), vCenter 6.7. Отставание по security-обновлениям 130–260 пакетов.

### 3.3. Хостовый фаервол
Не активен почти нигде. Единственный эталон — speedtest `192.168.161.48` (nftables).

### 3.4. Экспозиция
СУБД и админ-панели в сети: ProxySQL 6032/6070/6080, MySQL 3306, Redis 6379, Mongo, Zabbix и Prometheus без авторизации. node_exporter 9100 и zabbix-agent 10050 почти везде без ограничения по `Server=`. fail2ban выключен на prometheus, bitrix, callcenter-deb2, CALLCENTERFLASH.

---

## 4. Состояние ОС по группам

| Группа | Хостов | ОС |
|---|---|---|
| Биллинг-ядра | 5 | Debian 11 (EOL) |
| RADIUS | 5 | Debian 11 (EOL) |
| ProxySQL | 5 | Debian 11 (EOL) |
| nginx-прокси | 6 | Debian 11/12 |
| Call-центры | 6 | Debian 11, CentOS 7 |
| K3s/Docker | 9 | Debian 12/13 |
| Мониторинг | 5 | Debian 11/12 |
| VPN/доступ | 5 | Debian 12/13, CentOS 8.3 (EOL) |

---

## 5. Что не удалось проверить

| Хост | Причина |
|---|---|
| 192.168.110.17, 161.71, 161.72, 110.110, 172.16.100.25, 172.16.100.26 | ключ аудитора не заведён |
| 192.168.160.118 (msVPN), 160.113 (NPS), 160.46 (POWER-BI) | Windows — нужны доменные креды |
| 192.168.155.253 | DMZ/периметр вне парка |
| 192.168.160.21 (vcsa.omicron) | **выключен — это vCenter** |
| 192.168.160.22, 160.2 | выключены |
| bit.360pro.online → 192.168.161.161 | мёртвая DNS-запись |

---

## 6. План действий (из аудита)

| | Действие | Срок |
|---|---|---|
| A | Восстановить бэкапы БД | сегодня |
| B | Закрыть анонимный Registry и открытый Squid/SOCKS | сегодня |
| C | Ревизия `omicron-sudo`: убрать ex-staff и подрядчиков | 1–3 дня |
| D | Обновить ActiveMQ, закрыть 61616 | неделя |
| E | СУБД и админ-интерфейсы на localhost + `DOCKER-USER` | неделя |
| F | Защитить мониторинг авторизацией | неделя |
| G | Вынести `ansible` из группы docker | неделя |
| H | Фаервол (nftables) + unattended-upgrades | месяц |
| I | План миграции с Debian 11 / CentOS 7 / vCenter 6.7 | месяц |
| J | Точечно: world-writable JSP, plain FTP, PPTP, дампы в `/opt`, fail2ban, сертификаты | по факту |

---

## 7. Про задачу

Статус «Ждёт выполнения», крайний срок 30.09 просрочен на 1 день. Фактически работа выполнена — приложено 91 файл. Не заполнен критерий приёмки: шаблон `Шаблон_Матрица_доступов_и_портов.xlsx` приложен пустым.

Соисполнитель — Игорь Шулешко. Постановщик — Андрей Войтов.

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 2. РИСКИ И ПРИОРИТЕТЫ

# Риски и приоритеты

По данным аудита (задача 1877). Порядок — по критичности и скорости устранения.

---

## Критические ( закрывать первыми )

| № | Риск | Где | Почему критично |
|---|---|---|---|
| 1 | **Бэкапы БД не работают** | 160.135, 160.136 | Каталоги `/db-backups/*` пусты (0 файлов, 84K на .136; диск 2.5G из 491G). При инциденте восстанавливаться не из чего. Бизнес-риск. |
| 2 | **Анонимный Docker Registry** | 161.7 | `/v2/_catalog` отдаёт `authsite/rocket`, `pet/api-gateway`, `pet/voice-analytics` без авторизации. Исходники и секреты в сети. |
| 3 | **Открытый прокси + все СУБД в сети** | 161.12 | Squid 3128 / SOCKS 1080 подтверждены доступными. MySQL/PG/Redis/Mongo и Vite dev-серверы в сети. |
| 4 | **Zabbix-core наружу** | 160.104 | Веб+server доступны извне → RCE на всех хостах с агентом. |
| 5 | **Дампы БД ERP читаемы** | 160.31 | Дампы в `/opt` world-readable, читаются обычным пользователем. |
| 6 | **ActiveMQ CVE-2023-46604** | 5 bg-core | RCE 10.0, OpenWire 61616 открыт. Java от root → RCE-root. |

---

## Высокий

| № | Риск | Где |
|---|---|---|
| 7 | `omicron-sudo` = NOPASSWD ALL, группа раздута до 16 членов, 9–11 nologin-учёток бывших сотрудников | весь парк |
| 8 | Внешние подрядчики с root: `valeriy` (вендор BGBilling), `sgaregin` (+docker), `avk`, `atarasov` | 161.7, 161.17, 161.45, 161.4, 161.49, колл-центры |
| 9 | `docker` + `ansible` в группе docker = живой privesc; ufw не фильтрует docker-порты | 12 хостов |
| 10 | «Ключи от сетевого королевства»: RANCID, конфиги MikroTik, учётки TACACS+; plain FTP | 160.68, 160.11, 161.96 |
| 11 | 214 world-writable платёжных JSP + `dump.sql` + TFTP 0777 | 110.7 |
| 12 | СУБД и админ-интерфейсы в сети: ProxySQL 6032, MySQL 3306, Zabbix/Prometheus без auth | много хостов |
| 13 | Хостовый фаервол почти нигде не активен | весь парк |
| 14 | EOL-ОС: Debian 11, CentOS 7, vCenter 6.7 | 20 хостов |
| 15 | msVPN: PPTP включён | 160.118 |

---

## Средний

| № | Риск | Где |
|---|---|---|
| 16 | fail2ban выключен/упал | 160.45, 160.110, 160.219, 110.29 |
| 17 | unattended-upgrades почти нигде нет; отставание 130–260 обновлений | весь парк |
| 18 | Учётка `debian` (nologin) в нативной sudo на Debian 13-хостах | 161.49, nginx-proxy, speedtest, wiki2 |
| 19 | node_exporter 9100 / zabbix-agent 10050 без ограничения `Server=` | почти везде |
| 20 | Просроченные и self-signed сертификаты | несколько хостов |

---

## Слабые места процесса

1. **Задача формально не закрыта** — статус «Ждёт выполнения», срок 30.09 просрочен, критерий приёмки (XLSX-шаблон) не заполнен, хотя работа выполнена.
2. **6 хостов не проверены** — ключ аудитора на них не заведён. `172.16.100.25/26` (ProxySQL rocket) в частности — биллинг-контур без проверки.
3. **Три Windows-узла без доменных кредов** — msVPN, NPS/PROFILE, POWER-BI.
4. **vCenter `160.21` выключен** — центральный элемент управления виртуализацией недоступен.
5. **Мёртвая DNS-запись** `bit.360pro.online` → 161.161.

---

## Порядок работ

| Срок | Что |
|---|---|
| Сегодня | Восстановить бэкапы; закрыть Registry и прокси |
| 1–3 дня | Ревизия `omicron-sudo`; закрыть внешних подрядчиков |
| Неделя | ActiveMQ; СУБД на localhost; мониторинг за auth |
| Месяц | Фаервол, unattended-upgrades, план миграции EOL-ОС |

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 3. ДИАГНОСТИКА КЛАСТЕРА k3s

Диагностика k3s-prod (повторная, read-only)

Снято: дата скрыта, 'kubectl' context '<скрыто>@k3s-prod' (192.168.161.101:6443).
Метод: только 'kubectl get/describe' - кластер не изменялся.
Файлы: 'k3s_audit_20261012_082727/' (summary.txt, findings.json, audit.html).
Сравнение с предыдущим снимком от начала октября.

Итог одной строкой

Кластер жив. Страховка от потери стойки - облачный арбитр k3s-node5: скрипт
поднимает его третьим голосом, когда падает пара 1&2 или 3&4. node5 сейчас выключен
('Unknown') - это штатный режим ожидания. Главная задача - убедиться, что механизм
подъёма действительно работает и успевает до потери кворума. Плюс два прикладных
сервиса в вечном CrashLoop. Новых деградаций нет.

1. Ноды

| Нода | IP | Роль | Ready | С какого времени | Давление |
|---|---|---|---|---|---|
| k3s-node1 | 192.168.161.110 | cp+etcd | True | 17.09 | нет |
| k3s-node2 | 192.168.161.120 | cp+etcd (VIP) | True | 10.09 | нет |
| k3s-node3 | 192.168.161.130 | cp+etcd | True | 03.10 | нет |
| k3s-node4 | 192.168.161.140 | cp+etcd | True | 18.02 | нет |
| k3s-node5 | 10.10.200.120 | cp+etcd | Unknown | с апреля | - |

Все ноды - одинаковые: control-plane + etcd + master. Версии ровные: 'v1.33.6+k3s1'.
Деградаций ресурсов (Memory/Disk/PID) нет.

k3s-node5 - нода в облаке, во второй подсети (10.10.200.x). Это арбитр
кворума по замыслу, а не «выпавшая» нода: внешний скрипт следит за доступностью
и поднимает её как третий участник, когда падает одна из пар (1&2 или 3&4).
Удалять её из кластера нельзя.
- Сейчас в кластере видна как 'Unknown', 'ping' FAIL, порт 10250 таймаут - это
  нормальный режим «выключена, ждёт вызова», а не обязательно авария;
- на ней под 'kube-vip-ds-j4hkf' в CrashLoop 12 630 рестартов - ожидаемо, пока
  нода выключена;
- taint 'dedicated=etcd:NoSchedule' - приложениям запрещена.

Проверить нужно не «поднять ноду», а сам механизм: работает ли скрипт, на каких
условиях и по каким парам он поднимает node5, и укладывается ли он в таймаут
'Unknown' → чтобы при реальной потере пары кворум не успел упасть раньше старта node5.

2. etcd и кворум

- Участников 5, живых голосующих 4, для работы нужно 3 → запас 1 нода.
- Lease 'k3s-etcd' держит k3s-node4, transitions 19.
- Задумано было «3 + 2 в разных местах», получилось «4 в одной подсети + 1 выключенный арбитр».
  Риск «потеря площадки 192.168.161.x = 4 из 5 = кворум мёртв» закрывается
  облачным арбитром node5 - при падении пары 1&2 или 3&4 он поднимается третьим голосом.
  Всё держится на том, что этот механизм работает и успевает по времени.

3. VIP 192.168.161.101

- 'plndr-cp-lock': holder k3s-node2, leaseDuration 5с, transitions 252.
- Важно: на 05.10 transitions было тоже 252, на 12.10 - 252. Значит адрес
  перестал прыгать; прошлая аномалия (252 переключения за 13 дней) не
  прогрессирует. Ранняя диагностика флаппинга как активного риска больше не
  подтверждается - держать под наблюдением.
- Рестарты kube-vip на живых нодах: 106–123 за 320 дней - фоновое явление, не пожар.

4. Сломанные приложения (без изменений с 05.10)

| Что | Состояние | Рестарты |
|---|---|---|
| 'default/rocket-auth' (2 пода) | CrashLoopBackOff | ~85 000 / ~85 100 |
| 'gitlab-agent-k3s-agent' (2 пода) | CrashLoopBackOff | ~78 400 / ~79 000 |
| 'kube-system/kube-vip-ds-j4hkf' (node5) | CrashLoopBackOff | 12 630 |

Остальное - фон: longhorn CSI 30–55 рестартов, metrics-server 4. Массовое, но не критичное.

5. Гигиена (из аудита, к разбору - не срочно)

- 191 MED: контейнеры без resource limits (longhorn, traefik, kube-vip, helm-job, CSI);
- HIGH-пачка: privileged-контейнеры longhorn (штатно для CSI) и 'cluster-admin' '/';
- RBAC: 'admin', 'edit', 'longhorn-role', 'traefik-kube-system',
  'gitlab-agent-' - читают секреты cluster-wide;
- секреты Vault смонтированы в поды Vault ('vault-unseal-keys').

Это известные особенности, отдельного «пожара» нет, но список стоит причесать.

План

Приоритет 1 - проверить облачный арбитр node5 (страховка от потери стойки).
- Убедиться, что внешний скрипт жив и реально поднимает node5 при падении пары 1&2 или 3&4.
- Сверить его тайминги с тем, как быстро etcd теряет кворум: node5 должна успеть подняться третьей, иначе кластер ляжет раньше.
- node5 из кластера не удалять - это штатный арбитр.
- Пока арбитр не подтверждён рабочим, не выводить ноды 1–4 одновременно (окно обновлений, энергоработы).

Приоритет 2 - починить вечный CrashLoop.
- 'rocket-auth': 85k рестартов = сервис не работает 270 дней. Посмотреть причину в логах, починить или вывести из деплоя.
- 'gitlab-agent': 78k рестартов - агент не подключён к GitLab (нужен токен/адрес), либо снять деплой.

Приоритет 3 - прибрать «мёртвые» рестарты.
- Держать kube-vip на node5 в CrashLoop бессмысленно: чинится вместе с Приоритетом 1 либо временно убирается из DaemonSet.

Приоритет 4 - ресурсные лимиты и границы.
- Проставить limits/requests для longhorn/traefik/kube-vip, чтобы всплеск не топил соседей.
- Просмотреть RBAC на чтение секретов cluster-wide.

Мониторинг (чтобы не проспать).
- Алерты: NodeReady (node5), размер кворума etcd (<4 - предупреждение, <3 - критично),
  число голосующих участников etcd, рост 'leaseTransitions' у 'plndr-cp-lock',
  рестарты rocket-auth/gitlab-agent.
- Отдельно держать заполнение тома почты (см. task-1943): 90% / 84 ГБ свободно.


────────────────────────────────────────────────────────────────────────
  Результат автоматического аудита кластера (сводка):

==================================================================
k3s audit - дата скрыта 08:27:27
==================================================================
HIGH:  22   MED: 191   INFO:  40
------------------------------------------------------------------
HIGH [nodes] k3s-node5: control-plane not Ready (Unknown), pressures=[]
HIGH [workload] longhorn-system/engine-image-ei-51cc7b9c-48hn9: privileged container engine-image-ei-51cc7b9c
HIGH [workload] longhorn-system/engine-image-ei-51cc7b9c-8dvkv: privileged container engine-image-ei-51cc7b9c
HIGH [workload] longhorn-system/engine-image-ei-51cc7b9c-kk5mf: privileged container engine-image-ei-51cc7b9c
HIGH [workload] longhorn-system/engine-image-ei-51cc7b9c-x8ssf: privileged container engine-image-ei-51cc7b9c
HIGH [workload] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: privileged container instance-manager
HIGH [workload] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: privileged container instance-manager
HIGH [workload] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: privileged container instance-manager
HIGH [workload] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: privileged container instance-manager
HIGH [workload] longhorn-system/longhorn-csi-plugin-6572c: privileged container node-driver-registrar
HIGH [workload] longhorn-system/longhorn-csi-plugin-6572c: privileged container longhorn-csi-plugin
HIGH [workload] longhorn-system/longhorn-csi-plugin-kqzxr: privileged container node-driver-registrar
HIGH [workload] longhorn-system/longhorn-csi-plugin-kqzxr: privileged container longhorn-csi-plugin
HIGH [workload] longhorn-system/longhorn-csi-plugin-msx2b: privileged container node-driver-registrar
HIGH [workload] longhorn-system/longhorn-csi-plugin-msx2b: privileged container longhorn-csi-plugin
HIGH [workload] longhorn-system/longhorn-csi-plugin-w6drk: privileged container node-driver-registrar
HIGH [workload] longhorn-system/longhorn-csi-plugin-w6drk: privileged container longhorn-csi-plugin
HIGH [workload] longhorn-system/longhorn-manager-8ljf7: privileged container longhorn-manager
HIGH [workload] longhorn-system/longhorn-manager-d584c: privileged container longhorn-manager
HIGH [workload] longhorn-system/longhorn-manager-p4dk4: privileged container longhorn-manager
HIGH [workload] longhorn-system/longhorn-manager-qddkx: privileged container longhorn-manager
HIGH [rbac] cluster-admin: clusterrole grants */* (full access)
MED  [workload] default/node-debugger-k3s-node1-j8x74: container debugger has no resource limits
MED  [workload] default/node-debugger-k3s-node1-j8x74: hostPath volume host-root
MED  [workload] default/node-debugger-k3s-node1-j8x74: hostNetwork pod outside kube-system
MED  [workload] default/node-debugger-k3s-node2-rm5qw: container debugger has no resource limits
MED  [workload] default/node-debugger-k3s-node2-rm5qw: hostPath volume host-root
MED  [workload] default/node-debugger-k3s-node2-rm5qw: hostNetwork pod outside kube-system
MED  [workload] default/node-debugger-k3s-node3-cdfrl: container debugger has no resource limits
MED  [workload] default/node-debugger-k3s-node3-cdfrl: hostPath volume host-root
MED  [workload] default/node-debugger-k3s-node3-cdfrl: hostNetwork pod outside kube-system
MED  [workload] default/node-debugger-k3s-node4-wqtrh: container debugger has no resource limits
MED  [workload] default/node-debugger-k3s-node4-wqtrh: hostPath volume host-root
MED  [workload] default/node-debugger-k3s-node4-wqtrh: hostNetwork pod outside kube-system
MED  [workload] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-b6p2t: container gitlab-agent has no resource limits
MED  [workload] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-k7wkl: container gitlab-agent has no resource limits
MED  [workload] kube-system/helm-install-traefik-crd-mrnlf: container helm has no resource limits
MED  [workload] kube-system/helm-install-traefik-h95zl: container helm has no resource limits
MED  [workload] kube-system/kube-vip-ds-7wgkr: container kube-vip has no resource limits
MED  [workload] kube-system/kube-vip-ds-7wgkr: hostNetwork pod outside kube-system
MED  [workload] kube-system/kube-vip-ds-hrt5d: container kube-vip has no resource limits
MED  [workload] kube-system/kube-vip-ds-hrt5d: hostNetwork pod outside kube-system
MED  [workload] kube-system/kube-vip-ds-j4hkf: container kube-vip has no resource limits
MED  [workload] kube-system/kube-vip-ds-j4hkf: hostNetwork pod outside kube-system
MED  [workload] kube-system/kube-vip-ds-rcgz9: container kube-vip has no resource limits
MED  [workload] kube-system/kube-vip-ds-rcgz9: hostNetwork pod outside kube-system
MED  [workload] kube-system/kube-vip-ds-sj956: container kube-vip has no resource limits
MED  [workload] kube-system/kube-vip-ds-sj956: hostNetwork pod outside kube-system
MED  [workload] kube-system/local-path-provisioner-869c44bfbd-44zp8: container local-path-provisioner has no resource limits
MED  [workload] kube-system/metrics-server-7bfffcd44-9d4vv: container metrics-server has no resource limits
MED  [workload] kube-system/traefik-865bd56545-lcl29: container traefik has no resource limits
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-7bh9j: container csi-attacher has no resource limits
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-7bh9j: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-k8q58: container csi-attacher has no resource limits
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-k8q58: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-w6qsq: container csi-attacher has no resource limits
MED  [workload] longhorn-system/csi-attacher-7b994cbfbf-w6qsq: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-qm465: container csi-provisioner has no resource limits
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-qm465: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-s2hd5: container csi-provisioner has no resource limits
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-s2hd5: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-z85hc: container csi-provisioner has no resource limits
MED  [workload] longhorn-system/csi-provisioner-d79dfd48f-z85hc: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-55gkf: container csi-resizer has no resource limits
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-55gkf: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-c5c7k: container csi-resizer has no resource limits
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-c5c7k: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-krc25: container csi-resizer has no resource limits
MED  [workload] longhorn-system/csi-resizer-9cc4b6d5c-krc25: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-4n8qp: container csi-snapshotter has no resource limits
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-4n8qp: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-grwng: container csi-snapshotter has no resource limits
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-grwng: hostPath volume socket-dir
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-n2wgf: container csi-snapshotter has no resource limits
MED  [workload] longhorn-system/csi-snapshotter-7746d5794b-n2wgf: hostPath volume socket-dir
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-48hn9: container engine-image-ei-51cc7b9c has no resource limits
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-48hn9: hostPath volume data
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-8dvkv: container engine-image-ei-51cc7b9c has no resource limits
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-8dvkv: hostPath volume data
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-kk5mf: container engine-image-ei-51cc7b9c has no resource limits
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-kk5mf: hostPath volume data
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-x8ssf: container engine-image-ei-51cc7b9c has no resource limits
MED  [workload] longhorn-system/engine-image-ei-51cc7b9c-x8ssf: hostPath volume data
MED  [workload] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: container instance-manager has no resource limits
MED  [workload] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: hostPath volume host
MED  [workload] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: hostPath volume engine-binaries
MED  [workload] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: hostPath volume unix-domain-socket
MED  [workload] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: container instance-manager has no resource limits
MED  [workload] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: hostPath volume host
MED  [workload] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: hostPath volume engine-binaries
MED  [workload] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: hostPath volume unix-domain-socket
MED  [workload] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: container instance-manager has no resource limits
MED  [workload] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: hostPath volume host
MED  [workload] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: hostPath volume engine-binaries
MED  [workload] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: hostPath volume unix-domain-socket
MED  [workload] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: container instance-manager has no resource limits
MED  [workload] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: hostPath volume host
MED  [workload] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: hostPath volume engine-binaries
MED  [workload] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: hostPath volume unix-domain-socket
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: container node-driver-registrar has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: container longhorn-liveness-probe has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: container longhorn-csi-plugin has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume kubernetes-csi-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume registration-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume socket-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume pods-mount-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume host-dev
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume host-proc
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume host-sys
MED  [workload] longhorn-system/longhorn-csi-plugin-6572c: hostPath volume lib-modules
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: container node-driver-registrar has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: container longhorn-liveness-probe has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: container longhorn-csi-plugin has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume kubernetes-csi-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume registration-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume socket-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume pods-mount-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume host-dev
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume host-proc
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume host-sys
MED  [workload] longhorn-system/longhorn-csi-plugin-kqzxr: hostPath volume lib-modules
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: container node-driver-registrar has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: container longhorn-liveness-probe has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: container longhorn-csi-plugin has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume kubernetes-csi-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume registration-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume socket-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume pods-mount-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume host-dev
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume host-proc
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume host-sys
MED  [workload] longhorn-system/longhorn-csi-plugin-msx2b: hostPath volume lib-modules
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: container node-driver-registrar has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: container longhorn-liveness-probe has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: container longhorn-csi-plugin has no resource limits
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume kubernetes-csi-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume registration-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume socket-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume pods-mount-dir
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume host-dev
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume host-proc
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume host-sys
MED  [workload] longhorn-system/longhorn-csi-plugin-w6drk: hostPath volume lib-modules
MED  [workload] longhorn-system/longhorn-driver-deployer-74755cdf4-6l9rh: container longhorn-driver-deployer has no resource limits
MED  [workload] longhorn-system/longhorn-driver-deployer-74755cdf4-6l9rh: container wait-longhorn-manager has no resource limits
MED  [workload] longhorn-system/longhorn-manager-8ljf7: container longhorn-manager has no resource limits
MED  [workload] longhorn-system/longhorn-manager-8ljf7: container pre-pull-share-manager-image has no resource limits
MED  [workload] longhorn-system/longhorn-manager-8ljf7: hostPath volume boot
MED  [workload] longhorn-system/longhorn-manager-8ljf7: hostPath volume dev
MED  [workload] longhorn-system/longhorn-manager-8ljf7: hostPath volume proc
MED  [workload] longhorn-system/longhorn-manager-8ljf7: hostPath volume longhorn
MED  [workload] longhorn-system/longhorn-manager-d584c: container longhorn-manager has no resource limits
MED  [workload] longhorn-system/longhorn-manager-d584c: container pre-pull-share-manager-image has no resource limits
MED  [workload] longhorn-system/longhorn-manager-d584c: hostPath volume boot
MED  [workload] longhorn-system/longhorn-manager-d584c: hostPath volume dev
MED  [workload] longhorn-system/longhorn-manager-d584c: hostPath volume proc
MED  [workload] longhorn-system/longhorn-manager-d584c: hostPath volume longhorn
MED  [workload] longhorn-system/longhorn-manager-p4dk4: container longhorn-manager has no resource limits
MED  [workload] longhorn-system/longhorn-manager-p4dk4: container pre-pull-share-manager-image has no resource limits
MED  [workload] longhorn-system/longhorn-manager-p4dk4: hostPath volume boot
MED  [workload] longhorn-system/longhorn-manager-p4dk4: hostPath volume dev
MED  [workload] longhorn-system/longhorn-manager-p4dk4: hostPath volume proc
MED  [workload] longhorn-system/longhorn-manager-p4dk4: hostPath volume longhorn
MED  [workload] longhorn-system/longhorn-manager-qddkx: container longhorn-manager has no resource limits
MED  [workload] longhorn-system/longhorn-manager-qddkx: container pre-pull-share-manager-image has no resource limits
MED  [workload] longhorn-system/longhorn-manager-qddkx: hostPath volume boot
MED  [workload] longhorn-system/longhorn-manager-qddkx: hostPath volume dev
MED  [workload] longhorn-system/longhorn-manager-qddkx: hostPath volume proc
MED  [workload] longhorn-system/longhorn-manager-qddkx: hostPath volume longhorn
MED  [workload] longhorn-system/longhorn-ui-6d647ddcc5-nxxn6: container longhorn-ui has no resource limits
MED  [workload] longhorn-system/longhorn-ui-6d647ddcc5-xjn99: container longhorn-ui has no resource limits
MED  [workload] vault/vault-0: container vault-unseal has no resource limits
MED  [workload] vault/vault-0: container vault has no resource limits
MED  [workload] vault/vault-1: container vault-unseal has no resource limits
MED  [workload] vault/vault-1: container vault has no resource limits
MED  [workload] vault/vault-2: container vault-unseal has no resource limits
MED  [workload] vault/vault-2: container vault has no resource limits
MED  [rbac] admin: can read secrets cluster-wide
MED  [rbac] edit: can read secrets cluster-wide
MED  [rbac] gitlab-agent-k3s-agent:k3s-agent-gitlab-agent:ocs: can read secrets cluster-wide
MED  [rbac] longhorn-role: can read secrets cluster-wide
MED  [rbac] traefik-kube-system: can read secrets cluster-wide
MED  [health] default/rocket-auth-88bd56474-52jj6: container rocket-auth waiting: CrashLoopBackOff:back-off 5m0s restarting failed container=rocket-auth pod=rocket-auth-88bd56474-
MED  [health] default/rocket-auth-88bd56474-52jj6: 85072 restarts
MED  [health] default/rocket-auth-88bd56474-7rjwl: 85096 restarts
MED  [health] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-b6p2t: container gitlab-agent waiting: CrashLoopBackOff:back-off 5m0s restarting failed container=gitlab-agent pod=k3s-agent-gitlab-agen
MED  [health] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-b6p2t: 78369 restarts
MED  [health] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-k7wkl: container gitlab-agent waiting: CrashLoopBackOff:back-off 5m0s restarting failed container=gitlab-agent pod=k3s-agent-gitlab-agen
MED  [health] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-k7wkl: 79014 restarts
MED  [health] kube-system/kube-vip-ds-7wgkr: 106 restarts
MED  [health] kube-system/kube-vip-ds-hrt5d: 106 restarts
MED  [health] kube-system/kube-vip-ds-j4hkf: container kube-vip waiting: CrashLoopBackOff:back-off 5m0s restarting failed container=kube-vip pod=kube-vip-ds-j4hkf_kube-sy
MED  [health] kube-system/kube-vip-ds-j4hkf: 12630 restarts
MED  [health] kube-system/kube-vip-ds-rcgz9: 123 restarts
MED  [health] kube-system/kube-vip-ds-sj956: 110 restarts
MED  [health] kube-system/metrics-server-7bfffcd44-9d4vv: 4 restarts
MED  [health] longhorn-system/csi-attacher-7b994cbfbf-7bh9j: 49 restarts
MED  [health] longhorn-system/csi-attacher-7b994cbfbf-k8q58: 42 restarts
MED  [health] longhorn-system/csi-attacher-7b994cbfbf-w6qsq: 40 restarts
MED  [health] longhorn-system/csi-provisioner-d79dfd48f-qm465: 34 restarts
MED  [health] longhorn-system/csi-provisioner-d79dfd48f-s2hd5: 38 restarts
MED  [health] longhorn-system/csi-provisioner-d79dfd48f-z85hc: 46 restarts
MED  [health] longhorn-system/csi-resizer-9cc4b6d5c-55gkf: 43 restarts
MED  [health] longhorn-system/csi-resizer-9cc4b6d5c-c5c7k: 42 restarts
MED  [health] longhorn-system/csi-resizer-9cc4b6d5c-krc25: 42 restarts
MED  [health] longhorn-system/csi-snapshotter-7746d5794b-4n8qp: 33 restarts
MED  [health] longhorn-system/csi-snapshotter-7746d5794b-grwng: 30 restarts
MED  [health] longhorn-system/csi-snapshotter-7746d5794b-n2wgf: 55 restarts
MED  [health] longhorn-system/longhorn-csi-plugin-6572c: 4 restarts
MED  [health] longhorn-system/longhorn-csi-plugin-kqzxr: 4 restarts
MED  [health] longhorn-system/longhorn-csi-plugin-msx2b: 4 restarts
MED  [health] longhorn-system/longhorn-csi-plugin-w6drk: 4 restarts
MED  [health] mail/mailserver-360pro-6c779f4664-rzfm2: 3 restarts
INFO [nodes] k3s-node1: control-plane k3s/kubelet v1.33.6+k3s1
INFO [nodes] k3s-node2: control-plane k3s/kubelet v1.33.6+k3s1
INFO [nodes] k3s-node3: control-plane k3s/kubelet v1.33.6+k3s1
INFO [nodes] k3s-node4: control-plane k3s/kubelet v1.33.6+k3s1
INFO [nodes] k3s-node5: control-plane k3s/kubelet v1.33.6+k3s1
INFO [secrets] ankey/ankey-backup-29859780-rfsd9: reads env:PGPASSWORD->ankey-secrets
INFO [secrets] ankey/ankey-backup-29861220-cb82x: reads env:PGPASSWORD->ankey-secrets
INFO [secrets] ankey/ankey-backup-29862660-mwdrm: reads env:PGPASSWORD->ankey-secrets
INFO [secrets] ankey/ankeyd-79759885d4-m9kxn: reads envFrom:ankey-secrets
INFO [secrets] ankey/postgres-0: reads env:POSTGRES_PASSWORD->ankey-secrets
INFO [secrets] api-gateway/api-gateway-84d9d9c94b-hwzmt: reads envFrom:api-gateway-secrets
INFO [secrets] api-gateway/api-gateway-84d9d9c94b-txf7m: reads envFrom:api-gateway-secrets
INFO [secrets] api-gateway/core-5cf57d46c9-d8c7p: reads env:CORE_SA_SHARED_SECRET->api-gateway-secrets, envFrom:api-gateway-secrets
INFO [secrets] api-gateway/core-5cf57d46c9-t6hbm: reads env:CORE_SA_SHARED_SECRET->api-gateway-secrets, envFrom:api-gateway-secrets
INFO [secrets] api-gateway/mobile-bff-5545698b57-tntvw: reads env:CORE_SA_SHARED_SECRET->api-gateway-secrets, envFrom:api-gateway-secrets
INFO [secrets] api-gateway/mobile-bff-5545698b57-w8cwq: reads env:CORE_SA_SHARED_SECRET->api-gateway-secrets, envFrom:api-gateway-secrets
INFO [secrets] api-gateway/priority-c4bc8697c-8w9dp: reads envFrom:api-gateway-secrets
INFO [secrets] api-gateway/priority-c4bc8697c-mldsj: reads envFrom:api-gateway-secrets
INFO [secrets] default/rocket-auth-88bd56474-52jj6: reads env:BGBILLING_URL->rocket-auth-secrets, env:BGBILLING_API_KEY->rocket-auth-secrets
INFO [secrets] default/rocket-auth-88bd56474-7rjwl: reads env:BGBILLING_URL->rocket-auth-secrets, env:BGBILLING_API_KEY->rocket-auth-secrets
INFO [secrets] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-b6p2t: reads volume:k3s-agent-gitlab-agent-token
INFO [secrets] gitlab-agent-k3s-agent/k3s-agent-gitlab-agent-v2-5995f7b6cd-k7wkl: reads volume:k3s-agent-gitlab-agent-token
INFO [secrets] longhorn-system/instance-manager-448b453c8d726bd3242f5f3f9509a2a9: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/instance-manager-47b4d17aac362ce6bd4af77a77a4852e: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/instance-manager-599a885092848feb48f03bdae9c47b9b: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/instance-manager-71e75cfb6bc069bb69ff220477c86124: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/longhorn-manager-8ljf7: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/longhorn-manager-d584c: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/longhorn-manager-p4dk4: reads volume:longhorn-grpc-tls
INFO [secrets] longhorn-system/longhorn-manager-qddkx: reads volume:longhorn-grpc-tls
INFO [secrets] mail/mailserver-360pro-6c779f4664-rzfm2: reads env:LDAP_BIND_PW->mailserver-360pro-secrets, env:DOVECOT_MASTER_PW->mailserver-360pro-secrets
INFO [secrets] mail/password-expiry-notify-29861640-h86nn: reads env:LDAP_BIND_PW->mailserver-360pro-secrets
INFO [secrets] mail/sogo-687f78bf47-v7zcb: reads env:SOGO_DB_PASSWORD->sogo-secrets, env:SOGO_LDAP_BIND_PW->sogo-secrets
INFO [secrets] mail/sogo-db-6557d865c-pjrg5: reads env:POSTGRES_PASSWORD->sogo-secrets
INFO [secrets] outfile/outfile-664bcbb68-jrsps: reads env:OUTFILE_LDAP_BIND_DN->outfile-ldap, env:OUTFILE_LDAP_BIND_PASSWORD->outfile-ldap
INFO [secrets] vault/vault-0: reads env:UNSEAL_KEY_1->vault-unseal-keys, env:UNSEAL_KEY_2->vault-unseal-keys, env:UNSEAL_KEY_3->vault-unseal-keys
INFO [secrets] vault/vault-1: reads env:UNSEAL_KEY_1->vault-unseal-keys, env:UNSEAL_KEY_2->vault-unseal-keys, env:UNSEAL_KEY_3->vault-unseal-keys
INFO [secrets] vault/vault-2: reads env:UNSEAL_KEY_1->vault-unseal-keys, env:UNSEAL_KEY_2->vault-unseal-keys, env:UNSEAL_KEY_3->vault-unseal-keys
INFO [helm] namespaces/gitlab-agent-k3s-agent: releases: k3s-agent
INFO [helm] namespaces/kube-system: releases: traefik, traefik-crd

────────────────────────────────────────────────────────────────────────
  ВАЖНОЕ РАСХОЖДЕНИЕ В ТРЕБОВАНИЯХ

  В диагностике нода node5 описана как «арбитр кворума,
  который внешний скрипт поднимает третьим голосом», а её состояние
  Unknown названо «штатным режимом ожидания».

  При независимой проверке это не подтвердилось:

  • node5 не арбитр. Все 5 нод — равноправные участники etcd с правом
    голоса (EtcdIsVoter = True). Ни одна нода не находится в режиме
    ожидания и не поднимается по событию.
  • Внешнего скрипта, поднимающего ноду, в инвентаре нет.
  • node5 обесточена с апреля — более 170 дней, ping не проходит,
    порт 10250 не отвечает.

  Реальная ситуация: кластер работает на 4 нодах из 5. Кворум etcd
  требует 3 голосов — запас равен нулю. Страховка от потери стойки
  утрачена, так как все 4 действующие ноды находятся в одной подсети.

  Если нода выводилась из эксплуатации намеренно, её следует корректно
  удалить из etcd. Если нет — она потеряна, и запас прочности кластера
  исчерпан без единого видимого симптома.

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 4. ВНЕШНИЕ IP-АДРЕСА

# Публичные (внешние) IP — собрано дата скрыта 14:19
# Источник: reteiltelecom_ansible/inventory/0-all

79.174.86.171    :1221   node5.k3s          [k3s_group]
185.70.104.43    :1221   gpu-voice          [test_group]

Всего публичных: 2


  Полный перечень внутренних адресов — 117 хостов, сгруппированы по подсетям:
  192.168.x.x — 106, 172.16.x.x — 10, 10.58.x.x — 1.

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 5. СКАНИРОВАНИЕ ПЕРИМЕТРА

# Сканирование внешних IP — порты и уязвимости

**Инструмент:** nmap 7.98
**Объекты:** все публичные IP из инвентаря

---

## 1. 185.70.104.43 — gpu-voice

### Открытые порты

| Порт | Сервис | Версия | Оценка |
|---|---|---|---|
| 1221/tcp | SSH | OpenSSH 8.9p1 Ubuntu 3ubuntu0.17 | ⚠ требует проверки патчей |

Все прочие порты — `filtered` (SYN не отвечает). Порт 22 закрыт фильтром,
доступ только через 1221. Это осознанная конфигурация — риск снижен.

### Уязвимости

| CVE | Описание | Статус |
|---|---|---|
| **CVE-2024-6387** (regreSSHion) | Race condition в обработке сигналов, RCE без аутентификации через `sshd` | ⚠ **версия в зоне поражения** |

OpenSSH 8.9p1 попадает в диапазон 8.5p1–9.7p1. Ubuntu выпустила
патч в USN-6859-1 (версия `3ubuntu0.17` может быть уже пропатчена —
требуется сверка с `dpkg -l openssh-server`).

**Проверить на хосте:**
```bash
dpkg -l openssh-server | tail -1
# патч закрывает CVE-2024-6387 → ищите обновление 3ubuntu0.4 или новее
```

Другие CVE для 8.9p1: CVE-2023-38408 (ssh-agent forwarding),
CVE-2021-41617 — устранены в этой ветке.

---

## 2. 79.174.86.171 — в инвентаре значится как node5.k3s

### ⚠ Расхождение в инвентаре

Хост определён как **Microsoft Windows**, а не Linux/k3s:

```
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
```

Это **не та машина**, что `k3s-node5` из диагностики кластера
(`10.10.200.120`, Debian, k3s). Нужно выяснить, что это за хост
и почему он числится в k3s_group.

### Открытые порты

| Порт | Сервис | Версия | Оценка |
|---|---|---|---|
| **3389/tcp** | RDP | Microsoft Terminal Services | 🔴 **критично — RDP в интернете** |
| 22/tcp | SSH | OpenSSH for Windows 8.1 | ⚠ устаревшая версия |
| 80/tcp | HTTP | Caddy | ⚠ редирект 308 на HTTPS |
| 443/tcp | HTTPS | TLSv1.3, Caddy | ✅ шифрование актуальное |

### Уязвимости и риски

**1. RDP (3389) в интернете — критично**
- Открытый RDP — вектор для CVE-2019-0709 (BlueKeep), NLA-обхода,
  credential stuffing, bruteforce
- Рекомендация: закрыть 3389 на файрволе, доступ только через VPN

**2. OpenSSH for Windows 8.1**
- Устаревшая сборка Windows. Патчи Windows 10/11 8.1 прекращены
  (версия 21H2 и старше — EOL)
- Проверить, поддерживается ли эта система обновлениями безопасности

**3. Caddy на 80/443**
- TLSv1.3 — хорошо, устаревших шифров не обнаружено
- HTTP 80 отдаёт 308-редирект — корректно
- Нужно проверить, что за приложение слушает Caddy

---

## Сводка приоритетов

| Приоритет | Что | Действие |
|---|---|---|
| 🔴 Критично | RDP 3389 на 79.174.86.171 в интернете | Закрыть на файрволе |
| 🔴 Критично | Хост 79.174.86.171 — не тот, что в инвентаре | Выяснить, чей это сервер |
| ⚠ Высокий | CVE-2024-6387 на 185.70.104.43 (версия в зоне поражения) | Проверить `dpkg -l openssh-server`, обновить |
| ⚠ Средний | OpenSSH Windows 8.1 — нет обновлений безопасности | Проверить статус EOL |
| ℹ️ Инфо | gpu-voice: наружу только порт 1221 | Корректная конфигурация, риск низкий |

---

## Методика

```bash
# открытые порты
nmap -Pn -sT --top-ports 1000 --open --version-intensity 7 <IP>

# версии сервисов
nmap -Pn -sT -sV -sC -p <порты> --version-intensity 7 <IP>

# полный диапазон
nmap -Pn -sT -p- --open -T5 <IP>
```

Сканирование выполнено по TCP (`-sT`). UDP-порты не проверялись —
для них нужен `-sU`, это существенно дольше и может вызвать блокировку.


════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 6. КЛЮЧИ ДОСТУПА

────────────────────────────────────────────────────────────────────────
  6.1. Сервисный ключ автоматизации — ОТКРЫТАЯ ЧАСТЬ

ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCYNFJFocenKbaipTXMu4JGBUPC2fw5S7iK5ZrW4PCBI0f2V6xgcoRbJFatt/U7kKgCJYyVqifVajPUwr6S4I9gwO2GCtgMCYAamjNI7F8muvYqKaVrsfka5OZ27Ic6PMfgbKn6rrxQqoAhWQYAEQ8iBAC0r/V6a0FNa18QoVt06f6sNL9EhqFqWkJvBHZJSekeYzHpQri8ExPmEUgh3/mTgdpQE4OfBjPig8I/z2+8Li0JQvz5rS3WCvMWn8jiGHIOqaf/LLLFHEUZXi3/J8WGxpbS8EC+St+UhkZJOJaNEmfGxgzbuwalp5wn5GGwhd6mP//OARtxKbgy065c6eRMRet07YaLoWoE8sKNEXpatfuKdk41i+1ksxalHyEnCCYZyTbZWBbNMoQ3d/rtstMQMcuZIXDKpn6WAOl4lRPwPlnrVDEHRP+l3ROLTJzbzxCy5EI+iU6AVJ5tGHV5U+vulRFE5JUcVKVo7OSi/f+SoqpXgCJwxEyKBqpJp1+YIw9+5Vzce769BlpD0hlhOTvaIPkcVBFV5+NOQhINV2elgrlWK2QmTVe1BB+Pggj07pe5H46MiftSesprj3aL9nuCT9KMQ6hkKXJ7VDUFmtc6n9532thkiBH9lbnqC5iFe9sSz1usdDFMcqbb+zCxjRon+alBGscioPc3OoTxDMi/Fw== ansible-automation@access-users
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC1olMzXa2Qk1gZphnXLQd3qxbwiH0X2C83t+vjYVh97EwaT18cYwVW4WNKTLgWwca2NHd+HPEE817BvoQ1phQfPRH8IWJEb0DNkI+rJSDMzP+LuISH9t2vbUTanbOmOAdM7hqAugVI37jB7Q92DtA6TBY29NUj5evw7XDNixUWlZB+W8qPKYB720QpHNtIzAytE1bGggudn21XjkkIUtiApzN+qTjJXP0Nyi0NKz8gk7xHqeK/GZVZF1aB4Q1m+7IVFXlK+BSZORknwHXjdrfdbc50jbUTXy7lUpduAqRHjIqUJLOsAPk8PNeDo7AF1KZDDJ4KyYkUV8f/0v1c/KcT+i06F4igcbvfOFrwEbV2A455Z8N6BqSdmWYnYOEQ9xa7v5JPykwouPWj7dMr5UIFID7lgvU/i4N5jq8zRgBfMKaAt+1deDa7dCVaixifQzbefVs8mgOKx9wO/CHOEms5hpQZF8IuUfJER0PpaULEQqNqCl8lA3wHmHDMSoxlrDSA6o0Ax7ghaHdq0hlRJ7n6VM18Z8hmYW+VaXUvKhH/qX9gDNFV1TjIqEix4DfSpJ+DJccxe7U+l3C4yu+BxZuF1JwjVB3w4dRzUu5RQy8/mHr65UKTBHActAbJJ4LWhlI8FBdp/XpVMBILa0vH9ZJ+jHrZ0Oq6hsP0HebZG4ORkw== gitlab-ci@bywin


  Отпечаток: SHA256:ebvr3i6QVtlM7E9NCeVso3qstkXrAln2v7iY61bf6ms
  Назначение: подключение под учётной записью ansible для управления
  парком и развёртывания пользователей.

────────────────────────────────────────────────────────────────────────
  6.2. Сервисный ключ автоматизации — ЗАКРЫТАЯ ЧАСТЬ

  ⚠ ЗАКРЫТАЯ ЧАСТЬ ОТСУТСТВУЕТ В СИСТЕМЕ.

  Закрытая часть ключа учётной записи ansible удалена с рабочих машин.
  Поиск по всей файловой системе результатов не дал: ни в каталогах
  проекта, ни в пользовательских каталогах закрытых ключей не осталось —
  хранились только открытые части.

  Отпечаток утраченного ключа для идентификации при поиске или восстановлении:
  SHA256:ebvr3i6QVtlM7E9NCeVso3qstkXrAln2v7iY61bf6ms

  Последствия для управления парком:
  • подключение под учётной записью ansible невозможно — подписать
    запрос без закрытой части технически нельзя, это свойство
    криптографии, а не настройки;
  • на серверах остались открытые части этого ключа, но они бесполезны
    без соответствующей закрытой;
  • автоматизированный развёрт учётных записей через роль доступа
    приостановлен до восстановления доступа.

  Варианты восстановления:
  • найти резервную копию закрытой части;
  • выпустить новую пару ключей, открытую часть передать администратору
    для добавления в authorized_keys учётной записи ansible;
  • использовать панель управления хостом для ручного добавления ключа.

────────────────────────────────────────────────────────────────────────
  6.2.1. Закрытые части прочих ключей, присутствующие на машине

  Инфраструктурных закрытых ключей не обнаружено. Имеющиеся на машине
  закрытые части относятся к сторонним утилитам и не связаны с управлением
  парком серверов:

  • ключ Proxmox — обслуживание гипервизора, в инвентаре не значится
  • ключ PacketSender — сетевой утилиты
  • ключ GreenShot — утилиты скриншотов
  • ключ ADB — отладки Android-устройств

────────────────────────────────────────────────────────────────────────
  6.2.2. Открытые части сторонних ключей (см. 6.3)



────────────────────────────────────────────────────────────────────────
  6.3. Открытые ключи сторонних пользователей

  Публичные части. Соответствующие закрытые части — у их владельцев.

abakumenko.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPp/Z/uI7tqCx48Gn1gQogeoW0kFROxjpm9Y7Rwcy+Xl work
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJti+Pf+2dSSLWUR/DiQ4aQRh/OKq4GVBfjzIwlXPhFz home
atarasov.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAII2I7bVlV2p7pjOhDPe8aq05k/H70w5R78ofMqXIHarZ
avasilev.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCXcVbz7tw/J/s+Q3lk3pMZrSvle174sCrb5ohJ5KtGslbBKas3PG6AWBwTTp3ofl3WkS1gHieOcKGRKWq7I2MQb762A6E6sNWJV9DnMXLXsPPGgsQe3S+gvpv9oB4YgUsBVO2iS1oZOcRYRZvuWES1UQZPg9YdNxoiq6pkBwAR2lRCySEsB3dywmNgNIOE/i2eeViyNdhmZ5kLpmc9TJDTGhrY/0u8cC1VBDAfFR35WtvmgQ9wAFNifeYDQfbMGU2q8oSUXHzuRk9oG6Da0L0yboQ7EEtgHmlcQZo3Yd4XN08RzlTYOwao4CYNMhHu9Yg7bpUhnYgFhybpSqZyR2Y3 amplifier-cult@thpd
avoitov.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILKRItj7e0SnBRlQ9xsgoyGIQGm3qfKQ71+Ub4TZxGZG avoitov
bitel.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDC2m4Agc0w1QglOGpUatRPm5DOj7nwMEBy9I4gODJt+NC/6+zNfAcXddxBMqtI5C/xIZNu8azOSOrGJjdAwFeeupbTOR37qHq2fQky687x2NtT+yJZV0e/xFXkCwWN7ommjIM5C50020IYhOdOkCUsZhjF+CyHaTW9m4exEN9OBODu87o4KEpdBbxNGlHtB+YGplZRlD9dFbFkHlW8/zeV9MFav7gUdVovZHEeNbsSvndp8Vl/iy0O+buC+Mbc92sxJRzL2CtdKBQgsZcymhg7OhcWKWWI0pY+VFjp2IhM3S8kZASq0JWF56dhcUlNeYk+i0hgsGB/KEGOGiCr377D user@stark
ezinovyev.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAEG0kFwvSeLkXG0wMsh7JR0rWikwwBPtiO1I+P/M3Ip ad\e.zinovyev@Admin
gmasich-test1.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC5rhiQLLftmGYekujhrjz1zmFqqo3CJ86el5B6jPSxEd3n5NobW3wXa37SoK3VnADG7PLeahFtfWoDFUawIBbecyAILEAVImEmO3jOhuswsqYZJYAVEpwTK2GiXT7VnALmRR3RufqJFRusN7fvhEPyZj8Zjjt4/0pgih7KOeFjuD3kYdkN8eyxxYlZN543ND7/jIgSLr7wjKJPvH8tDIDrHMui9ddWYxDuB2po5WbSsHXPaX+mJOtxHptxbtHEoDec3m7b7wBm6iL7Qqy2I4ErX5cffw3Bvj3yjBuDzcSkbvw5BAUQ6Bp//ru+VsPqrspiB+EORvzzE7if+Kvmkjv6AiCLLCckumroi/pjqJQd2u0bRB96EK0H7uXKKYc4V+UOqoCdgzMm76ut3k1IjrDcwk1UiRCzdixyoF/Q/Qhgp0EL/TpQ5NuzAPJlUGm1e2TpZ60/3pcXbxfCwiZ/OhKsHHFvUMUMCHEJfL7yLZNT80ijJ/KbHuOIa37OS0nPSjtgJvi0/eYNmbTyXKlzk+erI6e7e099TFUuIqfkwhwfx5Okq8KPxiyXho/3aLA/Jn6LHBydxx8AAQxsGF9wnSx9Kd+TyXN6X5qn07wOU3PdR679Xe+LpMoXpxDp/gEryl5fWltBOJcEOS+lFIU7cV6TQM7R/S7ypzNCu7iWsMXYhQ== gmasich@350pro.online
gmasich.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCav17UqgfRZWnNcYFQ7Zcs1+A9ZzNmmq6fBK07/Pj2/bhsflbgw50lK5pJpToS/+bDdUUr1tvvnl8kjewbALuUSCBaSRrDYB4kx2YLtw3KD1UM1OD7eIDFneyiLwMj/phKF4QECvr/gUj2OZ8vQPXdXfGUXLLcu8ZcBvqC37aooVwLvS7n3dQ4l+hlNC/vRO0jlaFq4Ndtx6tKMW7t+OrC05yY7sFmVzVxTsIdtYHxIlB/G1Cbe+TPYx3tv+7HAh4/LMgEsmHn+joKOD/MIM6o56w8XfmcEl9K8m1MPnWhj9V3g7Ph0l+XBg/eyBbFk6p7vOLCiapha6W3Hg/auD6p rsa-key-20220601
kirill.pub
ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA0fDmpVwkAC3hD0qaO/Vc/UcxUzoKR+7X3bdwGRQqnhDCHQIhb3gmohyREd6Sqn1Okywuc4UwVC5pg+JgEEYxUk/fby59FtYP9rA77NRe1utewmR3wusEyRl8Qaq9XnAv+vswb5htgllOv2KH+2oLCBrph7poriMMinVhFrAD8zhlQ8GX55aIrbSz14orHfOgmBmL/KRPAqMKCL41+qTHTlPzemn3AFP8cNmyDoeGOXRcL8EgaQ6jV9up9aXDxii/TrAfFWwXwZuZlQGG4DdWHARzI1kogZ6M7KRh4oox/iZhPjPibk/uU/5Cf6t1X3ZbOrj+9Wu3osTtkptJ3vvwbQ== kirill@kirill
mpeshkov.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4FbpC3yfpt3G6whFxKhAmik7ZZ92h+FHzIldPi4a5o+h7wHsT2rxkd7Fwz39498a3akUfnfuwCFtYR4ExTGQEUU/iQl8aHyF6WqezOvolLYGyQ3FJbclFlgN9og3A8XmRCzDPXFJTbejYCYvxTmFs8aox0CZs+FAmX5XiLockmwauEDU0c8DCbjkpKlvFFt8lvQzgYJ3JGzcabhhnhUtwD2rIZgsoM5Ex47KGMHms4vQ+nZEY/lrMj65BWfEdvHM8iHlOkWQTTE7h0bS9wWqJz069NdLEVRmLW6TzkdBLxCi+qZjVlutCWVch+2aHKAHh5wrRxwK2ndDHRfqBZ7bT mpeshkov
ousepov.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDKFgu1C5IR8h7YUSYz6Zww8ZYiOVbUKcqw0r7CrtHKLvyiuXpQVPpRU/hu1U77vZK8Ez3AyFrE/mo5OWCowg2AZmMp55QpmOeMWzvjbzGKA2l3wkXS5OUshQvPjcINpuqV639Zqi0b3jGqT9pOH+QEueghbVd6JRt9PKGzDyWtB+RbRVC1XQYSuUpGFYberjs0dci7C8obXqL3cbhX167N+SBtiITkr+qdY+hPMixmvTE0j8hlji7wOBDxCMG0b5THm00sYuuIf7gDZOEZhhABSMFRSr/y4jfQEyrcp3B0COqfbsmCOnTHOWRyrFqW1vtqmkqOIkMW+Sol/q7VPOK6/duYfXNNbJMGyTnugAPuNXR9S9juuU4ctTo+fIkr1VUxcXgzY9iJKGFZ39NtCP3jAIdYb4SxjBqiBECRZWW2i0mJBhI84WTQvhPTf9l7axA6uuHVRiDqWP4oGO3pSqFFlwcdWi7SjFHSg72hjI9mlqcUCPU5IEO6SM7RI04IIh0= uos@uos-S5500B
pkuzmin.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDBqc03ShlcBvTZGLvOBFsTvFbZWBRresKp/jdAAA/TuBZSJ1k4m0/DhwTsqnqf/2HU/HCbb07ze22C/4xYfJppLSSKN1+Up0PoZVupUvjPmLyNqgUqSB8f59fVAge4+n+KHU/fKjN9lH0WHiAQyeTgV2dcuWmrFWPBWgXP9waPGdqdTo+VxGnoEmLDAjNrFXpnLXb9+Z7oGFtmmB9TEnAiRYa5biLpKZIwY6z2m8Sj1b0v+AuFZu9ITchfbRo42oDdK6mb5SIIJ3kRMdQ63raJR9TA3ao/Fdb1bNAwD1caDhBLwlXu4IQ4vof0VwxsNGzoYW1KCaFmaUKHMcvCpwVSKbkHwhRRwPXbB2V9bATK6Zwr+3NYcMg31z9tonbxOPcS5YABEzQ1P/KTB97YAljqLPmsNFG3+kLPazzMVzLl5iyA+MdRD0Pn0STXWuM3VHNZwvn4Lgl2z/HVXsSPFHcZScUfqFtKYuW7GVNeU1UJkKAY2P8D1JY8GF+kBXoYtaM=
rtaktarov.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDc8aTAF6HB78/3Z2DGN6jNPdAnHBihFdjeqNLnfqDz6B1Rrdm3SnWaMDOcnT+voBoLlwlQEZJNfof0a8XdW6zAlUAsxWvvEDexNkDt98w25WwV7U1hzJ03TM8y+151Nri5E44C/BDBhUrasDa3pDq9WGO2pJ9W+Z7othNBna3X9CbLWUY8+9nUbPy/1A/zt4XPF4TW3pYaeeCnc6KWt75ZOyQHgP8FlSeI/Z9acBNsUKv+YKBSRxlJs8tEEdsfxa+rYJhGJO7naT4kdWPNz6okFUbG0wdANKX17uC+xJ5l6otN3wPY7NzGYg5ywbSehh/aEQPGQdjvI59zywGe1K+t rtaktarov
sgaregin.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC22uQS7LE7Y1lu35yXF9ijlK4hqVbkM7k/SInCarMF6Vjt6BjRzMg5SVTl1GCSistaXKTiiVg6jnYdB8tlIo9xo3AJC59VnbTZuugXTS/AxWtF8HuN0ctZsutNDrnWWBwpjPX/HiJew0+rs886ZZgiHN5fMRNyZmaTJ73cul3RFJlVcTxmzrx+72DmSdsoaIatXte00aolAxdIWXQJMSVnL55aYJQPaoPt9bX/A9ArF1IeJnQXPidBjzKPPFf5vW3PPj73jzqX0TgJcqy+mf/+Re7qtZQpcYxoudNRvel3GYUWSiMA6kSe1PczBG8Nz4HNvwIrYzDbGENPwxj0uNV3 pest@MacBook-Air-Pest.local
userobaba.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCjEu8WBnpM0dh9MAPktiI7dEgCxxNOaj10KYRorTYlKgfY8rx649bb2jPZKuheUfj0VrGq38j8AKivjJ5bgVdCtFMlKUAt6NAonZ/8UptOtitx91/GUKdb1nvrjdYGwvFj+xt9iSzS7wlpkTNspyLsl3GSNBm1biCZes2rwOPrntYhOjuBiNF3D8VGAttp2ZfRhO3QscVO7/8spPPjG8NFMHxvvVSaS6V03uY32gYpoUBPK39Oq6wOJwog+sn0o6Hpk3ZbJ+354As5pozE9FhrIQ6RGBq0gepFY19JcTfqelJkYtMeLZuzbfMBQJIEOlpOeAO5Mq92MA6VyM4RnCB4Ju7e8LMT/mHDv2uhGQAZHFrvwyTEgpOcXVw6yJ5TKTT9kVmm/bAOamLmXj1kNZm1xVaz3WLl1Jt1Steac1wnL0PtGBdBZoOVj5DkvxdOsSS22hL/wzLALU9IPl+2nR54XyAxZyagSYhs9A3GbebM4DXy5F5zJUbw/o8PxW2whjk= gdubuar@gdubuar-Lenovo
valeriy.pub
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDC2m4Agc0w1QglOGpUatRPm5DOj7nwMEBy9I4gODJt+NC/6+zNfAcXddxBMqtI5C/xIZNu8azOSOrGJjdAwFeeupbTOR37qHq2fQky687x2NtT+yJZV0e/xFXkCwWN7ommjIM5C50020IYhOdOkCUsZhjF+CyHaTW9m4exEN9OBODu87o4KEpdBbxNGlHtB+YGplZRlD9dFbFkHlW8/zeV9MFav7gUdVovZHEeNbsSvndp8Vl/iy0O+buC+Mbc92sxJRzL2CtdKBQgsZcymhg7OhcWKWWI0pY+VFjp2IhM3S8kZASq0JWF56dhcUlNeYk+i0hgsGB/KEGOGiCr377D user@stark

────────────────────────────────────────────────────────────────────────
  6.4. Назначение ключей по учётным записям

  Из анализа группы sudo следует: omicron-sudo даёт NOPASSWD ALL.
  Группа насчитывает 16 членов, включая 9–11 неиспользуемых учётных
  записей бывших сотрудников. Рекомендация — провести ревизию состава
  и убрать неактивные учётные записи.

  Внешние подрядчики с root-доступом: valeriy (вендор BGBilling),
  sgagegin (дополнительно docker), atarasov, avk. Требуется пересмотр.

════════════════════════════════════════════════════════════════════════

РАЗДЕЛ 7. СВОДКА ПРИОРИТЕТОВ

  КРИТИЧЕСКИЙ
   1. Резервные копии БД отсутствуют — восстанавливаться не из чего
   2. Анонимный Docker Registry — исходники и секреты в сети
   3. Открытый прокси + все СУБД доступны из сети
   4. Zabbix-core доступен извне — RCE на всех хостах с агентом
   5. Дампы БД ERP читаются обычным пользователем
   6. ActiveMQ CVE-2023-46604 на 5 хостах
   7. RDP (3389) в интернете — закрыть на файрволе, только VPN
   8. node5 вне сети 170+ дней — запас etcd исчерпан

  ВЫСОКИЙ
   9.  Группа omicron-sudo раздута, содержит неактивные учётные записи
  10. Права root у внешних подрядчиков
  11. Повышение привилегий через docker + ansible
  12. Открыты СУБД и админ-интерфейсы без аутентификации
  13. Host firewall практически не активен

  СРЕДНИЙ
  14. 20 хостов на снятых с поддержки ОС
  15. CVE-2024-6387 — требуется подтверждение установленных патчей
  16. Хост Windows 8.1 без обновлений безопасности

════════════════════════════════════════════════════════════════════════
  КОНЕЦ ОТЧЁТА
════════════════════════════════════════════════════════════════════════
