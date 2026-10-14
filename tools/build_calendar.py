#!/usr/bin/env python3
"""Génère calendrier.html (A4 paysage, noir et blanc) pour l'année scolaire."""
import datetime as dt, subprocess, urllib.request, re
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START_YEAR = 2026
ICS = "https://calendar.google.com/calendar/ical/ape.leauvive%40gmail.com/public/basic.ics"
PAGE = "https://www.volent.fr/calendrier-ape/"
TZ = ZoneInfo("Europe/Paris")

MOIS = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
JOURS = ["L","M","M","J","V","S","D"]

# Vacances scolaires zone A (académie de Lyon), 2026-2027
VACANCES = [
    (dt.date(2026,10,17), dt.date(2026,11,1)),
    (dt.date(2026,12,19), dt.date(2027,1,3)),
    (dt.date(2027,2,13),  dt.date(2027,2,28)),
    (dt.date(2027,4,10),  dt.date(2027,4,25)),
    (dt.date(2027,7,3),   dt.date(2027,8,31)),
]
FERIES = {
    dt.date(2026,11,1): "Toussaint", dt.date(2026,11,11): "Armistice",
    dt.date(2026,12,25): "Noël", dt.date(2027,1,1): "Jour de l'an",
    dt.date(2027,3,29): "Pâques", dt.date(2027,5,1): "Fête du Travail",
    dt.date(2027,5,6): "Ascension", dt.date(2027,5,8): "Victoire 1945",
    dt.date(2027,5,17): "Pentecôte", dt.date(2027,7,14): "Fête nationale",
    dt.date(2027,8,15): "Assomption",
}
COURT = {"Café des parents": "Café parents"}  # libellés raccourcis dans les cases
SPECIAUX = {dt.date(2026,9,1): "Rentrée"}
# Emoji par événement (mot-clé en minuscules -> emoji). ★ par défaut.
EMOJIS = [("pizz", "🍕"), ("noël", "🎄"), ("carnaval", "🎭"), ("fête", "🎉"),
          ("grenier", "🧸"), ("café", "☕"), ("halloween", "🎃")]

def emoji(summary):
    if summary and not summary[0].isalnum():  # titre commençant déjà par un emoji
        return ""
    low = summary.lower()
    return next((e for k, e in EMOJIS if k in low), "★") + " "

def events():
    raw = urllib.request.urlopen(ICS).read().decode()
    raw = re.sub(r"\r?\n[ \t]", "", raw)
    out = {}
    for block in raw.split("BEGIN:VEVENT")[1:]:
        f = {}
        for line in block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f.setdefault(k.split(";")[0], (k, v))
        k, v = f["DTSTART"]
        summary = f.get("SUMMARY", ("", ""))[1].replace("\\,", ",").replace("\\;", ";")
        if "VALUE=DATE" in k or len(v) == 8:
            d, time = dt.datetime.strptime(v[:8], "%Y%m%d").date(), ""
        else:
            t = dt.datetime.strptime(v.rstrip("Z"), "%Y%m%dT%H%M%S")
            t = t.replace(tzinfo=dt.timezone.utc).astimezone(TZ) if v.endswith("Z") else t
            d, time = t.date(), f"{t.hour}h{t.minute:02d}".replace("h00", "h")
        out.setdefault(d, []).append((time, summary))
    return out

def in_vacances(d):
    return any(a <= d <= b for a, b in VACANCES)

