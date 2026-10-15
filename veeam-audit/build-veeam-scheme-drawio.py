#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерирует схему резервного копирования Veeam в формате draw.io (.drawio)
по фактическим данным выгрузок консолей (VeeamDump_*).
"""
import csv, pathlib, collections, datetime

BASE = pathlib.Path(__file__).resolve().parent      # все файлы лежат рядом со скриптом
OUT  = BASE / "Схема_бэкапов_Veeam.drawio"

def rd(p, n):
    f = p / n
    return list(csv.DictReader(open(f, encoding="utf-8-sig"))) if f.exists() else []
def dt(s):
    for f in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try: return datetime.datetime.strptime((s or "").strip(), f)
        except (ValueError, TypeError): pass
    return None

SRV = {"VeeamDump_omicron": ("Veeam #1 «omicron»", "192.168.160.14", "omicron"),
       "VeeamDump_db":      ("Veeam #2 «db»",      "192.168.160.16", "db")}
DATA = {}
for d in sorted(BASE.glob("VeeamDump_*")):
    if not d.is_dir(): continue
    lbl, ip, key = SRV.get(d.name, (d.name, "?", d.name))
    jobs, jstats = rd(d, "03-Jobs.csv"), rd(d, "08-JobStats.csv")
    st = {r["Задание"]: r for r in jstats}
    items = []
    for j in jobs:
        s = st.get(j["Задание"], {})
        n_all = int(s.get("Всего сессий") or 0); n_ok = int(s.get("Успешно") or 0)
        on = j["Включено"] == "True"
        pct = (n_ok / n_all * 100) if n_all else 0
        items.append(dict(name=j["Задание"], n=int(j["Объектов"] or 0), on=on,
                          ok=n_ok, all=n_all, pct=pct,
                          sched=(j["Расписание"] or "").strip(), repo=""))
    DATA[key] = dict(label=lbl, ip=ip, jobs=items,
                     repos=[(r["Репозиторий"], r["Путь"], float(r["Объём (ГБ)"]), float(r["Свободно (ГБ)"]))
                            for r in rd(d, "04-Repositories.csv")])
# задание DBnode2 (есть в сессиях, нет в конфигурации)
DATA["omicron"]["jobs"].append(dict(name="DBnode2  ⚠ НЕТ В КОНСОЛИ", n=5, on=False, ok=0, all=32,
                                   pct=0.0, sched="ежемесячно, 1-е", repo=""))
DATA["omicron"]["jobs"].sort(key=lambda x: (x["pct"], x["name"]))
DATA["db"]["jobs"].sort(key=lambda x: (x["pct"], x["name"]))

# ------------------------------------------------------------------ XML
def esc(t): return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    .replace('"', "&quot;"))
CELLS = []
def node(id_, value, style, x, y, w, h, parent=None):
    p = f' parent="{parent}"' if parent else ""
    CELLS.append(f'<mxCell id="{id_}" value="{esc(value)}" style="{style}" vertex="1"{p}>'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
def edge(id_, value, sx, sy, sw, sh, ex, ey, ew, eh, style):
    CELLS.append(f'<mxCell id="{id_}" value="{esc(value)}" style="{style}" edge="1" parent="1">'
                 f'<mxGeometry relative="1" as="geometry"><mxPoint x="{sx}" y="{sy}" as="sourcePoint"/>'
                 f'<mxPoint x="{ex}" y="{ey}" as="targetPoint"/>'
                 f'<mxArray as="points"><mxPoint x="{(sx+ex)//2}" y="{(sy+ey)//2}"/></mxArray>'
                 f'<mxPoint as="offset" x="0" y="0"/>'
                 f'<mxPoint x="{sw}" y="{sh}" as="sourcePoint"/><mxPoint x="{ew}" y="{eh}" as="targetPoint"/>'
                 f'</mxGeometry></mxCell>')
def link(id_, value, sid, tid, style, ex=None, ey=None):
    """Связь между вершинами: sid -> tid."""
    extra = ""
    if ex is not None: extra = f' exitX="{ex}" exitY="0" entryX="0" entryY="0.5"'
    elif style.find("exitY") < 0: extra = ' exitX="1" exitY="0.5" entryX="0" entryY="0.5"'
    CELLS.append(f'<mxCell id="{id_}" value="{esc(value)}" style="{style}" edge="1" parent="1" source="{sid}" target="{tid}">'
                 f'<mxGeometry relative="1" as="geometry"/></mxCell>')

S_TITLE  = "text;html=1;fontSize=26;fontStyle=1;fontColor=#1F3864;align=left;verticalAlign=middle;"
S_SUB    = "text;html=1;fontSize=13;fontColor=#555555;align=left;"
S_HDR    = "rounded=1;whiteSpace=wrap;html=1;fillColor=#1F3864;fontColor=#FFFFFF;fontSize=14;fontStyle=1;align=center;"
S_SRC    = "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=12;align=left;spacingLeft=10;"
S_SRCBAD = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;strokeWidth=2;fontSize=12;align=left;spacingLeft=10;fontColor=#9C0006;"
S_CONS   = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;strokeWidth=2;verticalAlign=top;spacingTop=8;fontSize=14;fontStyle=1;fontColor=#1F3864;"
S_OK     = "rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;align=left;spacingLeft=8;"
S_WARN   = "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;align=left;spacingLeft=8;"
S_BAD    = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;strokeWidth=2;fontSize=11;align=left;spacingLeft=8;fontColor=#9C0006;"
S_REPO_OK  = "rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;align=left;spacingLeft=8;"
S_REPO_BAD = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;strokeWidth=2;fontSize=11;align=left;spacingLeft=8;fontColor=#9C0006;"
S_REPO_WARN= "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;align=left;spacingLeft=8;"
S_OFF    = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;strokeWidth=3;dashed=1;fontSize=13;fontColor=#9C0006;align=center;fontStyle=1;"
S_PROB   = "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;align=left;verticalAlign=top;spacing=8;spacingLeft=6;"
S_LEG    = "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#999999;fontSize=11;align=left;verticalAlign=top;spacing=8;"
S_EDGE   = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth=2;endArrow=blockThin;endFill=1;fontSize=11;labelBackgroundColor=#ffffff;"
S_EDGED  = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;dashed=1;strokeWidth=3;strokeColor=#b85450;endArrow=blockThin;endFill=1;fontSize=11;fontColor=#9C0006;labelBackgroundColor=#ffffff;"

node("t1", "РЕЗЕРВНОЕ КОПИРОВАНИЙ VEEAM — СХЕМА ДВИЖЕНИЯ КОПИЙ", S_TITLE, 40, 16, 1500, 32)
node("t2", "по данным выгрузок консолей от 07.10.2026 · 2 сервера Veeam B&R 12.1 Enterprise Plus · 27 заданий · 102 объекта · 1347 запусков (66% успеха)",
     S_SUB, 40, 50, 1500, 22)

# ---------------- ИСТОЧНИКИ
node("h_src", "ИСТОЧНИКИ ДАННЫХ", S_HDR, 40, 110, 300, 34)
node("vc", "vCenter 192.168.160.202\nVMware vSphere 6.7 — вне поддержки\n(тех. поддержка закончилась в 2023)", S_SRC, 40, 156, 300, 66)
node("esxi", "ESXi-узлы (все добавлены в Veeam)\nnode10…node50 · dbnode1 · dbnode2 · dbnode3", S_SRC, 40, 236, 300, 60)
node("nas", "NAS-шара E:\\ на 192.168.160.62\n(копируется на уровне файлов)", S_SRC, 40, 310, 300, 56)
node("phys", "ФИЗИЧЕСКИЕ СЕРВЕРЫ — 43 из 77 хостов\nне попали ни в одну консоль Veeam\nЗаданий типа Physical Machine нет →\nэти хосты не копирует НИЧТО", S_SRCBAD, 40, 380, 300, 100)
node("problem_vm", "Проблемные ВМ внутри задания sv3 Services:\nvault.omicron — копий нет вообще\ngitlab.omicron — одна копия от 05.09.2026", S_SRCBAD, 40, 494, 300, 76)

# ---------------- КОНСОЛИ
def console(key, x, w, colhdr):
    d = DATA[key]
    jobs = d["jobs"]; rowh = 34
    h = 84 + len(jobs) * rowh + 14
    node(f"c_{key}", f"{d['label']}   {d['ip']}\nПрокси резервного копирования: этот же сервер · "
                      f"лицензия Enterprise Plus до 31.12.2035", S_CONS, x, 110, w, h)
    y = 74
    for i, j in enumerate(jobs):
        stl = S_OK if (j["pct"] >= 90 and j["ok"]) else (S_WARN if j["pct"] >= 35 else S_BAD)
        if not j["on"]: stl = S_BAD
        if j["all"] == 0: stl = S_BAD
        cnt = f"{j['ok']}/{j['all']}" if j["all"] else "нет запусков"
        state = ("✓ работает" if (j["pct"] >= 90 and j["ok"]) else
                 "⚠ нестабильно" if j["pct"] >= 35 else
                 ("✖ выключено" if not j["on"] else "✖ не работает"))
        val = f"{j['name']}  ·  {j['n']} об.  ·  {cnt}  ·  {state}"
        node(f"j_{key}_{i}", val, stl, 12, y, w - 24, rowh - 3, parent=f"c_{key}")
        y += rowh
    return h

h1 = console("omicron", 400, 470, 0)
h2 = console("db", 940, 470, 0)

# ---------------- ХРАНИЛИЩА
def storages(key, x, y):
    d = DATA[key]
    node(f"h_rep_{key}", f"ХРАНИЛИЩА {d['label']}", S_HDR, x, y, 340, 32)
    yy = y + 40
    for i, (nm, path, vol, free) in enumerate(d["repos"]):
        used = vol - free
        pfree = free / vol if vol else 0
        stl = S_REPO_BAD if pfree < .15 else (S_REPO_WARN if pfree < .25 else S_REPO_OK)
        mark = "✖" if pfree < .15 else ("⚠" if pfree < .25 else "✓")
        val = f"{mark} {nm}   {path}\nзанято {used:,.0f} ГБ из {vol:,.0f} ГБ · свободно {pfree:.0%}".replace(",", " ")
        node(f"r_{key}_{i}", val, stl, x, yy, 340, 52)
        yy += 60
    return yy
y_end1 = storages("omicron", 1470, 110)
y_end2 = storages("db", 1470, y_end1 + 24)

# ---------------- OFFSITE И РИСКИ
node("off", "OFFSITE — КОПИИ ЗА ПРЕДЕЛАМИ ПЛОЩАДКИ\nОТСУТСТВУЕТ\nВсе 11 хранилищ — локальные папки (WinLocal)\nна двух серверах в одном сегменте 160.0.0.0/24.\nДубли между двумя Veeam — единственный резерв,\nно он в том же ЦО.", S_OFF, 1470, y_end2 + 24, 340, 120)

node("risk_h", "ЧТО ТРЕБУЕТ ИСПРАВЛЕНИЯ (в порядке критичности)", S_HDR, 1870, 110, 470, 32)
node("risk", """1. ДИСК G:\\ — 9005 ГБ из 9999 (90% занято). Из-за нехватки места падают 4 задания: sv3 Services, sv3 BackConf, netboxv2, sv3 Exchange.
2. ДИСК K: — 699 ГБ из 699 (100%, свободно 0). Задание k3s выключено администратором; у узла node4 одна копия от 20.03.2026.
3. ЗАДАНИЕ DBnode2 ОТСУТСТВУЕТ в консоли «omicron» — базы биллинга на нодах node2 без копии с 27.06.2026 (101 день), 32 запуска подряд с ошибкой.
4. sv3 EXCHANGE — 0 успешных запусков из 100 (78 с предупреждениями, 22 с ошибкой). Вторая консоль Exchange не копирует вовсе.
5. ВМ vault.omicron и gitlab.omicron — статус «unavailable», пропускаются из обработки 36 раз.
6. KUBERNETES: копируется только node3; node1 и node2 — нигде. Для Longhorn (mail-PVC 800 ГБ) backup target не настроен, реплики не являются резервной копией.
7. НИ ОДНОГО ТЕСТА ВОССТАНОВЛЕНИЯ за всю историю обеих консолей — работоспособность копий не подтверждена.
8. 4 задания второй консоли ни разу не отработали: ex-flash, NetboxSingleTime, singleopnsense, test (первые два — дубликаты действующих заданий).""",
     S_PROB, 1870, 150, 470, 300)

node("good_h", "ЧТО РАБОТАЕТ ШТАТНО", S_HDR, 1870, 466, 470, 32)
node("good", """Консоль «db» (192.168.160.16): 12 заданий, 771 запуск, 0 ошибок.

