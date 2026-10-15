#!/bin/bash
#===============================================================================
# nslookup_audit.sh — актуализация пула адресов: файлы инвентарей + vCenter,
#                     проверка обратным DNS через контроллеры домена
#===============================================================================
# Шаг 1. Собирает пул IPv4-адресов из файлов РЕКУРСИВНО, включая адреса, которые
#        встречаются ВНУТРИ больших файлов (txt/md/json/html), а не только в
#        ansible_host=... Исходники открываются ТОЛЬКО НА ЧТЕНИЕ.
#
# Шаг 2. (опционально, --vcenter) Забирает из vCenter список виртуальных машин
#        через REST API vSphere 6.5+: имена ВМ + их IP + power_state + ОС.
#        ВСЕ IP из vCenter добавляются в общий пул — так находятся хосты, которых
#        нет ни в 0-all, ни в аудитах UG_Telecom.
#        У части ВМ guest.ip_address пустой (нет VMware Tools / ВМ выключена) —
#        тогда IP берётся из DNS: имя (сначала host_name, затем имя ВМ)
#        резолвится в A-запись через dc1/dc2. Не нашлось — попадает в отчёт
#        отдельным списком, а не молча теряется.
#
# Шаг 3. Для каждого адреса спрашивает PTR у двух контроллеров домена:
#          dc1 = 192.168.160.60
#          dc2 = 192.168.160.69
#        Адрес считается ДОСТУПНЫМ, если PTR вернул ХОТЯ БЫ ОДИН контроллер.
#        Если оба контроллера недоступны — адрес попадает в отдельный список
#        unknown (иначе «DC лежит» выглядел бы как «хост мёртв»).
#
# Шаг 4. Сводит всё в таблицу: ip | статус | имя из PTR | имя ВМ в vCenter |
#        ОС | питание | источник. Форматы: TSV, Markdown, HTML.
#
# Результат — новый каталог с меткой времени (старые прогоны не затираются):
#   <out>/<YYYYmmdd-HHMMSS>/all.txt            все адреса пула
#                          /available.txt        ip + имя: PTR есть на dc1/dc2
#                          /unavailable.txt      ip: PTR не найден ни на одном DC
#                          /unknown.txt          оба DC недоступны (если не пусто)
#                          /detail.tsv           ip, dc1, dc2, имя dc1, имя dc2
#                          /vcenter_vms.tsv      ВМ из vCenter (если подключались)
#                          /vcenter_hosts.tsv    ESXi-хосты из vCenter
#                          /vcenter_name2ip.tsv  имя ВМ → IP (резолв через DNS)
#                          /table.tsv            сводная таблица
#                          /report.md            сводка + три списка + таблица
#                          /report.html          то же в HTML
#   По умолчанию <out> = ./nslookup рядом со скриптом (переопределяется -o или OUT).
#   Источники по умолчанию — под /home/igor/projeck (переопределяется env PROJ).
#
# Кредены vCenter — только из окружения (в .env, который в .gitignore):
#   VCENTER_HOST=192.168.160.202     # .202 = vcenter.esxi.loc — рабочий vCenter 6.7.3
#                                    # .21  = vcsa.omicron.loc   — VCSA, но 443 закрыт
#                                    # .200 = dbnode1.esxi.loc  — БД, REST-API нет
#   VCENTER_USER=administrator@vsphere.local
#   VCENTER_PASS=...
#
# Использование:
#   ./nslookup_audit.sh                       файлы + PTR
#   ./nslookup_audit.sh --vcenter             то же + ВМ из vCenter (нужны кредены)
#   ./nslookup_audit.sh --vcenter --vcenter-debug   печатать HTTP-коды и сырые ответы
#   ./nslookup_audit.sh --pool                только собрать пул, без nslookup
#   ./nslookup_audit.sh -j 40 -t 2            40 потоков, таймаут nslookup 2с
#   ./nslookup_audit.sh -s 10.0.0.1,10.0.0.2  другие DNS-серверы вместо dc1/dc2
#   ./nslookup_audit.sh -c 10.0.0.5           другой vCenter
#   ./nslookup_audit.sh -o /tmp/nslookup       свой каталог для отчётов
#   ./nslookup_audit.sh /path/a /path/b       свои источники вместо дефолтных
#===============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Пути НЕ выводятся из расположения скрипта: копия живёт в /projeck/audit,
# а источники адресов лежат рядом с access-users. Всё переопределяется env-переменными.
PROJ="${PROJ:-/home/igor/projeck}"

# ── Источники по умолчанию (только чтение) ───────────────────────────────────
DEFAULT_SOURCES=(
    "$PROJ/access-users/available_hosts.txt"
    "$PROJ/access-users/inventory"
    "$PROJ/access-users-old/inventory"
    "$PROJ/UG_Telecom"
)

DNS_LIST="${DNS:-192.168.160.60 192.168.160.69}"   # dc1 dc2
JOBS="${JOBS:-20}"
NS_TIMEOUT=3
OUTBASE="${OUT:-$HERE/nslookup}"

VCENTER_HOST="${VCENTER_HOST:-192.168.160.202}"
VCENTER_USER="${VCENTER_USER:-}"
VCENTER_PASS="${VCENTER_PASS:-}"
VCENTER_TLS_VERIFY=0          # 1 = проверять сертификат (нужен CA-бандл в -k/--cacert)
VCENTER_CACERT=""
VCENTER_DEBUG="${VCENTER_DEBUG:-}"   # 1 = печатать HTTP-коды и сырые ответы vCenter

