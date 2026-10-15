#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Аудит резервного копирования Veeam — главный лист «Матрица» в колонках из ТЗ,
плюс детальные листы по двум консолям.

Читает все папки VeeamDump_* рядом с собой.
"""
import csv, re, json, datetime, collections, pathlib
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE  = pathlib.Path(__file__).resolve().parent      # все файлы лежат рядом со скриптом
OLD   = BASE / "Матрица_и_план_проверки_бэкапов.xlsx"
OUT   = BASE / "Аудит_бэкапов_Veeam_2026-10-07.xlsx"
HOSTS = pathlib.Path("/home/igor/projeck/UG_Telecom/reports/hosts.json")
SRV = {"VeeamDump_omicron": ("Veeam #1 «omicron»", "192.168.160.14"),
       "VeeamDump_db":      ("Veeam #2 «db»",      "192.168.160.16")}
REF_MIN = datetime.datetime(2026, 10, 7, 6, 0)
FMT_DT = "%m/%d/%Y %H:%M:%S"
DFMT, DFMT_T = "DD.MM.YYYY", "DD.MM.YYYY HH:MM"
NF_GB, NF_INT, NF_PCT = '# ##0.0" ГБ"', "# ##0", "0%"

def rd(path, n):
    f = path / n
    if not f.exists(): return []
    with open(f, encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh))
def pdt(s):
    s = (s or "").strip()
    for f in (FMT_DT, "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(s, f)
        except (ValueError, TypeError): pass
    return None
def gb(x):
    try: return float(str(x).replace(",", "."))
    except Exception: return None
def today(d):
    if isinstance(d, datetime.datetime): return d.strftime("%d.%m.%Y")
    return "—" if not d else str(d)
def nas(vm): return bool(re.match(r"^[A-Za-z]:\\|^\\\\", str(vm or "")))
def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\.(local|loc|online|ru|com|360pro|flash-telecom|esxi|global)\b", "", s)
    return re.sub(r"\s+new\s*\d.*", "", re.sub(r"[^a-z0-9 ]", "", s)).strip()

PT_FULL = {"Full": "Полный (Full)", "Increment": "Инкремент (Increment)", "Snapshot": "Снапшот реплики"}
RES_FULL = {"Success": "Успех", "Warning": "Успех с предупреждениями", "Failed": "Ошибка", "None": "нет данных"}
STATE_FULL = {"Stopped": "Завершено штатно", "Running": "Выполняется"}
TYPE_FULL = {"Backup": "резервное копирование", "Replica": "репликация", "NasBackup": "копирование NAS-шары"}

def sched_ru(text):
    """«Ежедневно в » → «каждый день», «Ежемесячно день 1» → «раз в месяц, 1-го числа»."""
    t = re.sub(r"\s*в\s*$", "", (text or "").strip())
    t = t.replace("Ежедневно", "каждый день").replace("Ежемесячно день", "раз в месяц, ")
    def _day(m):
        n = int(m.group(1))
        word = "число" if n == 1 else "числа" if 2 <= n <= 4 else "числа"
        return f"{n}-е число" if n == 1 else f"{n}-го {word}" if n % 10 in (2,3,4) and n % 100 not in (12,13,14) else f"{n}-е {word}"
    t = re.sub(r"раз в месяц,\s*(\d+)", lambda m: "раз в месяц, " + _day(m), t)
    t = t.replace("Каждые ", "каждые ")
    t = re.sub(r"каждые (\d+)\s*(секунд|минут|часа|часов|дня|дней|недели|недель)", lambda m: f"каждые {m.group(1)} {m.group(2)}", t)
    return t or "не задано"

def job_kind(nm):
    n = str(nm)
    if n.startswith("DBnode"):        return "Базы данных биллинга"
    if n == "sv3 Services":          return "Сервисные виртуальные машины (23 ВМ)"
    if n == "sv3 Exchange":          return "Microsoft Exchange, 5 доменов"
    if n in ("1c",):                 return "1С предприятие, 14 объектов"
    if n in ("CC",):                 return "Телефония и колл-центры, 10 объектов"
    if n in ("AD",):                 return "Active Directory, 7 доменов"
    if n in ("bg-core",):            return "Биллинг-ядра BGBilling, 5 нод"
    if n in ("bg-radius",):          return "RADIUS-серверы, 5 нод"
    if n in ("bg-proxysql",):        return "ProxySQL, 5 нод"
    if n in ("Access",):             return "Доступ и VPN: msVPN, NPS, MFA, OPNsense, WireGuard"
    if n == "TacacsEveryday":        return "TACACS+ (аутентификация администраторов)"
    if n == "ReplicaWG":             return "WireGuard (репликация)"
    if n in ("Monitoring",):         return "Мониторинг и сеть: Ansible, NetBox, oms, zabbix, SV1"
    if n.startswith("Share"):        return "Сетевая файловая шара (NAS)"
    if n.lower().startswith("k3"):   return "Kubernetes K3s, кластер"
    if n in ("sv3 BackConf", "backconf"): return "Резервные копии конфигов оборудования"
    if n.lower().startswith("netbox"): return "Система документирования сети NetBox"
    if n.startswith("ex"):           return "Microsoft Exchange (Flash)"
    if n == "singleopnsense":        return "Межсетевой экран OPNsense (дубль задания)"
    if n == "test":                  return "Тестовое задание для SQL Server"
    return "Прочее"
def src_kind(job_type, objs):
    if job_type == "NasBackup": return "Файлы на сетевой шаре (не виртуальные машины)"
    if job_type == "Replica":   return "Виртуальная машина, копия на другой узел"
    return "Виртуальные машины в VMware vSphere (vCenter 192.168.160.202)"
def vm_kind(vm):
    v = str(vm)
    if nas(v):                      return "Сетевая файловая шара"
    if v.startswith("db-"):         return "Сервер базы данных биллинга"
    if v.startswith("Active Directory") or v.startswith("AD("): return "Контроллер домена AD"
    if v.startswith("CALLCENTER") or v in ("call-center", "FOP2"): return "Телефония / колл-центр"
    if "Ex2-flash" in v or v.startswith("Ex1-") or v.startswith("Exchange"): return "Сервер Exchange"
    if v.startswith("proxysql"):    return "Прокси базы данных (ProxySQL)"
    if v.startswith("bg-"):         return "Ядро биллинга BGBilling"
    if v.startswith("vpn.") or v in ("wgAll", "WireGuard"): return "VPN-шлюз"
    if "BackupConf" in v or v == "TrueConf": return "Хранилище резервных конфигов"
    if "K3S" in v or "k3s" in v:    return "Узел Kubernetes"
    if "1CSERVER" in v:             return "Сервер 1С"
    if "Flussonic" in v:            return "Видеосервер (Flussonic)"
    if v in ("msVPN2", "MSVPN3", "MSVPN", "NPS", "SCUD", "MultiFactorRA"): return "Доступ / аутентификация"
    if v == "OPNSense":             return "Межсетевой экран"
    if v == "TACACS":               return "TACACS+"
    if v == "Ansible":              return "Сервер автоматизации"
    if v == "SV1":                  return "Docker-хост (SV1)"
    if v in ("gitlab.omicron",):    return "GitLab (репозитории кода)"
    if "vault" in v.lower():        return "Хранилище секретов Vault"
    return "Виртуальная машина"
def err_class(e):
    if "unavailable" in e:              return "ВМ недоступна — пропущена"
    if "not enough space" in e:         return "Нет свободного места на диске"
    if "Job finished with error" in e:  return "Задание завершено с ошибкой"
    if "could not be performed" in e:   return "Ошибка передачи данных (RPC)"
    if "Failed to process method" in e: return "Ошибка гостевого агента"
    if "Failed to pre-process" in e:    return "Ошибка подготовки задания"
    return "Прочая ошибка"

# ============================================================ разбор консоли
def analyze(dump):
    label, ip = SRV.get(dump.name, (dump.name, ""))
    servers = rd(dump, "01-Servers.csv"); lic = rd(dump, "02-License.csv")
    jobs = rd(dump, "03-Jobs.csv"); repos = rd(dump, "04-Repositories.csv")
    proxies = rd(dump, "05-Proxies.csv"); sessions = rd(dump, "06-Sessions.csv")
    rps = rd(dump, "07-RestorePoints.csv"); jstats = rd(dump, "08-JobStats.csv")
    errors = rd(dump, "10-FailedErrors.csv"); disks = rd(dump, "11-Disks.csv")
    host = next((s["Name"] for s in servers if s["Type"] == "Local"), label)
    ref = max([pdt(r["Время"]) for r in sessions] + [REF_MIN])

    job_of = {}
    for j in jobs:
        for o in re.split(r"[;,]", j["Что бэкапит"] or ""):
            o = o.strip()
            if o: job_of[o] = j["Задание"]
    rp_by_vm = collections.defaultdict(list)
    for r in rps: rp_by_vm[r["ВМ / объект"]].append(r)
    for v in rp_by_vm.values(): v.sort(key=lambda r: pdt(r["Время создания"]))
    for vm in list(rp_by_vm) + list(job_of):
        if re.match(r"db-\w+-node2$", vm): job_of[vm] = "DBnode2"
    s_by_job = collections.defaultdict(list)
    for r in sessions: s_by_job[r["Задание"]].append(r)
    for v in s_by_job.values(): v.sort(key=lambda r: pdt(r["Время"]))
    stats = {r["Задание"]: r for r in jstats}

    REPO_BY_NAME = {"AD": "AD → G:\\Backups", "CC": "CC → F:\\Backups", "1c": "1c → E:\\Backups",
                    "Share": "Share → H:\\Backups", "Access": "Access → V:\\Backups",
                    "k3s": "k3s → K:\\Backups  ⚠ ДИСК ЗАПОЛНЕН НА 100%", "Monitoring": "Monitoring → Q:\\Backups",
                    "sv3": "sv3 → G:\\Backups", "sv3 BackConf": "sv3 → G:\\Backups",
                    "netboxv2": "sv3 → G:\\Backups", "sv3 Exchange": "sv3 exchange → H:\\Backups",
                    "K3S": "sv3 → G:\\Backups (предположительно)", "Share main": "NAS-бэкап шары E:\\"}
    repo_by_path = {}
    for r in errors:
        for m in re.findall(r"([A-Za-z]:\\Backups\\[^\\\"]+?)[\\\.:]", r["Ошибка"]):
            repo_by_path[r["Задание"]] = ("sv3 → G:\\Backups" if m.lower().startswith("g:") else m)

    # фактическое время старта по последним сессиям задания (часы запуска в данных)
    fact_times = {}; fact_freq = {}
    _by_job = collections.defaultdict(list)
    for r in sessions:
        t0 = pdt(r["Время"])
        if t0: _by_job[r["Задание"]].append(t0)
    for nm_, lst in _by_job.items():
        lst.sort(reverse=True)
        fact_times[nm_] = sorted({t0.strftime("%H:%M") for t0 in lst[:10]})
        days_ = sorted({t0.date() for t0 in lst[:12]}, reverse=True)
        if len(days_) >= 3:
            gaps = [(days_[i] - days_[i+1]).days for i in range(len(days_) - 1)]
            g = min(gaps) if gaps else None
            freq_txt = ("ежедневно" if g == 1 else "через день" if g == 2 else
                        "еженедельно" if g in (6, 7, 8) else
                        f"раз в {g} дн." if g and g < 20 else
                        "примерно раз в месяц" if g and 25 <= g <= 40 else "нерегулярно")
        else:
            freq_txt = "запусков слишком мало для оценки"
        fact_freq[nm_] = (freq_txt, days_)

    # карта «объект → какие задания его копируют» (из самого списка заданий)
    jobs_of_obj = collections.defaultdict(list)
    for _j in jobs:
        for _o in re.split(r"[;,]", _j["Что бэкапит"] or ""):
            _o = _o.strip()
            if _o: jobs_of_obj[_o].append(_j["Задание"])

    # последние ошибки по заданиям (для колонки «Куда пишется» и «Комментарий»)
    err_by_job = collections.defaultdict(list)
    for e in errors:
        if e["Ошибка"] and "Job finished with error" not in e["Ошибка"]:
            err_by_job[e["Задание"]].append(e)
    for k in err_by_job: err_by_job[k].sort(key=lambda r: pdt(r["Время"]) or datetime.datetime.min, reverse=True)

    jobrows = []
    for j in jobs:
        nm = j["Задание"]; st = stats.get(nm, {})
        ss = s_by_job.get(nm, []); last = ss[-1] if ss else None
        n_all = int(st.get("Всего сессий") or 0); n_ok = int(st.get("Успешно") or 0)
        n_warn = int(st.get("Предупрежд.") or 0); n_err = int(st.get("Ошибок") or 0)
        days = (ref - pdt(last["Время"])).days if last else None
        objs = [o.strip() for o in re.split(r"[;,]", j["Что бэкапит"] or "") if o.strip()]
        pts = [(o, rp_by_vm.get(o, [])) for o in objs]
        npts = sum(len(p[1]) for p in pts)
        nfull = sum(sum(1 for x in p[1] if x["Тип"] == "Full") for p in pts)
        nincr = npts - nfull
        rep = repo_by_path.get(nm) or REPO_BY_NAME.get(nm, "не определён в выгрузке")
        ok = n_ok / n_all if n_all else 0
        # статус задания
        if j["Включено"] == "False":   st_txt, lvl = "НЕ РАБОТАЕТ: задание выключено вручную", 3
        elif n_all == 0:                st_txt, lvl = "НЕ РАБОТАЕТ: ни одного запуска за всю историю", 3
        elif ok < 0.35:                 st_txt, lvl = f"НЕ РАБОТАЕТ: успех только {ok:.0%}", 3
        elif ok < 0.75:                 st_txt, lvl = f"НЕСТАБИЛЬНО: успех {ok:.0%}", 2
        else:                           st_txt, lvl = f"РАБОТАЕТ: успех {ok:.0%}", 0
        if days is not None and days > 30 and lvl < 2:
            st_txt, lvl = f"ПРОСТОЙ: нет запусков {days} дн.", 3
        # хранение
        ret = int(j["Хранение (дней)"] or 0)
        plural = lambda n, a, b, c: f"{n} {a if n%10==1 and n%100!=11 else b if 2<=n%10<=4 and not 12<=n%100<=14 else c}"
        fresh = max((p[1][-1] for p in pts if p[1]), key=lambda r: pdt(r["Время создания"]), default=None)
        freshd = (ref - pdt(fresh["Время создания"])).days if fresh else None
        if nas(objs[0]) if objs else False:
            keep_txt = f"в репозитории точки восстановления не создаются — задание копирует файлы"
        elif npts:
            keep_txt = (f"в репозитории {plural(npts,'точка','точки','точек')}: "
                        f"{plural(nfull,'полный','полных','полных')} + {plural(nincr,'инкремент','инкремента','инкрементов')}"
                        + (f". Свежая точка: {today(pdt(fresh['Время создания']))} ({freshd} дн. назад)"
                           if fresh else ". Свежей точки нет"))
        else:
            keep_txt = "в репозитории точек восстановления нет ни одной — копий не создано"
        lastfull = max((p for p in pts if any(x["Тип"] == "Full" for x in p[1])), key=lambda p: pdt(p[1][-1]["Время создания"]), default=None)
        lf_txt = ""
        if lastfull and npts:
            lfd = (ref - pdt(lastfull[1][-1]["Время создания"])).days
            lf_txt = f" Последний полный бэкап: {today(pdt(lastfull[1][-1]['Время создания']))} ({lfd} дн. назад)."
        objs_txt = ", ".join(objs) if len(objs) <= 6 else ", ".join(objs[:6]) + f" и ещё {len(objs)-6}"
        # --- кто ещё копирует эти объекты (важно для «дублей»)
        alt_jobs = sorted({a2 for o in objs for a2 in jobs_of_obj.get(o, []) if a2 != nm})
        covered_elsewhere = bool(alt_jobs) and npts == 0
        # --- тип бэкапа (наглядно) ---
        if nas(objs[0]) if objs else False:
            btype = "КОПИРОВАНИЕ ФАЙЛОВ (NAS-шара) — точек восстановления ВМ не создаёт"
        elif j["Тип"] == "Replica":
            btype = "РЕПЛИКАЦИЯ — постоянная копия на другой узел, это не резервная копия"
        elif nfull and nincr:
            btype = (f"ПОЛНЫЙ (Full) + ИНКРЕМЕНТ (Increment) — "
                     f"{nfull} {('полный' if nfull == 1 else 'полных')}, {nincr} "
                     f"{('инкремент' if nincr == 1 else 'инкремента' if nincr in (2,3,4) else 'инкрементов')}")
        elif nfull == 1:
            btype = "ПОЛНЫЙ (Full) один, инкрементов нет — дальше растить цепочку нечем"
        elif nincr and not nfull:
            btype = f"ТОЛЬКО ИНКРЕМЕНТЫ ({nincr} шт.) — ПОЛНОГО БЭКАПА НЕТ, объект невосстановим"
        elif covered_elsewhere:
            btype = ("ЭТО ЗАДАНИЕ КОПИЙ НЕ СОЗДАЛО. Объект копируется другим заданием: " + ", ".join(alt_jobs))
        else:
            btype = "НЕТ ТОЧЕК ВООБЩЕ — копий нет"
        # --- последние копии (3 последние точки по всем объектам задания) ---
        allp = sorted((x for o in objs for x in rp_by_vm.get(o, [])), key=lambda r: pdt(r["Время создания"]), reverse=True)
        last3 = "; ".join(f"{PT_FULL.get(x['Тип'], x['Тип'])} {pdt(x['Время создания']).strftime('%d.%m.%Y %H:%M')}"
                          f" ({x['ВМ / объект']})" for x in allp[:3]) if allp else "точек в репозитории нет"
        # --- последняя ошибка ---
        le = err_by_job.get(nm, [])
        last_err = (f"{pdt(le[0]['Время']).strftime('%d.%m.%Y %H:%M')}: {le[0]['Ошибка'][:150]}"
                    if le else "ошибок в логах нет")
        n_err_events = len(le)
        jobrows.append(dict(
            srv=label, ip=ip, job=nm, kind=job_kind(nm), jtype=TYPE_FULL.get(j["Тип"], j["Тип"]),
            on="да" if j["Включено"] == "True" else "НЕТ (выключено)",
            sched=sched_ru(j["Расписание"]), sched_raw=(j["Расписание"] or "").strip(),
            objs=objs, n_objs=int(j["Объектов"] or 0), n_all=n_all, n_ok=n_ok, ok=ok,
            n_warn=n_warn, n_err=n_err, npts=npts, nfull=nfull, nincr=nincr,
            last=pdt(last["Время"]) if last else None, days=days,
            dur=round(float(last["Длит. (мин)"])) if last else None,
            res=RES_FULL.get(j["Последний результат"], j["Последний результат"]),
            repo=rep, keep=keep_txt + lf_txt, ret=ret, status=st_txt, lvl=lvl, objs_txt=objs_txt,
            fact_times=fact_times.get(nm, []), sched_time=(j.get("Время запуска") or "").strip(),
            fact_freq=fact_freq.get(nm, ("запусков не было", [])),
            src=src_kind(j["Тип"], objs), btype=btype, last3=last3, last_err=last_err,
            n_err_events=n_err_events, alt_jobs=alt_jobs, covered_elsewhere=covered_elsewhere))

    # задание DBnode2 — есть в сессиях, но отсутствует в конфигурации
    ss = s_by_job.get("DBnode2", [])
    if ss and not any(j["job"] == "DBnode2" for j in jobrows):
        last = ss[-1]; n_err = sum(1 for s in ss if RES_FULL.get(s["Результат"]) != "Успех")
        objs = [f"db-{d}-node2" for d in ("flash", "omiplat", "rocket", "rtc", "utk")]
        pts = [(o, rp_by_vm.get(o, [])) for o in objs]
        jobrows.append(dict(
            srv=label, ip=ip, job="DBnode2", kind="Базы данных биллинга, ноды node2",
            jtype="резервное копирование", on="НЕТ (задания нет в консоли)", sched="неизвестно", sched_raw="",
            objs=objs, n_objs=5, n_all=len(ss), n_ok=0, ok=0.0, n_warn=0, n_err=n_err,
            npts=sum(len(p[1]) for p in pts), nfull=sum(len(p[1]) for p in pts), nincr=0,
            last=pdt(last["Время"]), days=(ref - pdt(last["Время"])).days,
            dur=round(float(last["Длит. (мин)"])), res=RES_FULL.get(last["Результат"]),
            repo="не определён в выгрузке",
            keep="хранение 14 дн.; последние точки 27.06.2026 — 101 день без копии, полных бэкапов нет свежих",
            ret=14, status="НЕ РАБОТАЕТ: задание отсутствует в консоли, все запуски с ошибкой", lvl=3,
            objs_txt=", ".join(objs), src="Виртуальные машины в VMware vSphere",
            btype="ПОСЛЕДНИЕ ТОЧКИ ОТ 27.06.2026 (101 ДН. НАЗАД), СВЕЖЕГО ПОЛНОГО БЭКАПА НЕТ",
            last3="; ".join(f"{PT_FULL.get(x['Тип'], x['Тип'])} {pdt(x['Время создания']).strftime('%d.%m.%Y %H:%M')}"
                            f" ({x['ВМ / объект']})" for x in sorted((x for o in objs for x in rp_by_vm.get(o, [])),
                            key=lambda r: pdt(r["Время создания"]), reverse=True)[:3]),
            last_err=f"{last['Время']}: задание отсутствует в конфигурации консоли, сессия падает за 0,2 мин",
            n_err_events=len(ss), alt_jobs=[], covered_elsewhere=False,
            fact_times=fact_times.get("DBnode2", []), sched_time="",
            fact_freq=fact_freq.get("DBnode2", ("запусков не было", []))))
    jobrows.sort(key=lambda r: (-r["lvl"], r["job"]))

    coverage = []
    for vm, pts in rp_by_vm.items():
        lastp = pts[-1]; dlast = (ref - pdt(lastp["Время создания"])).days
        fulls = [p for p in pts if p["Тип"] == "Full"]
        dfull = (ref - pdt(fulls[-1]["Время создания"])).days if fulls else None
        if nas(vm):      vd, lvl = "Не применимо: копирование файлов, без точек", 0
        elif not pts:    vd, lvl = "НЕ ЗАЩИЩЁН: точек нет", 3
        elif dlast > 30: vd, lvl = f"ПРОСТОЙ: нет копии {dlast} дн.", 3
        elif dlast > 14: vd, lvl = f"РИСК: нет копии {dlast} дн.", 2
        elif dlast > 7:  vd, lvl = f"Слабо: нет копии {dlast} дн.", 1
        else:            vd, lvl = "Защищён: копия свежая", 0
        coverage.append([label, vm, vm_kind(vm), job_of.get(vm, "НЕ ВХОДИТ НИ В ОДНО ЗАДАНИЕ"),
                         len(pts), len(fulls), len(pts) - len(fulls), PT_FULL.get(lastp["Тип"], lastp["Тип"]),
                         pdt(lastp["Время создания"]), dlast,
                         pdt(fulls[-1]["Время создания"]) if fulls else None, dfull, vd, lvl])
    for vm, j in job_of.items():
        if vm not in rp_by_vm:
            vd, lvl = ("Не применимо: копирование файлов, без точек", 0) if nas(vm) else ("НЕ ЗАЩИЩЁН: точек нет", 3)
            coverage.append([label, vm, vm_kind(vm), j, 0, 0, 0, "—", None, None, None, None, vd, lvl])

    idle = []
    for r in jobrows:
        if r["lvl"] >= 2:
            idle.append([label, "Задание", r["job"], r["kind"], r["repo"], r["last"], r["days"], r["status"],
                         f"успешных запусков {r['n_ok']} из {r['n_all']}" if r["n_all"] else "запусков не было ни разу"])
    for c in coverage:
        if c[13] >= 2 and not nas(c[1]):
            idle.append([label, "Объект", c[1], c[2], c[3], c[8], c[9], c[12],
                         "точек восстановления нет ни одной" if c[4] == 0 else
                         f"последняя точка {today(c[8])}, дней назад: {c[9]}"])
    idle.sort(key=lambda r: (r[0], r[1], str(r[5])))

    REPO_NOTE = {("omicron", "D:\\Backup"): "Default Backup Repository — к какому заданию привязан, из выгрузки не читается",
                 ("omicron", "G:\\Backups"): "репозиторий sv3 — сюда пишут sv3 Services, sv3 BackConf, netboxv2 (подтверждено путями в ошибках)",
                 ("omicron", "H:\\Backups"): "репозиторий sv3 exchange — привязка подтверждена только по имени репозитория",
                 ("db", "C:\\Backup"): "Default Backup Repository, задания к нему не привязаны",
                 ("db", "G:\\Backups"): "репозиторий AD — сюда пишет задание AD (7 доменов)",
                 ("db", "E:\\Backups"): "репозиторий 1c — задание 1c (14 объектов)",
                 ("db", "F:\\Backups"): "репозиторий CC — задание CC (колл-центры)",
                 ("db", "H:\\Backups"): "репозиторий Share — задание Share (NAS-шара E:)",
                 ("db", "V:\\Backups"): "репозиторий Access — задание Access (VPN и аутентификация)",
                 ("db", "Q:\\Backups"): "репозиторий Monitoring — задание Monitoring",
                 ("db", "K:\\Backups"): "репозиторий k3s — ДИСК ЗАПОЛНЕН НА 100%, задание k3s выключено вручную"}
    repo_rows = []
    for r in repos:
        vol, free = gb(r["Объём (ГБ)"]), gb(r["Свободно (ГБ)"])
        pf = free / vol if vol else None
        repo_rows.append([label, r["Репозиторий"], "Локальная папка на сервере Veeam", r["Путь"],
                          vol, (vol - free) if vol and free is not None else None, free, pf,
                          "ЗАПОЛНЕН" if pf is not None and pf < .15 else ("РИСК" if pf is not None and pf < .25 else "норма"),
                          REPO_NOTE.get(("db" if "db" in label else "omicron", r["Путь"]), "")])
    disk_rows = []
    for d in disks:
        tot, free = gb(d["Всего ГБ"]), gb(d["Свободно ГБ"])
        pf = free / tot if tot else None
        disk_rows.append([label, d["Диск"], gb(d["Занято ГБ"]), free, tot, pf,
                          ("КРИТИЧНО: свободно меньше 15%" if pf < .15 else
                           "РИСК: свободно меньше 25%" if pf < .25 else "норма"),
                          3 if pf < .15 else (2 if pf < .25 else 0)])
    ERR_NOTE = {"ВМ недоступна — пропущена": "ВМ не отвечает хосту — копия не создаётся вообще",
                "Нет свободного места на диске": "диск заполнен — следствие нехватки места в репозитории",
                "Задание завершено с ошибкой": "сводная запись Veeam о падении задания",
                "Ошибка передачи данных (RPC)": "ошибка передачи данных в репозиторий",
                "Ошибка гостевого агента": "ошибка агента в гостевой ОС при обработке диска",
                "Ошибка подготовки задания": "задание не дошло до стадии копирования"}
    errsum = [[label, j, k, c, ERR_NOTE.get(k, "")]
              for (j, k), c in sorted(collections.Counter((r["Задание"], err_class(r["Ошибка"])) for r in errors).items(),
                                      key=lambda x: -x[1])]
    return dict(label=label, ip=ip, host=host, ref=ref, dump=dump.name, servers=servers, license=lic,
                proxies=proxies, jobs=jobrows, coverage=coverage, idle=idle, repos=repo_rows, disks=disk_rows,
                errsum=errsum, sessions=sessions, rps=rps, errors=errors,
                totals={k: sum(int(r.get(key) or 0) for r in jstats) for k, key in
                        (("all", "Всего сессий"), ("ok", "Успешно"), ("warn", "Предупрежд."), ("err", "Ошибок"))})

# ============================================================ сборка
dumps = sorted(p for p in BASE.glob("VeeamDump_*") if p.is_dir())
A = [analyze(p) for p in dumps]
REF = max(a["ref"] for a in A)
def col(k): return [r for a in A for r in a[k]]
coverage, idle, repo_rows, disk_rows = col("coverage"), col("idle"), col("repos"), col("disks")
errsum, sessions, rps, errors = col("errsum"), col("sessions"), col("rps"), col("errors")
jobrows = col("jobs")
T = {k: sum(a["totals"][k] for a in A) for k in ("all", "ok", "warn", "err")}

# ---- сверка между консолями
idx = collections.defaultdict(list)
for c in coverage:
    if len(norm(c[1])) >= 4: idx[norm(c[1])].append(c)
allvms = sorted({c[1] for c in coverage})
both, only = [], []
for vm in allvms:
    rec = idx.get(norm(vm), [])
    if not rec: continue
    if len({r[0] for r in rec}) > 1:
        fresh = [r for r in rec if r[13] == 0]
        both.append([vm, vm_kind(vm), "; ".join(f"{r[0]}: {r[12].lower()}" for r in rec),
                     "; ".join(sorted({r[3] for r in rec})),
                     ("оба актуальны" if len(fresh) == len(rec) else ("один устарел" if fresh else "оба устарели"))])
    else:
        r = rec[0]
        only.append([vm, vm_kind(vm), r[0], r[3], r[8], r[9], r[12],
                     "защищён только одной консолью" if r[13] <= 1 else "НЕ ЗАЩИЩЁН"])
only.sort(key=lambda r: (r[7].startswith("НЕ"), str(r[0])))
n_dup, n_only_ok = len(both), sum(1 for r in only if not r[7].startswith("НЕ"))

# ---- сверка с реестром хостов
hosts = json.load(open(HOSTS, encoding="utf-8"))
vnames = {}
for c in coverage:
    if len(norm(c[1])) >= 4: vnames.setdefault(norm(c[1]), c[1])
cov_by_norm = {norm(c[1]): c for c in coverage if len(norm(c[1])) >= 4}
uncovered = []
for h in sorted(hosts, key=lambda x: tuple(int(p) if p.isdigit() else 0 for p in x["ip"].split("."))):
    hn = norm(h["host"]); best = None
    if len(hn) >= 4:
        for k in vnames:
            if k == hn: best = k; break
        if not best:
            for k in vnames:
                if k in hn or hn in k:
                    if not best or len(k) > len(best): best = k
    c = cov_by_norm.get(best) if best else None
    if c:
        rec = idx.get(best, [])
        uncovered.append([h["ip"], h["host"], (h.get("role") or "")[:110], c[12],
                          "; ".join(f"{r[0]} — {r[12].lower()}" for r in rec) or c[0],
                          f"объект «{c[1]}», задание «{c[3]}»", 3 if c[13] == 3 else (2 if c[13] == 2 else 0)])
    else:
        uncovered.append([h["ip"], h["host"], (h.get("role") or "")[:110], "НЕ НАЙДЕНО НИ В ОДНОМ VEEAM", "—",
                          ("hostname не указан в реестре — сопоставление невозможно" if len(hn) < 4 else
                           "Нет ни в заданиях, ни в точках. Если хост физический — не копируется ничем: заданий типа Physical Machine нет"),
                          3])
uncovered.sort(key=lambda r: (-r[6], r[0]))
n_unfound = sum(1 for r in uncovered if r[3].startswith("НЕ НАЙДЕНО"))
n_stale = sum(1 for c in coverage if c[13] == 3 and isinstance(c[9], int) and c[9] > 180)
n_node2 = sum(1 for c in coverage if re.search(r"node2$", str(c[1])))
n_disk  = sum(1 for e in errors if "not enough space" in e["Ошибка"])

# ============================================================ книга
wb = openpyxl.Workbook()
NAVY = "1F3864"; RED, ORANGE, YELLOW, GREEN = "FFC7CE", "FFD8A8", "FFE699", "C6EFCE"
HDR = PatternFill("solid", fgColor=NAVY); HF = Font(color="FFFFFF", bold=True, size=10)
TITLE = Font(bold=True, size=14, color=NAVY)
FILLS = {3: PatternFill("solid", fgColor=RED), 2: PatternFill("solid", fgColor=ORANGE),
         1: PatternFill("solid", fgColor=YELLOW), 0: PatternFill("solid", fgColor=GREEN)}
LFONT = {3: Font(color="9C0006", bold=True, size=10), 2: Font(color="9C5700", size=10),
         1: Font(size=10), 0: Font(color="006100", size=10)}
THIN = Border(*[Side(style="thin", color="BFBFBF")] * 4)

def put_header(ws, row, headers):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=c, value=h); cell.fill, cell.font = HDR, HF
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[row].height = 34
def put_row(ws, row, values, lvl=None, fmts=None, from_col=1):
    for c, v in enumerate(values, from_col):
        cell = ws.cell(row=row, column=c, value=v); cell.border = THIN
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        f = (fmts or {}).get(c)
        if f and isinstance(v, (int, float)) and not isinstance(v, bool): cell.number_format = f
        if lvl is not None and lvl in FILLS:
            cell.fill = FILLS[lvl]; cell.font = LFONT[lvl]
def widths(ws, w):
    for c, v in w.items(): ws.column_dimensions[get_column_letter(c)].width = v
def simple(name, title, headers, rows, w, note=None, fmts=None, lvl_col=None, hide=None):
    ws = wb.create_sheet(name)
    ws["A1"] = title; ws["A1"].font = TITLE
    hr = 3
    if note:
        ws["A2"] = note; ws["A2"].font = Font(italic=True, size=9, color="808080")
    put_header(ws, hr, headers)
    for i, r in enumerate(rows, hr + 1):
        lvl = r[lvl_col] if lvl_col is not None and isinstance(r[lvl_col], int) else None
        if lvl_col is not None: r = list(r) + [None] * (len(headers) - len(r)); r = r[:len(headers)]
        put_row(ws, i, r, lvl, fmts)
        if name.startswith("01_") or name.startswith("03_") or name.startswith("14_"):
            ws.row_dimensions[i].height = max(30, min(220, 12 * max(
                (len(str(v or "")) // max(int(ws.column_dimensions[get_column_letter(c)].width or 18), 1) + 1)
                for c, v in enumerate(r, 1))))
    ws.freeze_panes = ws.cell(row=hr + 1, column=1)
    ws.auto_filter.ref = f"A{hr}:{get_column_letter(len(headers))}{hr+len(rows)}"
    widths(ws, w)
    for c in (hide or []):
        if c <= len(headers): ws.column_dimensions[get_column_letter(c)].hidden = True
    return ws

# ---------------------------------------------------------------- 01 МАТРИЦА (главный лист)
# --- Матрица: ровно 12 колонок по ТЗ ---
MX = ["Объект","Источник","Куда пишется","Частота","Инструмент","Хранение / ретеншн","Offsite",
      "Кто чистит / процесс","Restore проверялся?","Статус проверки факта","Риск","Комментарий"]

RESTORE_OK   = "Да"          # подтверждённое тестовое восстановление
RESTORE_PART = "Только косвенно"
RESTORE_NO   = "Нет"
ST_OK        = "Подтверждено"
ST_NO        = "Не проверено"
ST_BAD       = "Проблема"
OFF_NO       = "НЕТ: копии вне площадки нет"
OFF_DUP      = "НЕТ: дублируется на второй консоли Veeam, но она в том же ЦО — это не offsite"

def restore_state(row_old):
    v = str(row_old.get(9) or "").strip().lower()
    if v.startswith(("да", "провер")) and any(ch.isdigit() for ch in v): return f"Да ({v})"
    if "косвен" in v or "нет, только" in v or "откат" in v:            return RESTORE_PART
    if v.startswith("не провер") or v.startswith("нет"):                return RESTORE_NO
    if v.startswith("не тест") or "не проверялось" in v:                return RESTORE_NO
    return ST_NO if not v else v

def offsite_state(v):
    s = str(v or "").strip()
    if re.match(r"^(да|есть|с3|s3|регру|reg\.ru|другой цод|другой цо)", s, re.I): return s
    if s.lower().startswith(("не проверено", "не задокументировано", "не подтверждено")): return "Не проверено"
    return OFF_NO

def who_cleans(v):
    s = str(v or "").strip()
    if re.search(r"cron|скрипт|rsync|find ", s, re.I): return s
    if "veam" in s or "—" == s: return "Veeam автоматически (retention policy)" if "—" != s else "Никто — старые копии не удаляются"
    return s or "Не указано"

def mx_rows():
    """Одна строка матрицы = одно задание Veeam. Тексты рассчитаны на читателя-руководителя."""
    for j in jobrows:
        other = next((c[0] for c in coverage if c[1] in j["objs"] and c[0] != j["srv"]), None)
        off = OFF_DUP if other else OFF_NO
        covered = j["covered_elsewhere"]
        status = ST_OK if j["lvl"] == 0 else (ST_NO if (j["lvl"] == 1 or covered) else ST_BAD)
        risk = {3: "Критичный", 2: "Высокий", 1: "Средний", 0: "Низкий"}[j["lvl"]]
        if covered: risk = "Средний"          # объект защищён другим заданием
        if j["lvl"] == 3 and re.match(r"(Базы данных биллинга|Ядро биллинга)", j["kind"]): risk = "Критичный"
        if j["kind"].startswith("Тестовое задание"): risk = "Низкий"
        # --- 1. Источник
        src = ("Виртуальные машины в VMware vSphere, управление через vCenter 192.168.160.202.\n"
               f"Задание {j['job']} на сервере {j['ip']} — консоль {j['srv']}.\n"
               f"Что входит ({j['n_objs']} шт.): {j['objs_txt']}")
        # --- 3. Куда пишется
        if "100%" in j["repo"]:
            dest = f"{j['repo']}\nДИСК ЗАПОЛНЕН НА 100% (0 ГБ свободно) — записать новые копии некуда"
        elif "не определён" in j["repo"]:
            dest = ("РЕПОЗИТОРИЙ НЕ ОПРЕДЕЛЁН: в выгрузке нет связи задание → репозиторий "
                    "(ошибка GetTargetStorages). Определить вручную: Консоль Veeam → Backup → "
                    f"«{j['job']}» → Edit → вкладка Storage")
        else:
            free = next((f"Свободно на диске репозитория: {r[5]:.0f} ГБ из {r[4]:.0f} ГБ ({r[7]:.0%})"
                         for r in repo_rows if j["srv"] == r[0] and r[3] in j["repo"]), "")
            dest = j["repo"] + (("\n" + free) if free else "")
        # --- 4. Частота (фактическое время)
        base_sched = re.sub(r"\s*в\s*$", "", (j["sched"] or "").strip())
        ftxt, fdays = j["fact_freq"]
        if j["sched_time"]:
            head = f"НАСТРОЙКА VEEAM: {base_sched} в {j['sched_time']}"
        else:
            head = f"НАСТРОЙКА VEEAM: {base_sched} (час запуска в выгрузке не зафиксирован)"
        if not j["last"]:
            head += f"\nФАКТИЧЕСКИ ЗАПУСКОВ: ни одного за всю историю"
            freq = head + ("\nЗадание ВЫКЛЮЧЕНО администратором" if j["on"].startswith("НЕТ") else "")
        else:
            fact_line = (f"ФАКТИЧЕСКИ ЗАПУСКИ: {ftxt}"
                         + (f", часы запуска по последним сессиям: {', '.join(j['fact_times'][:6])}" if j["fact_times"] else ""))
            mismatch = ""
            monthly = "раз в месяц" in base_sched or "Ежемесячно" in base_sched
            if monthly and ftxt.startswith(("еженедельно", "ежедневно", "через день")):
                mismatch = ("\nНЕСООТВЕТСТВИЕ: в настройке сказано «раз в месяц», "
                            f"а по журналу запусков копии делаются {ftxt}. "
                            "Проверить расписание задания в консоли Veeam")
            elif monthly and ftxt.startswith("примерно раз в месяц"):
                mismatch = "\nНастройка и факт совпадают: копии делаются примерно раз в месяц."
            freq = (f"{head}\n{fact_line}{mismatch}\n"
                    f"Последний запуск: {j['last'].strftime('%d.%m.%Y в %H:%M')} "
                    f"({j['days']} дн. назад), шёл {j['dur']} мин, итог — {j['res'] or 'нет данных'}\n"
                    f"Успешных запусков: {j['n_ok']} из {j['n_all']} ({j['ok']:.0%})"
                    + (f", с предупреждениями {j['n_warn']}" if j["n_warn"] else "")
                    + (f", с ошибкой {j['n_err']}" if j["n_err"] else ""))
        # --- 5. Инструмент
        tool = ("Veeam Backup & Replication 12.1, лицензия Enterprise Plus.\n"
                f"Сервер: {j['srv']} ({j['ip']}). Тип задачи: {j['jtype']}.\n"
                f"ТИП КОПИИ: {j['btype']}")
        # --- 6. Хранение / ретеншн
        kt = j["keep"].replace(" Последний полный бэкап:", "\nПоследний полный бэкап:").replace("..", ".")
        keep = (f"Срок хранения копий: {j['ret']} дн., удаляет сам Veeam по retention policy.\n"
                f"{kt}\n"
                f"Последние копии (новые сверху): {j['last3']}")
        # --- Комментарий
        runs = (f"{j['n_ok']} успешных из {j['n_all']} ({j['ok']:.0%})" if j["n_all"] else "запусков не было ни разу")
        if j["n_warn"]: runs += f", с предупреждениями {j['n_warn']}"
        if j["n_err"]:  runs += f", с ошибкой {j['n_err']}"
        cm = [f"ОБЪЕКТОВ: {j['n_objs']} — {j['objs_txt']}",
              f"ЗАПУСКИ: {runs}.",
              f"СОСТОЯНИЕ: {j['status']}"]
        if j["n_err_events"]:
            cm.append(f"ОШИБОК В ЛОГАХ: {j['n_err_events']} шт. Последняя — {j['last_err']}")
        elif j["on"].startswith("НЕТ"):
            cm.append("Ошибок в логах нет, потому что задание не запускается: копий нет вообще.")
        else:
            cm.append("ОШИБОК В ЛОГАХ НЕТ — задание отрабатывает чисто.")
        if covered:
            cm.append(f"ОБЪЕКТ ЗАЩИЩЁН ДРУГИМ ЗАДАНИЕМ: {', '.join(j['alt_jobs'])}. "
                      "Это задание-дубликат: следует удалить его или устранить причину сбоя.")
        if other:
            cm.append(f"Те же объекты копируются и на консоли {other} — фактически вторая копия, но в том же ЦО.")
        yield [j["kind"], src, dest, freq, tool, keep, off,
               (f"Veeam сам, автоматически: удаляет копии старше {j['ret']} дней. "
                f"Скриптов и людей для этого не нужно — настройка retention в самом задании."
                if j["jtype"] != "репликация" else
                "Никто: это репликация, а не резервная копия — старые состояния не хранятся"),
               RESTORE_NO, status, risk, "\n".join(cm)]

OLDW = openpyxl.load_workbook(OLD)
FACTS = {  # факты Veeam для объектов прежней матрицы: (куда, частота, инструмент, хранение, offsite, restore, статус, риск, комментарий)
 "sv3 Services": ("sv3 → G:\\Backups (репозиторий sv3 на 192.168.160.14, 10 ТБ, занято 90%)",
  "ежедневно; последний запуск 06.10.2026 (1 дн. назад), 66 мин — результат «Ошибка»",
  "Veeam B&R 12.1 (консоль «omicron», 192.168.160.14), задача sv3 Services",
  "хранение 14 дн.; 23 ВМ в задании, 344 точки в репозитории; свежая точка 06.10.2026",
  OFF_NO, RESTORE_NO, ST_BAD, "Критичный",
  "21 ошибка «нет места на диске» по путям G:\\Backups\sv3 Services. ВМ gitlab.omicron и vault.omicron недоступны и пропускаются (36 раз); у vault точек нет вовсе"),
 "DBnode1": ("репозиторий в выгрузке не читается (ошибка GetTargetStorages)",
  "ежемесячно, 1-е число; последний запуск 03.10.2026 (4 дн. назад), 158 мин — успех",
  "Veeam B&R 12.1 (консоль «omicron»), задача DBnode1",
  "хранение 14 дн.; 10 полных бэкапов, свежая точка 03.10.2026", OFF_NO, RESTORE_NO, ST_BAD, "Высокий",
  "Работает стабильно (13 успешных из 13), но полный бэкап только 1-го числа месяца — при хранении 14 дней реальное окно защиты 2 недели в месяце"),
 "DBnode3": ("репозиторий в выгрузке не читается (ошибка GetTargetStorages)",
  "ежемесячно, 1-е число; последний запуск 03.10.2026 (4 дн. назад), 38 мин — успех",
  "Veeam B&R 12.1 (консоль «omicron»), задача DBnode3",
  "хранение 14 дн.; 7 точек (6 полных + 1 инкремент), свежая точка 03.10.2026", OFF_NO, RESTORE_NO, ST_BAD, "Выский",
  "12 успешных из 13 (92%). Та же проблема: ежемесячный ритм при хранении 14 дней"),
 "DBnode2": ("репозиторий в выгрузке не читается (ошибка GetTargetStorages)",
  "ежемесячно (предположительно); последний запуск 26.09.2026 (11 дн. назад), 0.2 мин — ошибка",
  "Veeam B&R 12.1 (консоль «omicron»), задача DBnode2 — ОТСУТСТВУЕТ В КОНФИГУРАЦИИ КОНСОЛИ",
  "хранение 14 дн.; последние точки 27.06.2026 — 101 день без копии", OFF_NO, RESTORE_NO, ST_BAD, "Критичный",
  "Задание исчезло из конфигурации, 32 запуска подряд с ошибкой. Базы данных биллинга на нодах node2 не копируются вообще"),
 "sv3 Exchange": ("sv3 exchange → H:\\Backups (репозиторий на 192.168.160.14, 10 ТБ, занято 44%)",
  "ежедневно 21:00; последний запуск 06.10.2026 (1 дн. назад), 182 мин — только предупреждения",
  "Veeam B&R 12.1 (консоль «omicron»), задача sv3 Exchange",
  "хранение 14 дн.; 51 точка, только инкременты — полных бэкапов за период нет",
  OFF_NO, RESTORE_NO, ST_BAD, "Критичный",
  "0 успешных из 100: 78 запусков с предупреждениями, 22 с ошибкой. Вторая консоль Veeam Exchange не копирует вовсе — единственное покрытие под вопросом"),
 "sv3 BackConf": ("sv3 → G:\\Backups (репозиторий sv3 на 192.168.160.14)",
  "ежедневно 22:00; последний запуск 06.10.2026 (1 дн. назад), 32 мин — предупреждения",
  "Veeam B&R 12.1 (консоль «omicron»), задача sv3 BackConf",
  "хранение 14 дн.; 9 точек, свежая точка 06.10.2026",
  OFF_DUP + ": та же схема на консоли «db» работает — задача backconf 24 успешных из 24",
  RESTORE_NO, ST_BAD, "Высокий",
  "18 успешных из 77 (23%), 48 запусков с ошибкой, из них 7 «нет места на диске» по G:\\Backups\sv3 BackConf"),
 "netboxv2": ("sv3 → G:\\Backups (репозиторий sv3 на 192.168.160.14)",
  "ежедневно 22:00; последний запуск 06.10.2026 (1 дн. назад), 43 мин — предупреждения",
  "Veeam B&R 12.1 (консоль «omicron»), задача netboxv2",
  "хранение 14 дн.; 6 точек, свежая точка 06.10.2026",
  OFF_DUP + ": на консоли «db» задача Monitoring 35 успешных из 35",
  RESTORE_NO, ST_BAD, "Средний",
  "18 успешных из 52 (35%), 16 запусков с ошибкой, 2 «нет места на диске»"),
 "K3S": ("sv3 → G:\\Backups (предположительно, подтверждения в выгрузке нет)",
  "ежедневно; последний запуск 03.10.2026 (4 дн. назад), 731 мин — успех",
  "Veeam B&R 12.1 (консоль «omicron»), задача K3S",
  "хранение 14 дн.; в задании только узел node3, 4 точки с 12.09.2026",
  OFF_NO, RESTORE_NO, ST_BAD, "Высокий",
  "14 успешных из 49 (29%). Ноды node1 и node2 не копируются ни одной из консолей"),
 "Share main": ("NAS-бэкап шары E:\\ (репозиторий NAS в выгрузке не указан)",
  "ежедневно 01:00; последний запуск 07.10.2026 (0 дн. назад), 5.8 мин — предупреждения",
  "Veeam B&R 12.1 (консоль «omicron»), задача Share main (копирование NAS-шары на уровне файлов)",
  "хранение 14 дн.; копируются файлы, точек восстановления ВМ не создаётся",
  OFF_DUP + ": та же шара копируется на консоли «db» — задача Share 83 успешных из 83",
  RESTORE_NO, ST_BAD, "Высокий",
  "35 успешных из 111 (32%), 43 запуска с ошибкой"),
 "ex2-flash": ("репозиторий в выгрузке не читается (ошибка GetTargetStorages)",
  "ежемесячно, 24-е; запусков не было ни разу за всю историю",
  "Veeam B&R 12.1 (консоль «omicron»), задача ex2-flash",
  "хранение 14 дн.; точек в репозитории нет ни одной", OFF_NO, RESTORE_NO, ST_BAD, "Средний",
  "Задание включено, но никогда не отработало (Last result = None)"),
 "k3s": ("k3s → K:\\Backups (репозиторий на 192.168.160.16) — ДИСК ЗАПОЛНЕН НА 100%",
  "ежедневно; запусков не было (задание выключено вручную)",
  "Veeam B&R 12.1 (консоль «db», 192.168.160.16), задача k3s",
  "хранение 14 дн.; 1 точка у узла node4 от 20.03.2026 (201 день назад)",
  OFF_NO, RESTORE_NO, ST_BAD, "Критичный",
  "Задание выключено вручную из-за заполненного диска K: (699,94 ГБ из 699,94, свободно 0). Ноды node1 и node2 не копируются"),
}
FACTS_MATCH = [("sv3 Services", lambda nm: nm.startswith("sv3 Services")),
 ("DBnode1",     lambda nm: nm.startswith("DBnode1") or "omiplat billing" in nm),
 ("DBnode2",     lambda nm: nm.startswith("DBnode2") or "rtc billing DB" in nm),
 ("DBnode3",     lambda nm: nm.startswith("DBnode3")),
 ("sv3 Exchange",lambda nm: nm.startswith("sv3 Exchange")),
 ("sv3 BackConf",lambda nm: nm.startswith("sv3 BackConf")),
 ("netboxv2",    lambda nm: nm.startswith("netboxv2")),
 ("K3S",         lambda nm: nm.startswith("K3S")),
 ("Share main",  lambda nm: nm.startswith("Share main")),
 ("ex2-flash",   lambda nm: nm.startswith("ex2-flash")),
 ("k3s",         lambda nm: nm.startswith("k3s") or nm.startswith("Vault (k3s)") or nm.startswith("etcd k3s"))]

rows = list(mx_rows())
for row in OLDW["01_Матрица_бэкапов"].iter_rows(min_row=4, values_only=True):
    if not row[0]: continue
    old = {"объект": row[1], "источник": row[2], "куда": row[3], "частота": row[4], "инструмент": row[5],
           "хранение": row[6], "offsite": row[7], "чистит": row[8], "restore": row[9],
           "статус": row[10], "риск": row[11], "комментарий": row[12]}
    nm = str(old["объект"] or "")
    for key, test in FACTS_MATCH:
        if test(nm):
            f = FACTS[key]
            old.update({"куда": f[0], "частота": f[1], "инструмент": f[2], "хранение": f[3],
                        "offsite": f[4], "restore": f[5], "статус": f[6], "риск": f[7]})
            old["комментарий"] = (str(old["комментарий"] or "") + " | ФАКТ VEEAM 07.10.2026: " + f[8]).strip(" |")
            break
    rows.append([old["объект"], old["источник"], old["куда"], old["частота"], old["инструмент"],
                 old["хранение"], offsite_state(old["offsite"]), who_cleans(old["чистит"]),
                 restore_state({"restore": old["restore"]}), old["статус"] or ST_NO,
                 old["риск"] or ST_NO, old["комментарий"]])

mx = simple("01_Матрица", "МАТРИЦА РЕЗЕРВНОГО КОПИРОВАНИЯ (12 колонок по ТЗ)",
            MX, rows, {1:30,2:46,3:34,4:42,5:42,6:46,7:32,8:30,9:18,10:20,11:12,12:78},
            note="Строки 4+ (первая часть) — задания Veeam, факты из выгрузок обеих консолей. "
                 "Строки после них — процессы вне Veeam (cron, rsync, mysqldump) из прежней матрицы аудита; "
                 "их поля «Откуда», «Куда», «Частота» перенесены из старой версии матрицы и требуют проверки. "
                 "Строка целиком красная = риск Критичный, оранжевая = Высокий.",
            fmts={})
# перенос строк по высоте содержимого
for r in range(4, 4 + len(rows)):
    mx.row_dimensions[r].height = max(58, min(300, 12 * max(
        (len(str(mx.cell(row=r, column=c).value or "")) // max(int(mx.column_dimensions[get_column_letter(c)].width or 18), 1) + 1)
        for c in range(1, 13))))

# подсветка по риску
RISK_FILL = {"Критичный": 3, "Высокий": 2, "Средний": 1, "Низкий": 0}
for r in range(4, 4 + len(rows)):
    lvl = RISK_FILL.get(str(mx.cell(row=r, column=11).value or "").strip(), None)
    if lvl is None: continue
    if lvl in (3, 2):
        for c in range(1, 13):
            cell = mx.cell(row=r, column=c); cell.fill = FILLS[lvl]; cell.font = LFONT[lvl]
    else:
        mx.cell(row=r, column=11).fill = FILLS[lvl]; mx.cell(row=r, column=11).font = LFONT[lvl]
    mx.cell(row=r, column=11).font = Font(bold=True, color=LFONT[lvl].color.rgb if lvl in (3, 2) else "006100")

# ---------------------------------------------------------------- 02 Сводка
ws = wb.create_sheet("02_Сводка")
ws["A1"] = "ИТОГИ АУДИТА — ДВЕ КОНСОЛИ VEEAM B&R 12.x"; ws["A1"].font = Font(bold=True, size=15, color=NAVY)
rows = [("Дата среза данных (последний запуск в выгрузках)", REF.strftime("%d.%m.%Y %H:%M")), ("", "")]
for a in A:
    t = a["totals"]
    rows += [(f"КОНСОЛЬ {a['label']}", f"{a['ip']}, сервер {a['host']}, выгрузка {a['dump']}"),
             ("  серверов в инвентаре Veeam", f"{len(a['servers'])}: " + ", ".join(s["Name"] for s in a["servers"])),
             ("  лицензия", "; ".join(f"{l.get('Edition','')} {l.get('Type','')}, до {l.get('ExpirationDate','')[:10]}" for l in a["license"])),
             ("  прокси", "; ".join(f"{p['Name']} ({p['Host']})" for p in a["proxies"])),
             ("  заданий всего", f"{len(a['jobs'])}, работает нормально: {sum(1 for r in a['jobs'] if r['lvl']==0)}, проблемных: {sum(1 for r in a['jobs'] if r['lvl']>=2)}"),
             ("  запусков за всю историю", f"{t['all']}: успешных {t['ok']}, с предупреждениями {t['warn']}, с ошибкой {t['err']}"),
             ("  объектов под защитой", f"{len(a['coverage'])}, без актуальной копии: {sum(1 for c in a['coverage'] if c[13]>=2)}")]
rows += [("", ""), ("ИТОГ ПО ДВУМ КОНСОЛЯМ", ""),
         ("заданий всего", str(len(jobrows))),
         ("запусков всего", f"{T['all']}: успешных {T['ok']} ({T['ok']/max(T['all'],1):.0%}), "
          f"с предупреждениями {T['warn']} ({T['warn']/max(T['all'],1):.0%}), с ошибкой {T['err']} ({T['err']/max(T['all'],1):.0%})"),
         ("объектов (с повторами по консолям)", f"{len(coverage)}, уникальных {len(allvms)}"),
         ("  с актуальной копией (≤7 дней)", str(sum(1 for c in coverage if c[13] == 0))),
         ("  без актуальной копии", str(sum(1 for c in coverage if c[13] == 3))),
         ("  из них без копии более 180 дней", str(n_stale)),
         ("копируется в обеих консолях (дубль)", f"{n_dup} объектов"),
         ("копируется только в одной консоли", f"{len(only)}, из них нормально защищено {n_only_ok}"),
         ("хостов реестра не найдено ни в одном Veeam", f"{n_unfound} из {len(uncovered)}"),
         ("", ""),
         ("ХРАНИЛИЩА", "; ".join(f"{r[1]} {r[3]} — свободно {r[6]:.0f} из {r[4]:.0f} ГБ ({r[7]:.0%})" for r in repo_rows)),
         ("ДИСКИ В РИСКЕ", "; ".join(f"{r[0]} {r[1]} — свободно {r[5]:.0%}" for r in disk_rows if r[7] >= 2)),
         ("OFFSITE (копия вне площадки)", "НЕ ПОДТВЕРЖДЕН — все 11 репозиториев локальные папки на двух серверах в одном ЦО"),
         ("ПРОВЕРКИ ВОССТАНОВЛЕНИЯ", "НЕ ЗАФИКСИРОВАНЫ — ни одного теста за всю историю"),
         ("", ""), ("КАК ОБЪЯСНИТЬ РУКОВОДСТВУ (в четырёх пунктах)", ""),
         ("Защищено ли то, что важно", "Билинг, RADIUS, ProxySQL, домены AD, 1С, колл-центры, VPN и доступ — защищены, "
          "задания отрабатывают ежедневно без ошибок (консоль Veeam #2 «db»). Это основная часть инфраструктуры."),
         ("Что НЕ защищено", "Microsoft Exchange (0 успешных копий из 100), базы данных биллинга на нодах node2 (101 день без копии), "
          "репозиторий GitLab (одна копия от 05.09.2026), хранилище секретов Vault (копий нет вообще)."),
         ("Почему это произошло", "Две причины, обе технические и обе чинятся за час работы: закончилось место на дисках "
          "репозиториев (G: занят на 90%, K: на 100%) и часть заданий была отключена вручную или потеряла связь с репозиторием."),
         ("Главный риск для компании", "Нет копий вне площадки: обе консоли и все 11 хранилищ находятся в одном сегменте сети. "
          "Потеря этого сегмента = потеря всех копий. Плюс за всю историю не было ни одной проверки восстановления."),
         ("Что достаточно сделать сейчас", "Освободить 2 ТБ на диске G:, включить задание k3s после очистки диска K:, "
          "починить задание DBnode2 и вернуть две недоступные ВМ (Vault, GitLab)."),
         ("", ""), ("ГЛАВНЫЕ ВЫВОДЫ", "")]
A1, A2 = (A + [A[0]])[:2]
rows += [
 ["1", f"{A1['label']} ({A1['ip']}) работает нормально: {sum(1 for r in A1['jobs'] if r['lvl']==0)} заданий без единой ошибки. "
        f"Это основной защищающий контур парка"],
 ["2", f"{A2['label']} ({A2['ip']}) в аварии: {sum(1 for r in A2['jobs'] if r['lvl']>=2)} из {len(A2['jobs'])} заданий проблемны, "
        f"успешных запусков {A2['totals']['ok']} из {A2['totals']['all']} ({A2['totals']['ok']/max(A2['totals']['all'],1):.0%}). Причина — диск G: заполнен на 90%"],
 ["3", "Биллинг-ядра, RADIUS, ProxySQL и домены AD защищены заданиями второй консоли (83 успешных запуска из 83). "
       "В первой консоли их копии заморожены с 20.09.2025 — это дубли, а не потеря защиты"],
 ["4", f"Базы данных биллинга на нодах node2 ({n_node2} шт.) без копии с 27.06.2026 — задание DBnode2 отсутствует в конфигурации первой консоли"],
 ["5", "Microsoft Exchange: задание sv3 Exchange на первой консоли — 0 успешных из 100, вторая консоль Exchange не копирует вовсе. "
       "Единственное покрытие Exchange под вопросом"],
 ["6", "Kubernetes: задание k3s на второй консоли ВЫКЛЮЧЕНО (диск K: заполнен на 100%), на первой копируется только node3. "
       "Ноды node1 и node2 не копируются нигде. Для Longhorn (mail-PVC 800 ГБ) backup target не настроен"],
 ["7", "vault.omicron — ни одной точки восстановления; gitlab.omicron — единственный полный бэкап от 05.09.2026. Исходники GitLab не защищены"],
 ["8", f"{n_unfound} из {len(uncovered)} хостов реестра не найдены ни в одной консоли. Заданий типа Physical Machine нет вообще — "
       "физические серверы парка не защищены"],
 ["9", f"{n_dup} объектов дублируются между консолями — единственный намёк на вторую копию, но обе консоли в одном ЦО"],
 ["10", f"Ни одного теста восстановления за всю историю. Неизвестно, восстанавливаются ли эти копии вообще"]]
for r, (k, v) in enumerate(rows, 3):
    c1 = ws.cell(row=r, column=1, value=k)
    c1.font = Font(bold=True, size=10, color=NAVY if str(k).startswith(("КОНСОЛЬ", "ИТОГ", "ГЛАВНЫЕ")) else "000000")
    c1.alignment = Alignment(wrap_text=True, vertical="top")
    c2 = ws.cell(row=r, column=2, value=v); c2.alignment = Alignment(wrap_text=True, vertical="top")
    if str(k) in ("OFFSITE (копия вне площадки)", "ПРОВЕРКИ ВОССТАНОВЛЕНИЯ") or str(k).startswith("ДИСКИ В РИСКЕ"):
        c2.font = Font(bold=True, color="9C0006")
widths(ws, {1: 46, 2: 132})
ws["A2"] = "Все цифры получены из выгрузок консолей Veeam (файлы 03/06/07/08/10/11-*.csv), а не из документации."
ws["A2"].font = Font(italic=True, size=9, color="808080")

# ---------------------------------------------------------------- остальные листы
simple("03_Задания", "ЗАДАНИЯ VEEAM — подробно по каждому заданию (что это и как работает)",
       ["Сервер Veeam (адрес)","Задание (имя в Veeam)","Что копирует","Тип задачи","Включено?",
        "Расписание (настройка Veeam)","Сколько объектов в задании","Запусков всего","Успешных запусков",
        "Доля успеха","Запусков с предупреждениями","Запусков с ошибкой","Точек копии всего",
        "Из них полных (Full)","Из них инкрементных","Последний запуск (факт)","Дней назад (с последнего запуска)",
        "Сколько длился запуск, мин","Итог последнего запуска","Куда пишется (репозиторий)","Хранение копий",
        "Статус","lvl"],
       [[j["srv"], j["job"], j["kind"], j["jtype"], j["on"], j["sched"], j["n_objs"], j["n_all"], j["n_ok"], j["ok"],
         j["n_warn"], j["n_err"], j["npts"], j["nfull"], j["nincr"], j["last"], j["days"], j["dur"], j["res"],
         j["repo"], j["keep"], j["status"], j["lvl"]] for j in jobrows],
       {1:18,2:16,3:34,4:24,5:20,6:22,7:9,8:10,9:10,10:11,11:11,12:10,13:9,14:9,15:11,16:20,17:11,18:10,19:24,20:34,21:70,22:40,23:4},
       note="Сортировка: сначала проблемные задания. Скрытый столбец 23 — служебный уровень подсветки.",
       fmts={7:NF_INT,8:NF_INT,9:NF_INT,11:NF_INT,12:NF_INT,13:NF_INT,14:NF_INT,15:NF_INT,17:NF_INT,18:NF_INT,10:NF_PCT,16:DFMT_T},
       lvl_col=22, hide=[23])

simple("04_Покрытие", "ПОКРЫТИЕ ОБЪЕКТОВ — что реально копируется и когда была последняя копия",
       ["Сервер Veeam (адрес)","Объект (ВМ, шара или узел)","Тип объекта","Задание (имя в Veeam)",
        "Копий (точек) всего","Из них полных (Full)","Из них инкрементных (Increment)","Тип последней копии",
        "Последняя копия создана","Дней назад (с последней копии)","Последний полный бэкап создан",
        "Дней с последнего полного","Статус","lvl"],
       coverage, {1:18,2:34,3:28,4:28,5:9,6:9,7:11,8:22,9:20,10:11,11:22,12:12,13:40,14:4},
       note="Красным — копии нет дольше 30 дней либо точек нет вовсе. Оранжевым — копии нет 15–30 дней.",
       fmts={5:NF_INT,6:NF_INT,7:NF_INT,10:NF_INT,12:NF_INT,9:DFMT_T,11:DFMT},
       lvl_col=13, hide=[14])

simple("05_Простои", "ПРОСТОИ И НЕПОКРЫТИЕ — задания и объекты без актуальных копий",
       ["Сервер Veeam (адрес)","Что за строка (задание или объект)","Имя","Что это",
        "Задание / где находится","Последняя активность","Дней назад","Статус","Пояснение"],
       idle, {1:18,2:10,3:32,4:32,5:30,6:22,7:11,8:44,9:60},
       note="Требует немедленного внимания. Основная масса проблем — на консоли «omicron».",
       fmts={7:NF_INT,6:DFMT_T})

ws = wb.create_sheet("06_Две_консоли")
ws["A1"] = "СВЕРКА ДВУХ КОНСОЛЕЙ — дублирование и пробелы в покрытии"; ws["A1"].font = TITLE
ws["A2"] = f"Один и тот же объект копируется в обоих Veeam: {n_dup}. Фактически это скрытая вторая копия, но обе консоли в одном ЦО."
ws["A2"].font = Font(italic=True, size=9, color="808080")
put_header(ws, 4, ["Объект","Тип объекта","Состояние по серверам Veeam","Какими заданиями копируется","Оценка"])
for i, row in enumerate(both, 5): put_row(ws, i, row)
r = 5 + len(both) + 2
ws.cell(row=r, column=1, value="ОБЪЕКТЫ, КОТОРЫЕ КОПИРУЕТ ТОЛЬКО ОДНА КОНСОЛЬ").font = Font(bold=True, size=11, color=NAVY)
put_header(ws, r + 1, ["Объект","Тип объекта","Сервер Veeam (адрес)","Задание","Последняя копия","Дней назад","Статус","Примечание","lvl"])
for i, o in enumerate(only, r + 2):
    put_row(ws, i, o + [3 if o[7].startswith("НЕ") else 0], 3 if o[7].startswith("НЕ") else 0,
            {5: DFMT_T, 6: NF_INT})
widths(ws, {1:34,2:28,3:72,4:34,5:26,6:11,7:40,8:44,9:4})
ws.column_dimensions["I"].hidden = True
ws.freeze_panes = "A5"

simple("07_Точки", "ТОЧКИ ВОССТАНОВЛЕНИЯ — каждая созданная копия (для выгрузки данных)",
       ["Сервер Veeam (адрес)","Когда создана копия","Объект (ВМ или шара, которую копируют)",
        "Имя точки копии (как назвал Veeam)","Тип копии"],
       [[a["label"], pdt(r["Время создания"]), r["ВМ / объект"], r["Имя точки"], PT_FULL.get(r["Тип"], r["Тип"])]
        for a in A for r in a["rps"]], {1:18,2:22,3:36,4:36,5:22}, fmts={2:DFMT_T})
simple("08_Сессии", "ЗАПУСКИ РЕЗЕРВНОГО КОПИРОВАНИЯ — все сессии обеих консолей",
       ["Сервер Veeam (адрес)","Начало сессии","Задание (имя в Veeam)","Результат запуска",
        "Состояние процесса","Окончание сессии","Длительность, мин"],
       [[a["label"], pdt(r["Время"]), r["Задание"], RES_FULL.get(r["Результат"], r["Результат"]),
         STATE_FULL.get(r["Состояние"], r["Состояние"]), pdt(r["Окончание"]),
         round(float(r["Длит. (мин)"])) if r["Длит. (мин)"] else None] for a in A for r in a["sessions"]],
       {1:18,2:20,3:16,4:28,5:22,6:20,7:12}, fmts={2:DFMT_T,6:DFMT_T,7:NF_INT},
       note="Период: 08.01.2026 — " + REF.strftime("%d.%m.%Y") +
            ". «Завершено штатно» означает, что сессия завершилась, а не что она успешна — смотрите столбец «Результат».")
simple("09_Ошибки_сводка", "ОШИБКИ — СВОДКА ПО КЛАССАМ",
       ["Сервер Veeam (адрес)","Задание (имя в Veeam)","Класс ошибки","Сколько раз встретилась","Что это значит"], errsum,
       {1:18,2:16,3:32,4:10,5:66}, fmts={4:NF_INT},
       note=f"Всего записей об ошибках в выгрузках: {len(errors)}")
simple("10_Ошибки", "ОШИБКИ — ПОЛНЫЙ СПИСОК",
       ["Когда произошла","Сервер Veeam (адрес)","Задание (имя в Veeam)","Класс ошибки","Текст ошибки из лога Veeam"],
       [[pdt(e["Время"]), a["label"], e["Задание"], err_class(e["Ошибка"]), e["Ошибка"]]
        for a in A for e in a["errors"]], {1:22,2:18,3:16,4:30,5:110}, fmts={1:DFMT_T})

ws = wb.create_sheet("11_Хранилища")
ws["A1"] = "РЕПОЗИТОРИИ И ДИСКИ"; ws["A1"].font = TITLE
ws["A2"] = "Репозиторий — целевая папка, куда Veeam складывает копии. Все репозитории локальные, копии вне площадки нет."
ws["A2"].font = Font(italic=True, size=9, color="808080")
put_header(ws, 4, ["Сервер Veeam (адрес)","Репозиторий (имя в Veeam)","Что это","Путь на диске","Объём диска",
                   "Занято копиями","Свободно","Свободно, %","Состояние","Комментарий"])
for i, row in enumerate(repo_rows, 5):
    lvl = 3 if row[8] == "ЗАПОЛНЕН" else (2 if row[8] == "РИСК" else 0)
    put_row(ws, i, row, lvl, {5:NF_GB,6:NF_GB,7:NF_GB,8:NF_PCT})
r = 5 + len(repo_rows) + 2
ws.cell(row=r, column=1, value="СВОБОДНОЕ МЕСТО НА ДИСКАХ СЕРВЕРОВ VEEAM").font = Font(bold=True, size=11, color=NAVY)
put_header(ws, r + 1, ["Сервер Veeam (адрес)","Диск","Занято","Свободно","Объём","Свободно, %","Состояние","lvl"])
for i, row in enumerate(disk_rows, r + 2):
    put_row(ws, i, row, row[7], {3:NF_GB,4:NF_GB,5:NF_GB,6:NF_PCT})
widths(ws, {1:18,2:26,3:28,4:16,5:14,6:14,7:14,8:13,9:14,10:62})
ws.freeze_panes = "A5"
for rr in (r + 3, r + 4):
    ws.cell(row=rr, column=1).font = Font(bold=True, color="9C0006")

simple("12_Не_покрыто", "СВЕРКА С РЕЕСТРОМ ХОСТОВ АУДИТА (UG_Telecom/reports/hosts.json)",
       ["IP-адрес","Hostname","Роль на сервере","Состояние копирования","Где защищён","Объект Veeam / причина","lvl"],
       uncovered, {1:16,2:32,3:70,4:38,5:44,6:64,7:4},
       note=f"Красным — хосты, не найденные ни в одной консоли: {n_unfound}. Если такой хост физический, его не копирует ничто: "
            "заданий типа Physical Machine нет ни на одной консоли.",
       lvl_col=6, hide=[7])

# ---------------------------------------------------------------- 13 Справочник
ws = wb.create_sheet("13_Справочник")
ws["A1"] = "СПРАВОЧНИК — что означают термины и цвета"; ws["A1"].font = TITLE
LEG = [("ТИПЫ ТОЧЕК ВОССТАНОВЛЕНИЯ", ""),
 ("Полный (Full)", "Полная копия виртуальной машины целиком. Без свежего полного бэкапа инкременты не восстановить."),
 ("Инкремент (Increment)", "Разница с предыдущей точкой. Занимает мало места, но требует цепочку предыдущих точек. Нет свежего Full дольше 30 дней — объект фактически невосстановим."),
 ("Снапшот реплики", "Снимок реплики (например WireGuard). Не полная копия, а состояние на момент."),
 ("", ""), ("ТИПЫ ЗАДАНИЙ VEEAM", ""),
 ("резервное копирование", "Обычная задача: регулярно создаёт точки восстановления."),
 ("копирование NAS-шары", "Копирование данных с сетевой шары на уровне файлов — точек восстановления не создаёт, поэтому их отсутствие нормально."),
 ("репликация", "Постоянная копия на другой узел. Это отказоустойчивость, а не резервная копия."),
 ("", ""), ("РЕЗУЛЬТАТ ОДНОГО ЗАПУСКА", ""),
 ("Успех", "Все объекты скопированы, свежая точка создана."),
 ("Успех с предупреждениями", "Копия создана, но были предупреждения (часто — пропущенные недоступные ВМ). Считать неполным успехом."),
 ("Ошибка", "Задание упало, копия за этот день не создана."),
 ("", ""), ("СТАТУС В ОТЧЁТЕ", ""),
 ("Защищён: копия свежая", "Последняя точка не старше 7 дней."),
 ("Слабо", "Копии нет 8–14 дней."),
 ("РИСК: нет копии N дн.", "Копии нет 15–30 дней."),
 ("ПРОСТОЙ: нет копии N дн.", "Копии нет больше 30 дней либо точек нет вообще."),
 ("ВЫКЛЮЧЕНО ВРУЧНУЮ", "Задание отключено администратором. Пока выключено — копий нет."),
 ("НЕ РАБОТАЕТ: ни одного запуска", "Задание включено, но ни разу не отработало за всю историю. Часто — дубликат или ошибка настройки."),
 ("НЕ РАБОТАЕТ: задание сломано", "Задание пропало из конфигурации, последние запуски — с ошибкой."),
 ("", ""), ("ЦВЕТА СТРОК", ""),
 ("Красный", "Критично: копии нет больше 30 дней, точек нет, задание выключено / сломано / не работает."),
 ("Оранжевый", "Высокий риск: копии нет 15–30 дней либо задание нестабильно (успех 35–75%)."),
 ("Жёлтый", "Средний риск: копии нет 8–14 дней."),
 ("Зелёный", "Всё в порядке, копии свежие."),
 ("", ""), ("ПОЛЯ ОТЧЁТА", ""),
 ("Доля успеха", "Успешные запуски ÷ все запуски за всю историю задания. Ниже 35% — критично."),
 ("Дней назад", "Сколько дней прошло с последнего запуска или последней точки на дату среза отчёта."),
 ("Точек / Полных / Инкрементов", "Сколько всего точек восстановления у объекта и сколько из них полных бэкапов."),
 ("Хранение / ретеншн", "Сколько дней Veeam хранит точки перед удалением (retention policy)."),
 ("Offsite", "Есть ли копия репозитория за пределами текущей площадки. В обоих Veeam — НЕТ."),
 ("Кто чистит / процесс", "Кто удаляет старые копии: retention policy Veeam или скрипт с cron."),
 ("Restore проверялся?", "Была ли выполнена практическая проверка восстановления. Везде — нет."),
 ("", ""), ("ТЕРМИНЫ В СТАТУСЕ ХОСТОВ", ""),
 ("", ""), ("ПОЯСНЕНИЕ КОЛОНОК В ЛИСТАХ ОТЧЁТА", ""),
 ("Лист 03_Задания · Задание (имя в Veeam)", "Техническое название задания в консоли Veeam. Одно задание = одна строка отчёта: «что копируется» + «как копируется»."),
 ("Лист 03_Задания · Расписание (настройка Veeam)", "Что администратор задал в Veeam: ежедневно / ежемесячно день N. Это НАСТРОЙКА, а не факт — фактические запуски показаны в колонке «Последний запуск»."),
 ("Лист 03_Задания · Доля успеха", "Успешные запуски ÷ все запуски по этому заданию за всю историю. Ниже 35% — критично: значит, копии создаются изредка и в основном падают."),
 ("Лист 03_Задания · Дней назад (с последнего запуска)", "Сколько дней назад задание отработало в последний раз. Дата среза отчёта — 07.10.2026."),
 ("Лист 03_Задания · Сколько длился запуск, мин", "Время работы задания в минутах. 700+ минут = копирование шло более 11 часов — признак нехватки места или узкого канала."),
 ("Лист 04_Покрытие · Объект", "Что именно копируют: виртуальная машина (bg-core.flash), узел (K3S node3), контроллер домена (Active Directory(360pro.online)) или сетевая шара (E:\\)."),
 ("Лист 04_Покрытие · Задание (имя в Veeam)", "Какое задание отвечает за этот объект. Если написано «НЕ ВХОДИТ НИ В ОДНО ЗАДАНИЕ» — объект есть в репозитории, но ни одно задание сейчас его не копирует (остались старые точки)."),
 ("Лист 04_Покрытие · Копий (точек) всего", "Сколько копий данного объекта лежит в репозитории."),
 ("Лист 04_Покрытие · Дней назад (с последней копии)", "Сколько дней прошло с момента создания самой свежей копии объекта. 0–7 дней — норма, 15–30 — риск, больше 30 — объект фактически без копии."),
 ("Лист 04_Покрытие · Дней с последнего полного", "Сколько дней прошло с последнего ПОЛНОГО (Full) бэкапа. Важно: инкременты без свежего полного восстановить нельзя — цепочка потеряна."),
 ("Лист 04_Покрытие · Тип последней копии", "Полный (Full) = копия целиком. Инкремент (Increment) = только изменения с прошлой копии. Снапшот реплики = состояние реплики, не полная копия."),
 ("Лист 07_Точки · Объект (ВМ или шара)", "Какая виртуальная машина или шара была скопирована в этой строке."),
 ("Лист 07_Точки · Имя точки копии", "Название, которое Veeam присвоил копии внутри репозитория. Обычно совпадает с именем объекта. Это техническое имя для восстановления, а не описание данных."),
 ("Лист 07_Точки · Тип копии", "Полный / Инкремент / Снапшот реплики — см. выше."),
 ("Лист 08_Сессии · Результат запуска", "Успех = все объекты скопированы. Успех с предупреждениями = копия есть, но часть объектов пропущена (обычно недоступные ВМ). Ошибка = копия за этот запуск не создана."),
 ("Лист 08_Сессии · Состояние процесса", "Завершено штатно = сессия дошла до конца. Это НЕ значит «успех» — смотрите колонку «Результат запуска»."),
 ("Лист 11_Хранилища · Репозиторий", "Папка, куда Veeam складывает копии. У каждого задания свой репозиторий: sv3, AD, CC, 1c, Access, k3s и другие."),
 ("Лист 11_Хранилища · Свободно, %", "Доля свободного места на диске репозитория. Меньше 15% — копирование начнёт падать с ошибкой «нет места на диске»."),
 ("", ""), ("КАК ПОНЯТЬ СТАТУСЫ И ЦВЕТА", ""),
 ("Подтверждено", "Данные взяты из выгрузки консоли Veeam: видно, что копии реально создаются и обновляются."),
 ("Проблема", "Подтверждено, что есть проблема: копий нет, задание выключено/сломано либо падает в большинстве запусков."),
 ("Не проверено", "Данных в выгрузке нет либо объект копируется другим заданием, и это задание нужно проверить отдельно."),
 ("Красная строка целиком", "Риск критичный: либо копий нет больше 30 дней, либо задание не работает, либо объект защищён единственной копией без резерва."),
 ("Оранжевая строка целиком", "Риск высокий: копии нет 15–30 дней либо задание нестабильно (успех 35–75%)."),
 ("Жёлтая ячейка «Риск»", "Риск средний: копии нет 8–14 дней."),
 ("Зелёная ячейка «Риск»", "Риск низкий: копии свежие, задание отрабатывает стабильно."),
 ("НЕ НАЙДЕНО НИ В ОДНОМ VEEAM", "Хост из реестра аудита не встречается ни в заданиях, ни в точках. Если хост физический — не копируется ничем."),
 ("Не применимо: копирование файлов", "Объект — сетевая шара. Для неё физика копирования другая (файлы, а не точки), поэтому отсутствие точек нормально.")]
r = 3
for k, v in LEG:
    if v == "" and k:
        ws.cell(row=r, column=1, value=k).font = Font(bold=True, size=11, color=NAVY)
    else:
        c1 = ws.cell(row=r, column=1, value=k); c1.font = Font(bold=True, size=10)
        c1.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=r, column=2, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    r += 1
widths(ws, {1: 40, 2: 112})

# ---------------------------------------------------------------- 14 План
plan = [
 ["Освободить место на диске G: консоли «omicron» (репозиторий sv3)", "RDP на 192.168.160.14: удалить старые цепочки, расширить том или перенести часть копий на H:\\ (свободно 4358 ГБ)",
  "На G: свободно больше 2 ТБ; задания sv3 Services, sv3 BackConf, netboxv2 идут без ошибок «нет места на диске»", "Критичный", "Не сделано",
  f"Это причина {n_disk} падений в логах. Пока место не освобождено, остальные пункты по этой консоли не имеют смысла"],
 ["Освободить или заменить диск K: консоли «db» (репозиторий k3s)", "K: = 699,94 ГБ из 699,94, свободно 0. Расширить том, перенести репозиторий или удалить устаревшие точки",
  "На K: есть свободное место, задание k3s включено и отрабатывает", "Критичный", "Не сделано",
  "Задание k3s выключено вручную из-за этого диска; единственная точка K3S node4 — 20.03.2026"],
 ["Починить задание DBnode2 (базы данных биллинга на нодах node2)", "Задания нет в конфигурации консоли «omicron». Восстановить из резервной копии конфигурации Veeam либо создать заново на db-*-node2",
  "Задание есть, идут успешные полные бэкапы db-flash/omiplat/rocket/rtc/utk-node2", "Критичный", "Не сделано",
  f"{n_node2} баз данных без копии с 27.06.2026 (101 день), 32 запуска подряд с ошибкой"],
 ["Разобраться с заданием sv3 Exchange (Exchange, 5 доменов)", "Консоль Veeam → sv3 Exchange → последние сессии → Session Details: искать «нет места на диске» на H:\\ и ошибки агента",
  "Есть хотя бы одна успешная сессия со всеми 5 доменами", "Критичный", "Не сделано",
  "0 успешных из 100, 78 с предупреждениями. Вторая консоль Exchange не копирует — риск единоличный и не перекрыт"],
 ["Вернуть в копирование vault.omicron и gitlab.omicron", "Консоль Veeam → sv3 Services → Edit → список ВМ; vCenter → состояние ВМ; снять статус «unavailable»",
  "В логах нет строк «is unavailable», у обеих ВМ появляются точки", "Критичный", "Не сделано",
  "У vault.omicron точек нет вообще (только rsync-зеркало на backonf). У gitlab.omicron один полный бэкап от 05.09.2026 — исходники GitLab не защищены"],
 ["Решить с 4 заданиями консоли «db», которые никогда не работали", "ex-flash, NetboxSingleTime, singleopnsense, test — включены, но 0 запусков",
  "Либо отрабатывают успешно, либо удалены как ненужные дубликаты", "Высокий", "Не сделано",
  "NetboxSingleTime дублирует объект Netbox из задания Monitoring, singleopnsense — объект OPNSense из Access. Мусор в конфигурации вводит в заблуждение при разборе"],
 ["Увеличить частоту резервного копирования баз данных биллинга", "Консоль «omicron» → DBnode1 и DBnode3: перевести на ежедневное или еженедельное полное + ежедневные инкременты; подключить транзакционные логи через SQL-плагин",
  "У баз данных биллинга есть точки не старше 1 дня", "Высокий", "Не сделано",
  "Сейчас полный бэкап только 1-го числа месяца при хранении 14 дней — реальное окно защиты 2 недели в месяце"],
 ["Закрыть резервное копирование кластера Kubernetes", "Консоль «omicron» → задание K3S копирует только node3; консоль «db» → задание k3s выключено, только node4. Ноды node1 и node2 не копируются",
  "Все 4 ноды (161.110/120/130/140) в заданиях либо кворум и etcd защищены отдельно", "Высокий", "Не сделано",
  "Плюс настроить backup target для Longhorn: реплики томов не являются резервной копией, mail-PVC 800 ГБ не защищён"],
 ["Проверить дублирование между консолями", f"{n_dup} объектов копируются в обоих Veeam одновременно",
  "Для каждой пары принято решение: оставить в обоих (разные носители) или отключить в одном", "Средний", "Не сделано",
  "Фактически это единственная «вторая копия», но обе консоли в одном ЦО — отказоустойчивости это не даёт"],
 ["Настроить резервную копию вне площадки", "11 репозиториев, все — локальные папки на серверах 192.168.160.14 и 192.168.160.16, оба в одном ЦО",
  "Хотя бы один репозиторий или реплика в другом ЦО / у внешнего провайдера", "Высокий", "Не сделано",
  "Потеря обоих серверов или всего сегмента 160.0.0.0/24 = полная потеря всех точек"],
 ["Включить иммутабельность репозиториев", "Enterprise Plus → Backup Infrastructure → Repositories → Enable immutability (или Object Lock на хранилище)",
  "Репозитории защищены от удаления и перезаписи точек", "Средний", "Не сделано",
  "Лицензия EnterprisePlus на обеих консолях, действительна до 31.12.2035 — функция доступна"],
 ["Покрыть физические серверы", f"Ни на одной консоли нет заданий типа Physical Machine / Entire Computer; из {len(uncovered)} хостов реестра не найдено {n_unfound}",
  "Либо добавлены задания для физики, либо риск официально принят и записан в матрицу", "Критичный", "Не сделано",
  "Большинство хостов парка — Debian-физика вне vSphere. Сейчас они не защищены ничем"],
 ["Провести реальное восстановление", "Instant VM Recovery в изолированную сеть: ns1 (PowerDNS), Bitrix_2, erp.omicron, db-flash-node1, 1CSERVER_FLASH",
  "ВМ поднимается, приложение стартует, зафиксировано время процедуры", "Высокий", "Не сделано",
  "Ни одного теста восстановления не зафиксировано ни на одной консоли за всю историю"],
 ["Добавить резервную копию vCenter 192.168.160.202 (версия 6.7, вне поддержки)", "Объект vCenterMS есть в sv3 Services, но задание падает в 94% запусков; встроенного бэкапа vCenter в Veeam 12 нет",
  "Есть свежая точка по vCenter appliance", "Высокий", "Не сделано", "vCenter 6.7 вне технической поддержки с ноября 2023 г."],
 ["Починить выгрузку данных для аудита", "В файле размеров бэкапов все значения пустые; привязка задание→репозиторий падает на CBackupJob.GetTargetStorages",
  "В выгрузке видно, куда пишет каждое задание и сколько занимает", "Низкий", "Не сделано",
  "Без этого невозможно планировать место в репозиториях"],
 ["Проверить процессы вне Veeam (backonf → RegRu)", "backonf: cat /home/backup/send_bkp_to_regru.sh; ls -la /backup/erp (ошибка retention: find -mtime без -type f)",
  "Понятно что копируется, копия свежая (менее 24 ч), retention реально чистит старые каталоги", "Высокий", "Не сделано",
  "Из прежней матрицы аудита; это единственный подтверждённый элемент offsite во всей схеме"],
]
simple("14_План", "ПЛАН ДЕЙСТВИЙ ПО РЕЗУЛЬТАТАМ АУДИТА",
       ["№","Что сделать","Где и как","Критерий выполнения (как проверить)","Приоритет","Статус","Почему это важно"],
       [[i] + p for i, p in enumerate(plan, 1)],
       {1:5,2:50,3:64,4:46,5:12,6:14,7:74},
       note="Пункты выведены из выгрузок обеих консолей; последний — из прежней матрицы аудита (процессы вне Veeam).")

# порядок листов: матрица первой
order = ["01_Матрица","02_Сводка","03_Задания","04_Покрытие","05_Простои","06_Две_консоли",
         "07_Точки","08_Сессии","09_Ошибки_сводка","10_Ошибки","11_Хранилища","12_Не_покрыто",
         "13_Справочник","14_План"]
wb._sheets = [wb[n] for n in order]
if "Sheet" in wb.sheetnames: del wb["Sheet"]
wb.save(OUT)
print("OK ->", OUT)
print(f"листов {len(wb.sheetnames)}  консолей {len(A)}  заданий {len(jobrows)}  объектов {len(coverage)}  "
      f"дублей {n_dup}  простоев {len(idle)}  не найдено хостов {n_unfound}/{len(uncovered)}")