Защищены ежедневно:
• Биллинг-ядра bg-core (5 нод) — 83/83 успешных
• RADIUS bg-radius (5 нод) — 83/83
• ProxySQL (5 нод) — 83/83
• Домены Active Directory (7) — 83/83
• 1С предприятие (14 объектов) — 59/59
• Колл-центры (10 объектов) — 48/48
• Доступ и VPN: msVPN, NPS, MFA, OPNsense, WireGuard — 24/24
• Мониторинг: Ansible, NetBox, oms, zabbix, SV1 — 35/35
• TACACS+ — 83/83, репликация WireGuard — 83/83
• Резервные копии конфигов — 24/24, NAS-шара E:\\ — 83/83

Базы биллинга node1 — 13/13 (100%), node3 — 12/13 (92%),
но срок хранения 14 дней при фактическом запуске раз в неделю."""
     , "rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;align=left;verticalAlign=top;spacing=8;",
     1870, 506, 470, 320)

# ---------------- ЛЕГЕНДА
node("leg_h", "УСЛОВНЫЕ ОБОЗНАЧЕНИЯ", S_HDR, 40, 610, 300, 32)
node("leg", "✓ зелёный — задание отрабатывает стабильно\n"
            "⚠ оранжевый — нестабильно (успех 35–75%)\n"
            "✖ красный — не работает / выключено / нет места\n"
            "▬ пунктир красный — отсутствующий элемент (offsite)\n\n"
            "Числа вида 83/83 = успешных запусков из общего числа.\n"
            "«об.» = сколько объектов в задании.\n"
            "Хранилище: занято/объём диска и доля свободного места.\n\n"
            "Стрелка сплошная — поток копий данных.\n"
            "Пунктир красный — того, что должно быть, но нет.",
     S_LEG, 40, 650, 300, 200)

node("sum_h", "ИТОГИ", S_HDR, 40, 1030, 1940, 32)
node("sum", """Всего: 27 заданий на двух серверах · 1347 запусков за историю: 891 успешных (66%), 160 с предупреждениями (12%), 296 с ошибкой (22%).
Объектов под защитой: 145 записей (102 уникальных) · 42 объекта копируются в обеих конслях (вторая копия, но в том же ЦО) · 57 только в одной.
Без актуальной копии: 40 объектов, из них 32 — без копии более 180 дней.