USE_VCENTER=auto              # auto | yes | no
POOL_ONLY=0
SOURCES=()

if [[ -t 1 ]]; then
    R=$'\033[0m'; B=$'\033[1m'; D=$'\033[2m'
    RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; BLU=$'\033[34m'; CYA=$'\033[36m'
else
    R=''; B=''; D=''; RED=''; GRN=''; YEL=''; BLU=''; CYA=''
fi
die()  { printf '%s%sОШИБКА:%s %s\n' "$RED" "$B" "$R" "$*" >&2; exit 1; }
ok()   { printf '%s  ✓ %s%s\n' "$GRN" "$*" "$R"; }
warn() { printf '%s  ! %s%s\n' "$YEL" "$*" "$R"; }
info() { printf '%s%s%s\n' "$BLU" "$*" "$R"; }

usage() {
    local end
    end=$(grep -n '^#====' "$0" | tail -1 | cut -d: -f1)
    [[ "$end" =~ ^[0-9]+$ ]] || end=$(wc -l < "$0")
    sed -n "2,${end}p" "$0" | sed 's/^#\{0,1\} \{0,1\}//'
    exit 0
}

command -v nslookup >/dev/null 2>&1 || die "nslookup не найден (нужен пакет dnsutils)"
command -v timeout   >/dev/null 2>&1 || die "timeout не найден (нужен coreutils)"

# ── Разбор аргументов ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pool)         POOL_ONLY=1; shift ;;
        --vcenter-debug) VCENTER_DEBUG=1; shift ;;
        --vcenter)      USE_VCENTER=yes; shift ;;
        --no-vcenter)   USE_VCENTER=no; shift ;;
        -c|--vcenter-host) VCENTER_HOST="${2:?нужен адрес vCenter}"; shift 2 ;;
        --vcenter-tls)  VCENTER_TLS_VERIFY=1; shift ;;
        --cacert)       VCENTER_CACERT="${2:?нужен путь к CA}"; shift 2 ;;
        -j|--jobs)      JOBS="${2:?нужно число потоков}"; shift 2 ;;
        -t|--timeout)   NS_TIMEOUT="${2:?нужны секунды}"; shift 2 ;;
        -s|--servers)   DNS_LIST="${2//,/ }"; shift 2 ;;
        -o|--out)       OUTBASE="${2:?нужен каталог}"; shift 2 ;;
        -h|--help)      usage ;;
        -*)             die "Неизвестный ключ: $1 (см. --help)" ;;
        *)              SOURCES+=("$1"); shift ;;
    esac