def main():
    ev = events()
    months = [(START_YEAR + (m >= 1 and i >= 4), (8 + i) % 12 + 1) for i, m in enumerate(range(12))]
    months = [(START_YEAR if i < 4 else START_YEAR + 1, (8 + i) % 12 + 1) for i in range(12)]
    qr = subprocess.run(["qrencode", "-t", "SVG", "-m", "0", "--svg-path", "-l", "M", "-o", "-", PAGE],
                        capture_output=True, text=True, check=True).stdout
    qr = qr[qr.index("<svg"):]

    rows = []
    for day in range(1, 32):
        cells = []
        for y, m in months:
            try:
                d = dt.date(y, m, day)
            except ValueError:
                cells.append('<td class="none"></td>'); continue
            cls = []
            if d.weekday() >= 5: cls.append("we")
            if in_vacances(d): cls.append("vac")
            if d in FERIES: cls.append("ferie")
            label = ""
            if d in SPECIAUX and d not in ev:
                label = f'<span class="special">{SPECIAUX[d]}</span> '
            if d in ev:
                cls.append("event")
                label += "".join(f'<span class="ev">{emoji(s)}{COURT.get(s, s)}</span>' for t, s in ev[d])
            elif d in FERIES:
                label += f'<span class="fer">{FERIES[d]}</span>'
            cells.append(f'<td class="{" ".join(cls)}"><div class="c"><span class="n"><b>{day}</b><i>{JOURS[d.weekday()]}</i></span>{f'<span class="lbl">{label}</span>' if label else ""}</div></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")

    JS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
    first, last = dt.date(*months[0], 1), dt.date(months[-1][0], months[-1][1], 31)
    items = []
    for d in sorted(k for k in ev if first <= k <= last):
        for t, s_ in ev[d]:
            items.append(f'<li><span class="em">{emoji(s_)}</span><b>{s_}</b> — {JS[d.weekday()]} {d.day if d.day > 1 else "1er"} {MOIS[d.month-1].lower()}{" à " + t if t else ""}</li>')
    evlist = "".join(items)
    head = "".join(f"<th>{MOIS[m-1]}<small>{y}</small></th>" for y, m in months)
    common = dict(head=head, rows="\n".join(rows), qr=qr, evlist=evlist, y1=START_YEAR, y2=START_YEAR + 1,
                  page=PAGE.replace("https://", "").rstrip("/"))
    variants = {
        "calendrier.html": dict(logo="logo-nb.png", extra_css=""),
        "calendrier-couleur.html": dict(logo="logo.png", extra_css=COULEUR_CSS),
    }
    for name, v in variants.items():
        (ROOT / name).write_text(TEMPLATE.format(**common, **v))
        print(name, "écrit")

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<title>Calendrier de l'APE {y1}-{y2}</title>
<link rel="icon" href="logo.png">
<style>
  @page {{ size: A4 landscape; margin: 7mm; }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  html, body {{ margin: 0; background: #fff; color: #000; }}
  body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }}
  .sheet {{ width: 283mm; height: 196mm; margin: 0 auto; display: flex; flex-direction: column; }}
  @media screen {{ body {{ background: #ccc; padding: 10mm 0; }} .sheet {{ background: #fff; padding: 7mm; width: 297mm; height: 210mm; box-shadow: 0 2px 12px rgba(0,0,0,.3); }} }}
  header {{ display: flex; align-items: center; gap: 5mm; height: 27mm; margin-bottom: 2mm; }}
  header img {{ height: 25mm; }}
  header .title {{ flex: 1; }}
  h1 {{ margin: 0; font-size: 22pt; letter-spacing: -.02em; line-height: 1.05; }}
  header p {{ margin: 1.5mm 0 0; font-size: 9.5pt; }}
  .qr {{ display: flex; align-items: center; gap: 4mm; border: .8mm solid #000; border-radius: 3mm; padding: 1.5mm 4mm 1.5mm 1.5mm; height: 27mm; }}
  .qr svg {{ width: 24mm; height: 24mm; }}
  .qr div {{ font-size: 8.5pt; line-height: 1.2; width: 66mm; }}
  .qr strong {{ font-size: 12pt; display: block; margin-bottom: .6mm; }}
  .qr small {{ display: block; margin-top: 1.2mm; font-size: 7.5pt; }}
  table {{ flex: 1; width: 100%; border-collapse: collapse; table-layout: fixed; }}
  th {{ font-size: 9pt; text-transform: uppercase; letter-spacing: .04em; background: #000; color: #fff; padding: 1mm 0; border: .25mm solid #000; }}
  th small {{ display: block; font-size: 6.5pt; font-weight: normal; letter-spacing: 0; }}
  td {{ border: .2mm solid #000; padding: 0 .6mm; font-size: 6.4pt; height: 4.35mm; overflow: hidden; line-height: 1; }}
  .c {{ display: flex; align-items: center; gap: .6mm; height: 4.05mm; overflow: hidden; }}
  .n {{ flex: none; white-space: nowrap; }}
  .lbl {{ flex: 1; min-width: 0; font-size: 5.3pt; line-height: .98; padding: .15mm 0; white-space: normal; overflow: hidden; max-height: 4.05mm; }}
  td b {{ display: inline-block; width: 3.2mm; text-align: right; font-size: 6.8pt; }}
  td i {{ display: inline-block; width: 2.2mm; font-style: normal; margin-left: .5mm; color: #333; }}
  td.we {{ background: #d9d9d9; }}
  td.vac {{ background: repeating-linear-gradient(135deg, #fff 0 .55mm, #9a9a9a .55mm .8mm); }}
  td.we.vac {{ background: repeating-linear-gradient(135deg, #d9d9d9 0 .55mm, #7a7a7a .55mm .8mm); }}
  td.none {{ background: #000; }}
  td.ferie b, td.ferie i {{ text-decoration: underline; font-weight: bold; color: #000; }}
  .fer {{ font-style: italic; background: #fff; padding: 0 .3mm; }}
  .special {{ font-weight: bold; text-transform: uppercase; background: #fff; padding: 0 .3mm; }}
  td.event {{ outline: .55mm solid #000; outline-offset: -.55mm; }}
  .ev {{ font-weight: bold; padding: 0; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
  .events {{ display: flex; align-items: baseline; gap: 3mm; margin-top: 2mm; border: .4mm solid #000; border-radius: 2mm; padding: 1.5mm 3mm; font-size: 8.5pt; }}
  .events h2 {{ margin: 0; font-size: 9pt; white-space: nowrap; text-transform: uppercase; }}
  .events ul {{ margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: .8mm 5mm; }}
  .events .em {{ margin-right: .8mm; }}
  footer {{ display: flex; gap: 6mm; align-items: center; font-size: 7.5pt; margin-top: 2mm; }}
  .sw {{ display: inline-block; width: 6mm; height: 3mm; border: .2mm solid #000; vertical-align: middle; margin-right: 1mm; }}
  td.vac .ev, td.vac b, td.vac i {{ background: #fff; padding: 0 .3mm; }}
  .sw-ev {{ outline: .55mm solid #000; outline-offset: -.55mm; }}
  .sw-vac {{ background: repeating-linear-gradient(135deg, #fff 0 .55mm, #9a9a9a .55mm .8mm); }}
  .sw-we {{ background: #d9d9d9; }}
  footer > span {{ white-space: nowrap; }}
  footer .right {{ margin-left: auto; }}
{extra_css}
</style>
</head>
<body>
<div class="sheet">
  <header>
    <img src="{logo}" alt="Logo de l'APE École L'Eau Vive Éveux">
    <div class="title">
      <h1>Calendrier de l'APE<br>Année scolaire {y1}-{y2}</h1>
      <p>École L'Eau Vive · Éveux — les événements de l'association des parents d'élèves</p>
    </div>
    <div class="qr">{qr}<div><strong>📲 Abonnez-vous&nbsp;!</strong>Scannez ce QR code pour ajouter le calendrier de l'APE à votre agenda (Google Agenda ou Calendrier de l'iPhone) et recevoir les mises à jour.<small>🔒 Votre agenda reste privé&nbsp;: l'APE ne le voit pas.</small></div></div>
  </header>
  <table>
    <thead><tr>{head}</tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <section class="events"><h2>Les rendez-vous de l'APE</h2><ul>{evlist}</ul></section>
  <footer>
    <span><span class="sw sw-ev"></span><b>Événement de l'APE</b></span>
    <span><span class="sw sw-vac"></span>Vacances scolaires zone A (Lyon)</span>
    <span><span class="sw sw-we"></span>Week-end</span>
    <span><b><u>1</u></b> Jour férié</span>
    <span>Rentrée : mardi 1er septembre {y1}</span>
    <span class="right">{page}</span>
  </footer>
</div>
</body>
</html>
"""

# Version couleur : teintes du logo, mais foncées / motifs conservés pour rester
# lisible si elle est imprimée en noir et blanc.
COULEUR_CSS = """
  th { background: #0b5394; border-color: #0b5394; }
  th:nth-child(3n+1) { background: #b0124f; border-color: #b0124f; }
  th:nth-child(3n+2) { background: #3f7a0e; border-color: #3f7a0e; }
  h1 { color: #b0124f; }
  td.we, .sw-we { background: #cfe2f3; }
  td.vac, .sw-vac { background: repeating-linear-gradient(135deg, #fff 0 .55mm, #6aa121 .55mm .8mm); }
  td.we.vac { background: repeating-linear-gradient(135deg, #cfe2f3 0 .55mm, #3f7a0e .55mm .8mm); }
  td.none { background: #0b5394; }
  td.event, .sw-ev { outline-color: #b0124f; outline-width: .7mm; outline-offset: -.7mm; }
  .ev { color: #b0124f; }
  td.ferie b, td.ferie i, .fer { color: #0b5394; }
  .qr { border-color: #0b5394; }
  .qr strong { color: #b0124f; }
  .qr { border-color: #0b5394; }
  .events { border-color: #b0124f; }
  .events h2 { color: #b0124f; }
"""

if __name__ == "__main__":
    main()