РИСК ДЛЯ КОМПАНИИ: потеря сегмента 160.0.0.0/24 = потеря всех копий, потому что offsite не настроен ни на одной консоли.
Затраты на устранение первых шести пунктов — несколько часов работы и свободное место на дисках.""",
     "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1F3864;strokeWidth=2;fontSize=12;align=left;verticalAlign=top;spacing=10;",
     40, 1070, 1940, 110)

# ---------------- СВЯЗИ
link("e_vc_c1", "запросы копирования (vSphere API)", "vc", "c_omicron", S_EDGE)
link("e_vc_c2", "", "vc", "c_db", S_EDGE)
link("e_esxi_c1", "прямое подключение к ESXi", "esxi", "c_omicron", S_EDGE)
link("e_nas_c2", "чтение файлов шары", "nas", "c_db", S_EDGE)
node("xmark", "✖  копирования нет →", "text;html=1;fontSize=16;fontColor=#b85450;fontStyle=1;align=left;verticalAlign=top;", 40, 578, 300, 24)

link("e_c1_r1", "поток копий в хранилища «omicron»", "c_omicron", "h_rep_omicron", S_EDGE + "strokeColor=#b85450;")
link("e_c2_r2", "поток копий в хранилища «db»", "c_db", "h_rep_db", S_EDGE + "strokeColor=#6c8ebf;")
link("e_r1_off", "КОПИЙ ВНЕ ПЛОЩАДКИ НЕТ", "r_omicron_1", "off", S_EDGED)
link("e_r2_off", "", "r_db_6", "off", S_EDGED)

# ---------------- СБОРКА ФАЙЛА
xml = ('<mxfile host="app.diagrams.net" modified="2026-10-07T00:00:00.000Z" agent="audit" version="24.0.0" type="device">'
       '<diagram id="veeam-backups" name="Схема бэкапов Veeam">'
       '<mxGraphModel dx="2400" dy="1400" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
       'arrows="1" fold="1" page="1" pageScale="1" pageWidth="2400" pageHeight="1250" math="0" shadow="0">'
       '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(CELLS) +
       '</root></mxGraphModel></diagram></mxfile>')
OUT.write_text(xml, encoding="utf-8")
print("OK ->", OUT, len(xml), "байт")