done
[[ ${#SOURCES[@]} -gt 0 ]] || SOURCES=("${DEFAULT_SOURCES[@]}")
[[ "$JOBS" =~ ^[0-9]+$ && "$JOBS" -gt 0 ]] || die "Некорректное число потоков: $JOBS"
[[ "$NS_TIMEOUT" =~ ^[0-9]+$ && "$NS_TIMEOUT" -gt 0 ]] || die "Некорректный таймаут: $NS_TIMEOUT"
[[ -n "$DNS_LIST" ]] || die "Не заданы DNS-серверы"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="$OUTBASE/$STAMP"
mkdir -p "$OUTDIR" || die "Не удалось создать $OUTDIR"

POOL="$OUTDIR/all.txt"
DETAIL="$OUTDIR/detail.tsv"
FILES_IPS="$OUTDIR/.ips-from-files"
VC_IPS="$OUTDIR/.ips-from-vcenter"
VC_TSV="$OUTDIR/vcenter_vms.tsv"
VC_HOSTS="$OUTDIR/vcenter_hosts.tsv"

info "══════════════════════════════════════════════════════════════"
info " Источники:"
for s in "${SOURCES[@]}"; do
    if [[ -e "$s" ]]; then
        printf '   %s+ %s\n' "$GRN" "$s"
    else
        printf '   %s- %s  %s(нет такого пути)%s\n' "$YEL" "$s" "$D" "$R"
    fi
done

# ── Шаг 1a. Адреса из файлов ──────────────────────────────────────────────────
RAW="$OUTDIR/.raw-ips"
: > "$RAW"
MISSING=0
for s in "${SOURCES[@]}"; do
    [[ -e "$s" ]] || { MISSING=$((MISSING + 1)); continue; }
    if [[ -d "$s" ]]; then
        grep -rhoaE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "$s" 2>/dev/null >> "$RAW"
    else
        grep -hoaE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "$s" 2>/dev/null >> "$RAW"
    fi
done
[[ $MISSING -eq 0 ]] || warn "пропущено источников: $MISSING"

# Валидация октетов + отсев мусора (0.x, 127.x, >=224 — служебные/мультикаст).
# Версии вида «2.4.0.0» из текстов пройдут как валидные — смотри отчёт.
awk -F. '
    NF != 4 { next }
    {
        ok = 1
        for (i = 1; i <= 4; i++) {
            if ($i !~ /^[0-9]{1,3}$/) { ok = 0; break }
            if ($i + 0 > 255)         { ok = 0; break }
            if ($i + 0 == 0)          { ok = 0; break }
        }
        if (!ok) next
        o1 = $1 + 0
        if (o1 == 127) next
        if (o1 >= 224) next
        print
    }
' "$RAW" > "$FILES_IPS"
rm -f "$RAW"

N_FILES=$(grep -cve '^[[:space:]]*$' "$FILES_IPS"); N_FILES="${N_FILES:-0}"
ok "адресов из файлов: $N_FILES"


# ── Шаг 1b. Виртуальные машины из vCenter ────────────────────────────────────
# auto: подключаемся, только если заданы креды. --vcenter: креды обязательны.
if [[ "$USE_VCENTER" == "yes" ]]; then
    command -v jq    >/dev/null 2>&1 || die "--vcenter требует jq (apt install jq)"
    command -v curl  >/dev/null 2>&1 || die "--vcenter требует curl"
    [[ -n "$VCENTER_USER" && -n "$VCENTER_PASS" ]] || die \
"креды vCenter не заданы. Задайте их в .env и подгрузите:
    VCENTER_HOST=192.168.160.202
    VCENTER_USER=administrator@vsphere.local
    VCENTER_PASS=...
    source .env && $0 --vcenter"
    USE_VCENTER=yes
elif [[ "$USE_VCENTER" == "auto" && -n "$VCENTER_USER" && -n "$VCENTER_PASS" ]]; then
    command -v jq >/dev/null 2>&1 && command -v curl >/dev/null 2>&1 && USE_VCENTER=yes
fi
[[ "$USE_VCENTER" == "yes" ]] || USE_VCENTER=no

# Молча пропускать vCenter нельзя: в прошлый прогон он тихо не отработал, и
# выглядело это как «не парсит», хотя скрипт даже не подключался.
VC_SKIP_REASON=""
if [[ "$USE_VCENTER" == "no" ]]; then
    if [[ -z "$VCENTER_USER" || -z "$VCENTER_PASS" ]]; then
        VC_SKIP_REASON="не заданы VCENTER_USER/VCENTER_PASS"
    else
        VC_SKIP_REASON="задан --no-vcenter"
    fi
fi
if [[ "$USE_VCENTER" == "no" && -n "$VC_SKIP_REASON" ]]; then
    warn "vCenter пропущен: $VC_SKIP_REASON"
    warn "чтобы включить: положить VCENTER_USER/VCENTER_PASS в .env рядом со скриптом"
    warn "                и запустить: source .env && $0 --vcenter"
fi

: > "$VC_TSV"
: > "$VC_HOSTS"
: > "$VC_IPS"
VC_OK=0
N_NOID=0; N_RESOLVED=0; N_STILL=0; N_VM=0; N_VCH=0; N_VC=0; N_ONLY=0

if [[ "$USE_VCENTER" == "yes" ]]; then
    info ""
    info " vCenter: $VCENTER_HOST как $VCENTER_USER"
    VC_BASE="https://$VCENTER_HOST"
    if [[ "$VCENTER_TLS_VERIFY" == "1" ]]; then
        if [[ -n "$VCENTER_CACERT" ]]; then VC_TLS="--cacert $VCENTER_CACERT"
        else die "--vcenter-tls требует --cacert /path/to/ca.pem"; fi
    else
        VC_TLS="-k"
    fi
    # ВАЖНО: опции curl держим СТРОКОЙ, а не массивом — массив нельзя экспортировать
    # в bash -c, а детали ВМ тянутся параллельно через xargs + bash -c.

    # ВАЖНО: нельзя брать просто jq '.value' — при 401 vCenter тоже отдаёт JSON
    # с полем value, где лежит текст ошибки, и это выглядит как session id.
    # Поэтому сначала смотрим HTTP-код, и только потом разбираем тело.
    # На vCenter 6.7 отвечают оба API: /rest (vAPI REST) и /api (vAPI).
    # Берём /rest, но если он не зарегистрирован (404) — пробуем /api.
    for API_PREFIX in /rest /api; do
    vc_resp=$(curl -s $VC_TLS -m 20 -u "$VCENTER_USER:$VCENTER_PASS" \
        -X POST -H 'Content-Type: application/json' \
        -w $'\n%{http_code}' \
        "$VC_BASE$API_PREFIX/com/vmware/cis/session" 2>/dev/null)
    vc_code=$(printf '%s' "$vc_resp" | tail -n1)
    vc_body=$(printf '%s' "$vc_resp" | sed '$d')
    [[ -n "$VCENTER_DEBUG" ]] && printf '%s[vcenter %s] HTTP %s: %s%s\n' "$D" "$API_PREFIX" "$vc_code" "${vc_body:0:200}" "$R"
    case "$vc_code" in
        200) vc_session=$(printf '%s' "$vc_body" | jq -r '.value // empty' 2>/dev/null)
             [[ -n "$vc_session" ]] && break ;;
        # 401 — креды неверны; /api тут не поможет, поэтому НЕ пробуем запасной API.
        401|403) vc_session=""; warn "vCenter $VCENTER_HOST: HTTP $vc_code — логин/пароль не приняты или нет прав"
                warn "проверьте VCENTER_USER (обычно administrator@vsphere.local) и VCENTER_PASS"
                break ;;
        400|404) vc_session=""
                if [[ "$API_PREFIX" == "/rest" ]]; then
                    warn "vCenter $VCENTER_HOST: HTTP $vc_code на /rest/com/vmware/cis/session — пробую /api"
                    continue
                fi
                warn "vCenter $VCENTER_HOST: HTTP $vc_code на /api — REST-API нет, это не vCenter"
                warn "проверено: .202 = vcenter.esxi.loc (vCenter), .21 = vcsa.omicron.loc (443 закрыт), .200 = dbnode1" ;;
        *)   vc_session=""; warn "vCenter $VCENTER_HOST: неожиданный HTTP $vc_code" ;;
    esac
    done
    if [[ -z "$vc_session" ]]; then
        [[ -n "${vc_session:-}" ]] || warn "сессия vCenter не получена — ВМ в прогон не попадут"
    else
        VC_HDR="vmware-api-session-id: $vc_session"
        vc_get() { curl -s $VC_TLS -m "${2:-30}" -H "$VC_HDR" "$VC_BASE$1"; }

        # ── список ВМ ────────────────────────────────────────────────────────
        : > "$OUTDIR/.vm-ids"
        # ВАЖНО: REST отдаёт {"value":[...]}. Нужен именно .value[]? —
        # с .[]? jq отдаст массив целиком и напечатает "[" и "vm-1," отдельными строками.
        vc_get "$API_PREFIX/vcenter/vm" 60 | jq -r '.value[]?' 2>/dev/null | sort -u > "$OUTDIR/.vm-ids"
        N_VM=$(grep -cve '^[[:space:]]*$' "$OUTDIR/.vm-ids"); N_VM="${N_VM:-0}"
        [[ "$N_VM" -gt 0 ]] || warn "сессия есть, но /rest/vcenter/vm вернул 0 ВМ — нет прав на чтение?"

        # Детали ВМ тянем параллельно — иначе сотня машин будет ходить минутами.
        vc_vm_one() {
            local vm="$1" d
            d=$(curl -s $VC_TLS -m 30 -H "$VC_HDR" \
                "$VC_BASE$API_PREFIX/vcenter/vm/$vm" 2>/dev/null) || return 0
            printf '%s\n' "$d" | jq -r --arg id "$vm" '[
        $id,
        (.name                        // ""),
        (.guest.ip_address            // .guest.ipAddress // ""),
        (.guest.host_name             // .guest.hostName  // ""),
        (.power_state                 // ""),
        (.guest.full_name.guest_os    // ""),
        ((.cpu_count                  // 0) | tostring),
        ((.memory_size_MiB            // 0) | tostring),
        ((.guest.ip_stack             // "") | tostring),
        "vcenter"
    ] | @tsv' 2>/dev/null
        }
        export -f vc_vm_one
        export VC_BASE VC_TLS VC_HDR API_PREFIX

        grep -v '^[[:space:]]*$' "$OUTDIR/.vm-ids" \
          | xargs -P "$JOBS" -I{} bash -c 'vc_vm_one "$1"' _ {} 2>/dev/null \
          | sort -t. -k3,3V > "$VC_TSV"
        rm -f "$OUTDIR/.vm-ids"

        # ── ВМ без IP: резолвим имя в IP через контроллеры домена ─────────────
        # В vCenter guest.ip_address часто пустой (нет VMware Tools, ВМ выключена
        # или IP не отдаётся гостевой ОС). Тогда берём имя — сначала host_name
        # (то, что видит ОС), затем имя самой ВМ — и спрашиваем A-запись у dc1/dc2.
        # В .vm-noid кладём ТОЛЬКО имя: дальше resolve_name получает "$1" целиком,
        # и если там останется "vm-id<TAB>имя", резолв не сработает никогда.
        awk -F'\t' '$3 == "" { n = ($4 != "" ? $4 : $2); if (n != "") print n }' "$VC_TSV" \
          | sort -u > "$OUTDIR/.vm-noid"
        N_NOID=$(grep -cve '^[[:space:]]*$' "$OUTDIR/.vm-noid"); N_NOID="${N_NOID:-0}"

        # A-запись: у nslookup строки Address идут и для самого сервера, поэтому
        # берём только Address, который идёт ПОСЛЕ строки Name:.
        resolve_name() {
            local n="$1" s out ip
            for s in $DNS_LIST; do
                out=$(timeout "$NS_TIMEOUT" nslookup "$n" "$s" 2>/dev/null)
                ip=$(printf '%s\n' "$out" | awk '
                    /^Name:/   { found = 1; next }
                    /^Address:/ {
                        if (found) { sub(/^Address:[ \t]*/, ""); print; exit }
                    }' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1)
                [[ -n "$ip" ]] && { printf '%s\n' "$ip"; return 0; }
            done
            return 1
        }
        export -f resolve_name
        export NS_TIMEOUT DNS_LIST

        if [[ "$N_NOID" -gt 0 ]]; then
            info ""
            info " ВМ без IP в vCenter: $N_NOID — резолвлю имена через dc1/dc2"
            : > "$OUTDIR/.name2ip"
            # exit 0 в конце: нерезолвившееся имя не должно ронять xargs кодом 123.
            xargs -d '\n' -P "$JOBS" -I{} bash -c \
                'r=$(resolve_name "$1"); if [ -n "$r" ]; then printf "%s\t%s\n" "$1" "$r"; fi; exit 0' _ {} \
              < "$OUTDIR/.vm-noid" 2>/dev/null | sort > "$OUTDIR/vcenter_name2ip.tsv"
            N_RESOLVED=$(grep -cve '^[[:space:]]*$' "$OUTDIR/vcenter_name2ip.tsv"); N_RESOLVED="${N_RESOLVED:-0}"
            N_STILL=$((N_NOID - N_RESOLVED)); [[ "$N_STILL" -lt 0 ]] && N_STILL=0
            ok "имен разрешено в IP: $N_RESOLVED, осталось без IP: $N_STILL"

            # Подставляем найденный IP в 3-ю колонку, помечая источник как dns.
            # OFS обязателен: присваивание $3 заставляет awk пересобрать $0,
            # и без OFS="\t" строка выйдет разделённая пробелами.
            awk -F'\t' -v OFS='\t' '
                NR == FNR { n2i[$1] = $2; next }
                {
                    if ($3 == "") {
                        if ($4 != "" && ($4 in n2i))      { $3 = n2i[$4]; $10 = "dns:" $4 }
                        else if ($2 != "" && ($2 in n2i)) { $3 = n2i[$2]; $10 = "dns:" $2 }
                    }
                    print
                }
            ' "$OUTDIR/vcenter_name2ip.tsv" "$VC_TSV" > "$VC_TSV.tmp" && mv "$VC_TSV.tmp" "$VC_TSV"
            rm -f "$OUTDIR/.vm-noid"
        fi

        # ── ESXi-хосты (для контекста) ───────────────────────────────────────
        vc_get "$API_PREFIX/vcenter/host" 30 2>/dev/null | jq -r '.value[]?' 2>/dev/null \
          | xargs -r -P "$JOBS" -I{} bash -c '
                d=$(curl -s $VC_TLS -m 30 -H "$VC_HDR" "$VC_BASE$API_PREFIX/vcenter/host/{}") || exit 0
                printf "%s\n" "$d" | jq -r "[
                    (.name // {}), (.connection_state // \"\"), (.power_state // \"\"),
                    (.config.lockdownMode // \"\"), ((.hardware.memorySize // 0) | tostring)
                ] | @tsv"' 2>/dev/null \
          | sort > "$VC_HOSTS"

        N_VCH=$(grep -cve '^[[:space:]]*$' "$VC_HOSTS"); N_VCH="${N_VCH:-0}"

        # Закрываем сессию — она живёт 30 минут, но закрывать надо.
        curl -s $VC_TLS -m 10 -H "$VC_HDR" -X DELETE \
            "$VC_BASE$API_PREFIX/com/vmware/cis/session" >/dev/null 2>&1

        # ── IP из vCenter ─────────────────────────────────────────────────────
        awk -F'\t' 'NF>=3 && $3 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {print $3}' "$VC_TSV" \
          | awk -F. '{ if ($1 != 0 && $1 != 127 && $1 < 224 && $2 <= 255 && $3 <= 255 && $4 <= 255) print }' \
          | sort -u -t. -k1,1n -k2,2n -k3,3n -k4,4n > "$VC_IPS"
        N_VC=$(grep -cve '^[[:space:]]*$' "$VC_IPS"); N_VC="${N_VC:-0}"

        VC_OK=1
        ok "vCenter: ВМ=$N_VM, ESXi-хостов=$N_VCH, адресов=$N_VC"
        # IP, которых не было в файлах, — это и есть ценность выгрузки
        # awk, а не comm: файлы отсортированы по-разному (числовой sort по точкам).
        awk 'NR == FNR { seen[$0] = 1; next } !($0 in seen)' "$FILES_IPS" "$VC_IPS" \
          > "$OUTDIR/.vcenter-only"
        N_ONLY=$(grep -cve '^[[:space:]]*$' "$OUTDIR/.vcenter-only"); N_ONLY="${N_ONLY:-0}"
        [[ "$N_ONLY" -gt 0 ]] && ok "из них НЕТ в инвентарях: $N_ONLY"
    fi
fi

# ── Шаг 1c. Общий пул ────────────────────────────────────────────────────────
{ cat "$FILES_IPS"; [[ "$VC_OK" == "1" ]] && cat "$VC_IPS"; } \
  | sort -u -t. -k1,1n -k2,2n -k3,3n -k4,4n > "$POOL"
TOTAL=$(grep -cve '^[[:space:]]*$' "$POOL"); TOTAL="${TOTAL:-0}"
ok "уникальных адресов в пуле: $TOTAL"

if [[ $POOL_ONLY -eq 1 ]]; then
    info "режим --pool: nslookup не выполнялся"
    info "список: $POOL"
    exit 0
fi

# ── Шаг 2. Reverse-DNS через контроллеры домена ──────────────────────────────
info ""
info " DNS-серверы: $(echo "$DNS_LIST" | tr ' ' ',')"
info " Потоков: $JOBS, таймаут: ${NS_TIMEOUT}s"

# Проверяем доступность DC заранее, чтобы не помечать 200 хостов «мёртвыми».
DC_DEAD=""
for srv in $DNS_LIST; do
    if timeout "$NS_TIMEOUT" nslookup -type=SOA omiplat.local "$srv" >/dev/null 2>&1 \
       || timeout "$NS_TIMEOUT" nslookup "$srv" "$srv" >/dev/null 2>&1; then
        printf '   %s+ %s отвечает%s\n' "$GRN" "$srv" "$R"
    else
        printf '   %s- %s не отвечает%s\n' "$YEL" "$srv" "$R"
        DC_DEAD="$DC_DEAD $srv"
    fi
done
if [[ -n "$DC_DEAD" ]]; then
    warn "часть контроллеров недоступна (нужен VPN/доступ в сеть 192.168.160.0/24):$DC_DEAD"
    warn "эти адреса попадут в unknown.txt, а не в unavailable.txt"
fi

# Рабочий процесс: ip -> ip<TAB>статус dc1<TAB>статус dc2<TAB>имя dc1<TAB>имя dc2
probe_ip() {
    local ip="$1"
    local -a st=() nm=()
    local s out n
    for s in $DNS_LIST; do
        out=$(timeout "$NS_TIMEOUT" nslookup "$ip" "$s" 2>&1)
        if printf '%s\n' "$out" | grep -qiE 'communications error|no servers could be reached|timed out'; then
            st+=("unreachable"); nm+=("")
            continue
        fi
        n=$(printf '%s\n' "$out" | sed -n 's/^.*name = //p' | paste -sd, -)
        if [[ -n "$n" ]]; then st+=("ptr"); nm+=("$n"); else st+=("none"); nm+=(""); fi
    done
    local l1="" l2="" n1="" n2=""
    [[ ${#st[@]} -ge 1 ]] && l1="${st[0]}"
    [[ ${#st[@]} -ge 2 ]] && l2="${st[1]}"
    [[ ${#nm[@]} -ge 1 ]] && n1="${nm[0]}"
    [[ ${#nm[@]} -ge 2 ]] && n2="${nm[1]}"
    printf '%s\t%s\t%s\t%s\t%s\n' "$ip" "$l1" "$l2" "$n1" "$n2"
}
export -f probe_ip
export NS_TIMEOUT DNS_LIST

info ""
printf ' %sПроверяю %s адресов (nslookup), это займёт до %s c...%s\n' \
    "$B" "$TOTAL" "$((TOTAL * NS_TIMEOUT / (JOBS > 0 ? JOBS : 1) + NS_TIMEOUT))" "$R"

grep -v '^[[:space:]]*$' "$POOL" \
  | xargs -P "$JOBS" -I{} bash -c 'probe_ip "$1"' _ {} 2>/dev/null \
  | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n > "$DETAIL"

# ── Повтор для «DC не ответил» ───────────────────────────────────────────────
# При 20 параллельных обращениях контроллеры начинают отбрасывать запросы
# (таймаут), и хосты с живым PTR попадают в unknown. Переспрашиваем их
# с меньшей параллельностью — обычно этого достаточно.
RETRY_JOBS=$(( JOBS > 4 ? JOBS / 4 : 1 ))
for attempt in 1 2; do
    UNKNOWN="$OUTDIR/.unknown.$attempt"
    awk -F'\t' '
        $2 != "ptr" && $3 != "ptr" && ($2 == "unreachable" || $3 == "unreachable") { print $1 }
    ' "$DETAIL" > "$UNKNOWN"
    RETRY_N=$(grep -cve '^[[:space:]]*$' "$UNKNOWN"); RETRY_N="${RETRY_N:-0}"
    [[ "$RETRY_N" -eq 0 ]] && break
    info "повтор $attempt: переспрашиваю $RETRY_N адресов (потоков $RETRY_JOBS)"
    grep -v '^[[:space:]]*$' "$UNKNOWN" \
      | xargs -P "$RETRY_JOBS" -I{} bash -c 'probe_ip "$1"' _ {} 2>/dev/null \
      | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n > "$DETAIL.retry"
    # подменяем строки, где повтор дал результат
    awk -F'\t' '
        NR == FNR { d[$1] = $0; next }
        $1 in d { print d[$1]; next }
        { print }
    ' "$DETAIL.retry" "$DETAIL" > "$DETAIL.new" && mv "$DETAIL.new" "$DETAIL"
    rm -f "$DETAIL.retry"
done

AVAIL="$OUTDIR/available.txt"
UNAVAIL="$OUTDIR/unavailable.txt"
UNKNOWN="$OUTDIR/unknown.txt"

# dc1 и dc2 обычно отдают одно и то же имя — не дублируем его в списке.
awk -F'\t' '
    $2 == "ptr" || $3 == "ptr" {
        names = $4
        if ($5 != "" && $5 != names) names = (names == "" ? "" : names ",") $5
        printf "%s\t%s\n", $1, names
    }
' "$DETAIL" > "$AVAIL"

awk -F'\t' '
    $2 != "ptr" && $3 != "ptr" && $2 != "unreachable" && $3 != "unreachable" { print $1 }
' "$DETAIL" > "$UNAVAIL"

awk -F'\t' '
    $2 != "ptr" && $3 != "ptr" && ($2 == "unreachable" || $3 == "unreachable") { print $1 }
' "$DETAIL" > "$UNKNOWN"

cnt() { local n; n=$(grep -cve '^[[:space:]]*$' "$1" 2>/dev/null); printf '%s' "${n:-0}"; }
N_ALL=$(cnt "$POOL"); N_AV=$(cnt "$AVAIL"); N_UN=$(cnt "$UNAVAIL"); N_UNK=$(cnt "$UNKNOWN")

# ── Шаг 3. Сводная таблица ───────────────────────────────────────────────────
# ip -> «имя ВМ, ОС, power» из vCenter (на один IP может приходиться несколько ВМ).
IP2VM="$OUTDIR/.ip2vm"
: > "$IP2VM"
if [[ "$VC_OK" == "1" ]]; then
    awk -F'\t' '
        NF >= 6 && $3 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {
            key = $3
            line = $2 "\t" $6 "\t" $5
            if (!(key in seen)) { order[++n] = key; seen[key] = line }
            else if (index(seen[key], line) == 0) { seen[key] = seen[key] "; " line }
        }
        END { for (i = 1; i <= n; i++) print order[i] "\t" seen[order[i]] }
    ' "$VC_TSV" | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n > "$IP2VM"
fi

# ip -> «из файлов / из vCenter / из обоих»
SRCMAP="$OUTDIR/.srcmap"
# ВАЖНО: без print в END массив src так и не попадёт в файл — колонка
# «источник» молча останется пустой (и скрипт подставит дефолт «файлы»).
awk -F'\t' -v OFS='\t' '
    NR == FNR { files[$1] = 1; next }
    { vc[$1] = 1 }
    END {
        for (i in files) src[i] = "файлы"
        for (i in vc)   src[i] = (i in src) ? "файлы+vcenter" : "vcenter"
        for (i in src)  print i, src[i]
    }
' "$FILES_IPS" "$VC_IPS" > "$SRCMAP"
[[ "$VC_OK" == "1" ]] || awk '{ print $1 "\tфайлы" }' "$FILES_IPS" > "$SRCMAP"

TABLE="$OUTDIR/table.tsv"
# Сводка строится одним awk по трём файлам, а не циклом в bash:
# IFS=$'\t' в `read` схлопывает пустые поля (таб — это IFS-пробел), и колонки
# съезжают влево. Здесь $1..$7 сохраняются всегда.
# ПОРЯДОК АРГУМЕНТОВ ВАЖЕН: awk читает файлы последовательно, поэтому справочники
# (IP2VM, SRCMAP) должны идти ПЕРЕД DETAIL — иначе для строк DETILL массивы
# ещё пусты и колонки vCenter/источник останутся пустыми.
printf 'ip\tстатус\tимя_dns\tвм_vcenter\tос\tпитание\tисточник\n' > "$TABLE"
awk -F'\t' '
    FILENAME == ARGV[1] { vm[$1] = $2; os[$1] = $3; pw[$1] = $4; next }
    FILENAME == ARGV[2] { src[$1] = $2; next }
    {
        ip = $1
        if ($2 == "ptr" || $3 == "ptr") {
            status = "доступен"; names = $4
            if ($5 != "" && $5 != names) names = (names == "" ? "" : names ",") $5
        } else if ($2 == "unreachable" || $3 == "unreachable") {
            status = "DC_недоступен"; names = ""
        } else {
            status = "нет_PTR"; names = ""
        }
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", \
            ip, status, names, vm[ip], os[ip], pw[ip], (ip in src ? src[ip] : "файлы")
    }
' "$IP2VM" "$SRCMAP" "$DETAIL" >> "$TABLE"

# ── Отчёт: три списка + сводка + таблица ─────────────────────────────────────
REPORT="$OUTDIR/report.md"
{
    printf '# Reverse-DNS актуализация пула адресов\n\n'
    printf -- '- **Дата:** %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
    printf -- '- **DNS-серверы:** %s (критерий: PTR есть на dc1 **или** dc2)\n' "$(echo "$DNS_LIST" | tr ' ' ',')"
    printf -- '- **Потоков/таймаут:** %s / %ss\n' "$JOBS" "$NS_TIMEOUT"
    if [[ "$VC_OK" == "1" ]]; then
        printf -- '- **vCenter:** %s как %s — ВМ %s, ESXi %s, адресов %s (из них уникальных для vCenter: %s)\n' \
            "$VCENTER_HOST" "$VCENTER_USER" "$N_VM" "$N_VCH" "$N_VC" "${N_ONLY:-0}"
        printf -- '- **ВМ без IP в vCenter:** %s → разрешено по имени через DNS: %s, осталось без IP: %s\n' \
            "$N_NOID" "$N_RESOLVED" "$N_STILL"
    else
        printf -- '- **vCenter:** не опрашивался (%s)\n' "${VC_SKIP_REASON:-выключен}"
    fi
    printf -- '- **Источники (только чтение, ничего не изменено):**\n'
    for s in "${SOURCES[@]}"; do printf '  - `%s`\n' "$s"; done

    printf '\n## Сводка\n\n'
    printf '| Список | Количество |\n|---|---:|\n'
    printf '| Всего адресов в пуле | %s |\n' "$N_ALL"
    printf '| Доступных (PTR есть) | %s |\n' "$N_AV"
    printf '| Недоступных (нет PTR) | %s |\n' "$N_UN"
    printf '| Не определено (DC лежат) | %s |\n' "$N_UNK"
    printf '| Из них только из vCenter | %s |\n' "${N_ONLY:-0}"

    printf '\n## 1. Все адреса (%s)\n\n```\n' "$N_ALL"
    cat "$POOL"

    printf '\n```\n\n## 2. Доступные — PTR есть на dc1/dc2 (%s)\n\n```\n' "$N_AV"
    cat "$AVAIL"

    printf '\n```\n\n## 3. Недоступные — PTR не найден (%s)\n\n```\n' "$N_UN"
    cat "$UNAVAIL"

    if [[ "$N_UNK" -gt 0 ]]; then
        printf '\n```\n\n## Не определено — контроллеры домена недоступны (%s)\n\n```\n' "$N_UNK"
        cat "$UNKNOWN"
    fi
    printf '\n```\n'

    if [[ "$N_RESOLVED" -gt 0 ]]; then
        printf '\n## Имя ВМ → IP (резолв через dc1/dc2, в vCenter IP не было)\n\n```\n'
        cat "$OUTDIR/vcenter_name2ip.tsv"
        printf '```\n'
    fi

    printf '\n## Сводная таблица (ip → DNS → vCenter)\n\n'
    printf '| IP | Статус | Имя DNS | ВМ в vCenter | ОС | Питание | Источник |\n'
    printf '|---|---|---|---|---|---|---|\n'
    awk -F'\t' 'NR > 1 {
        printf "| %s | %s | %s | %s | %s | %s | %s |\n", $1, $2, ($3 ? $3 : "-"), \
               ($4 ? $4 : "-"), ($5 ? $5 : "-"), ($6 ? $6 : "-"), ($7 ? $7 : "-")
    }' "$TABLE"

    printf '\n## Файлы\n\n'
    for f in "$POOL" "$AVAIL" "$UNAVAIL" "$DETAIL" "$TABLE"; do printf -- '- `%s`\n' "$f"; done
    [[ "$VC_OK" == "1" ]] && { printf -- '- `%s`\n' "$VC_TSV"; printf -- '- `%s`\n' "$VC_HOSTS"; }
    [[ -s "$OUTDIR/vcenter_name2ip.tsv" ]] && printf -- '- `%s`\n' "$OUTDIR/vcenter_name2ip.tsv"
    [[ "$N_UNK" -gt 0 ]] && printf -- '- `%s`\n' "$UNKNOWN"
    printf -- '- `%s/report.html`\n' "$OUTDIR"
} > "$REPORT"

# ── HTML-версия таблицы ──────────────────────────────────────────────────────
HTML="$OUTDIR/report.html"
{
    printf '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    printf '<title>Пул адресов %s</title><style>\n'
    printf 'body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#222;background:#fafafa}\n'
    printf 'h1{font-size:20px}h2{font-size:16px;margin-top:28px}\n'
    printf 'table{border-collapse:collapse;font-size:13px;background:#fff}\n'
    printf 'th,td{border:1px solid #ddd;padding:4px 8px;text-align:left;white-space:nowrap}\n'
    printf 'th{background:#eee;position:sticky;top:0}\n'
    printf 'tr.ok td:nth-child(2){color:#0a7d28;font-weight:600}\n'
    printf 'tr.bad td:nth-child(2){color:#c02626;font-weight:600}\n'
    printf 'tr.unk td:nth-child(2){color:#a06000;font-weight:600}\n'
    printf 'code{background:#eee;padding:1px 4px}\n</style></head><body>\n'
    printf '<h1>Пул адресов — %s</h1>\n' "$(date '+%Y-%m-%d %H:%M')"
    printf '<p>DNS: <code>%s</code>. vCenter: <code>%s</code>%s</p>\n' \
        "$(echo "$DNS_LIST" | tr ' ' ',')" \
        "$([[ "$VC_OK" == 1 ]] && echo "$VCENTER_HOST" || echo 'не опрашивался')" \
        "$([[ "$VC_OK" == 1 ]] && echo " (ВМ: $N_VM, ESXi: $N_VCH)" || echo '')"
    printf '<p>Всего <b>%s</b> · доступных <b>%s</b> · недоступных <b>%s</b> · не определено <b>%s</b></p>\n' \
        "$N_ALL" "$N_AV" "$N_UN" "$N_UNK"
    printf '<h2>Сводная таблица</h2>\n<table>\n<tr><th>IP</th><th>Статус</th><th>Имя DNS</th>'
    printf '<th>ВМ vCenter</th><th>ОС</th><th>Питание</th><th>Источник</th></tr>\n'
    awk -F'\t' 'NR > 1 {
        cls = ($2 == "доступен") ? "ok" : (($2 == "DC_недоступен") ? "unk" : "bad")
        printf "<tr class=\"%s\"><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n", \
               cls, $1, $2, ($3 ? $3 : "-"), ($4 ? $4 : "-"), ($5 ? $5 : "-"), \
               ($6 ? $6 : "-"), ($7 ? $7 : "-")
    }' "$TABLE"
    printf '</table>\n</body></html>\n'
} > "$HTML"

printf '\n'
ok "всего:      $N_ALL"
ok "доступных:  $N_AV"
warn "недоступных: $N_UN"
[[ "$N_UNK" -gt 0 ]] && warn "не определено: $N_UNK (контроллеры домена не отвечают)"
[[ "$VC_OK" == "1" ]] && ok "vCenter: ВМ $N_VM, из них уникальных адресов ${N_ONLY:-0}"
info ""
info "Отчёты:"
info "  $REPORT"
info "  $HTML"
info "  $TABLE"
exit 0