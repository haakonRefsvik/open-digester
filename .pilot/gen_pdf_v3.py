#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a large multi-page pumpdriver datablad PDF for task_aquarack_v3."""
import textwrap
import fitz

OUT = "task_aquarack_v3/docs/pumpdriver-manual.pdf"

W, H = 595, 842
ML, MR, MT, MB = 72, 72, 72, 64
LH = 15.0
CW_CHARS = 92  # approx chars per line at 10pt helv in 451pt width

doc = fitz.open()
page = None
y = 0.0


def new_page():
    global page, y
    page = doc.new_page(width=W, height=H)
    y = MT
    return page


def emit(text, size=10, bold=False, font="helv", color=(0, 0, 0), lh=None):
    global y
    step = lh or (LH if size == 10 else size * 1.5)
    if y + step > H - MB:
        new_page()
    fn = font
    if bold:
        fn = "hebo" if font == "helv" else "cobo"
    page.insert_text((ML, y), text, fontsize=size, fontname=fn, color=color)
    y += step


def gap(n=1):
    global y
    y += LH * n


def heading(text, level=1):
    if level == 1:
        new_page()
        emit(text, size=16, bold=True)
        gap(1)
    elif level == 2:
        gap(1)
        emit(text, size=12, bold=True)
        gap(0.5)


def para(text, indent=False):
    wrapped = textwrap.wrap(text, width=CW_CHARS)
    for ln in wrapped:
        emit(("  " if indent else "") + ln)
    gap(0.4)


def table(rows, mono=True):
    # rows = list of strings already padded
    for r in rows:
        emit(r, font="cour", size=9, lh=12)
    gap(0.5)


# ---------------------------------------------------------------------------
# CONTENT
# ---------------------------------------------------------------------------

# 1. Cover
new_page()
gap(12)
emit("PM-4 / PM-4HF", size=30, bold=True)
emit("Peristaltisk doseringsdriver — 4 kanaler", size=16)
gap(2)
emit("Modbus RS-485 referanse og datablad", size=13)
gap(4)
emit("Revisjon D  ·  2026-05", size=12)
emit("AquaRack Systems AS  ·  Dok.nr. PM4-DS-D", size=10)
gap(10)
emit("Dette dokumentet er autoritativt for alle register-definisjoner,", size=10)
emit("enheter og tidskrav som gjelder PM-4-familien.", size=10)

# 2. Revision history
heading("1. Revisjonshistorikk", 1)
table([
    "Rev   Dato       Beskrivelse",
    "----  ---------  -------------------------------------------",
    "A     2023-11    Forste utgave.",
    "B     2024-06    La til termisk derating for PM-4HF.",
    "C     2025-01    Utvidet registerkart; klargjorde enheter.",
    "D     2026-05    Presiserte enhet for dosevolum (avsnitt 4.3).",
])

# 3. TOC
heading("2. Innholdsfortegnelse", 1)
for ln in [
    "1.  Revisjonshistorikk",
    "2.  Innholdsfortegnelse",
    "3.  Oversikt og egenskaper",
    "4.  Registerkart (Modbus)",
    "5.  Elektriske spesifikasjoner",
    "6.  Mekaniske mal",
    "7.  Tids- og syklus-krav",
    "8.  Termisk derating",
    "9.  Stromningskurver",
    "10. Kalibreringsprosedyre",
    "11. Applikasjonsnotater",
    "12. Samsvar og sikkerhet",
    "13. Bestillingsinformasjon",
    "14. Vanlige sporsmal (FAQ)",
    "15. Ordliste",
]:
    emit(ln)

# 3. Overview
heading("3. Oversikt og egenskaper", 1)
para("PM-4 er en 4-kanals peristaltisk doseringsdriver konstruert for "
     "presis tilsetning av næring og pH-justering i hydroponiske rack. Hver "
     "kanal driver én peristaltisk pumpe med stepmotor og innebygd "
     "posisjonstilbakemelding over Modbus RTU.")
para("PM-4HF er hoyvolum-varianten med kraftigere motor og hoyere "
     "maksimalt mot-trykk. Begge variantene deler samme registerkart, men "
     "skiller seg i elektriske grenser og termisk derating.")
para("Driveren kommuniserer over RS-485 (Modbus RTU), 8N1, standard 9600 "
     "eller 19200 baud, adresserbar 0x01..0x0F.")

# 4. Register map — CRITICAL FACT BURIED HERE
heading("4. Registerkart (Modbus)", 1)
heading("4.1 Adresserom", 2)
para("Alle registre er 16-bit, big-endian (Modbus-standard). Skriveregistre "
     "aksepterer verdi 0..65535; verdier utenfor gyldig omrade avvises med "
     "Modbus-unntak 0x03 (ulovlig dataverdi).")
table([
    "Adresse        | Lengde | Retning | Beskrivelse",
    "---------------+--------+---------+--------------------------------",
    "0x0010          | 16-bit | R       | Firmwareversjon driver",
    "0x0011          | 16-bit | R       | Serienummer (lav)",
    "0x0012          | 16-bit | R       | Serienummer (hoy)",
    "0x0013          | 16-bit | R       | Driftsstatus / feil-flagg",
    "0x0020..0x0023  | 16-bit | W       | Dosevolum pumpe 0..3",
    "0x0030..0x0033  | 16-bit | R       | Aktuell posisjon pumpe 0..3",
    "0x0040..0x0043  | 16-bit | R       | Stromningsrate pumpe 0..3",
    "0x0050          | 16-bit | R       | Temperatur driver (grader C)",
    "0x0051          | 16-bit | R       | Mot-trykk (hPa)",
    "0x0052          | 16-bit | R       | Væskeledningsevne (EC)",
])

heading("4.2 Enheter og opplosning", 2)
para("Hvert register har en fast enhet som firmware MAA respektere. Enhetene "
     "er IKKE utskiftbare mellom registre; et tall som er korrekt i ett "
     "register er feil i et annet.")
table([
    "Register       | Enhet                 | Merknad",
    "---------------+-----------------------+--------------------------------",
    "0x0010         | dimensjonslos         | Major.Minor som 0xMMmm",
    "0x0020..0x0023 | 0,1 milliliter        | se avsnitt 4.3 (KRITISK)",
    "0x0030..0x0033 | trinn (1/256 omdr.)   | 256 trinn per omdreining",
    "0x0040..0x0043 | 0,01 L/min            | momentan stromningsrate",
    "0x0050         | 0,1 grader C          | to-komplement for negative",
    "0x0051         | 1 hPa                 | 0..4000 hPa",
    "0x0052         | 0,001 S/m             | EC i Siemens per meter",
])

heading("4.3 Enhet for dosevolum (viktig)", 2)
para("DOSEVOLUM-REGISTERET ER I 0,1 MILLILITER (en tiendedels ml).")
para("Eksempel: onsket dose 12,5 ml -> skriv verdi 125. Firmware ma derfor "
     "gange onsket ml med 10 for registeret skrives.")
para("Merknad om enhetsfeil: En vanlig feil er aa skrive volumet direkte i "
     "hele ml (faktor 1), som gir en dose som er 10x for liten. Verifiser "
     "alltid at firmware bruker faktor 10 mot dosevolum-registeret.")
para("For PM-4HF gjelder samme enhet (0,1 ml); hoyvolum-varianten endrer "
     "IKKE registerets opplosning, kun maksimalt volum per syklus.")

# 4.4 per-channel details (padding + a couple of distractors)
heading("4.4 Kanal-spesifikke detaljer", 2)
for ch in range(4):
    para(f"Kanal {ch} (pumpe {ch}): skrive-register 0x002{ch}, "
         f"posisjons-register 0x003{ch}, stromnings-register 0x004{ch}. "
         f"Alle kanaler bruker identisk enhet for dosevolum (0,1 ml).")

# 5. Electrical
heading("5. Elektriske spesifikasjoner", 1)
table([
    "Parameter              | PM-4        | PM-4HF      | Enhet",
    "-----------------------+-------------+-------------+-------",
    "Forsyningsspenning     | 12..24      | 12..48      | V DC",
    "Hvile-strom            | 40          | 90          | mA",
    "Topp-strom (per kanal) | 600         | 1400        | mA",
    "Stepmotor-opplosning   | 256         | 256         | trinn/omdr.",
    "RS-485-terminering     | 120         | 120         | ohm",
])

# 6. Mechanical
heading("6. Mekaniske mal", 1)
para("Bredde 82 mm, hoyde 56 mm, dybde 41 mm (PM-4) og 47 mm (PM-4HF). "
     "Monteringshull 4x M3 pa 68 mm x 44 mm senteravstand. Vekt 210 g "
     "(PM-4) og 260 g (PM-4HF).")

# 7. Timing
heading("7. Tids- og syklus-krav", 1)
para("Minste dose-syklus er 1 sekund per 0,1 ml ved nominell motorhastighet. "
     "Driveren bufferer skriveregistre i 100 ms etter Modbus-skriv; en "
     "etterfolgende lesing innen dette vinduet kan returnere gammel verdi.")
para("Anbefalt poll-intervall for status er 1 s; EC/pH-sensorer pa samme "
     "buss bor polls med maksimalt 2 Hz for a unnga kollisjon.")

# 8. Thermal derating (padding)
heading("8. Termisk derating", 1)
para("Maksimal tillatt omgivelsestemperatur avhenger av driftssyklus og "
     "forsyningsspenning. Verdiene under er retningsgivende.")
table([
    "Omgivelsestemp | Driftssyklus | Forsyning | Tillatt?",
    "---------------+--------------+-----------+---------",
    "-20..40 C      | 100 %        | 12 V      | Ja",
    "40..50 C       | 80 %         | 12 V      | Ja",
    "50..60 C       | 60 %         | 12 V      | Ja",
    "60..70 C       | 40 %         | 24 V      | Nei",
])
for t in range(-20, 71, 5):
    para(f"Ved {t} C er anbefalt maksimal kontinuerlig driftssyklus "
         f"{max(20, 100 - (t - 20))} % for PM-4 og "
         f"{max(15, 90 - (t - 20))} % for PM-4HF. Overstiges dette, "
         f"reduserer driveren automatisk motorstrommen med 10 % per 5 C.")

# 9. Flow curves (padding)
heading("9. Stromningskurver", 1)
para("Nominell stromningsrate som funksjon av slange-diameter og mot-trykk.")
table([
    "Slange (mm) | Mot-trykk (hPa) | Rate (ml/min) | Avvik",
    "------------+-----------------+---------------+-------",
    "1.6         | 0               | 12.0          | +/-2 %",
    "1.6         | 500             | 11.2          | +/-3 %",
    "2.4         | 0               | 28.0          | +/-2 %",
    "2.4         | 800             | 25.1          | +/-4 %",
])
for d in [1.6, 2.4, 3.2, 4.0]:
    for p in [0, 200, 400, 600, 800, 1000]:
        rate = round(d * d * 4.7 * (1 - p / 4000), 1)
        para(f"Slange {d} mm ved {p} hPa: nominell rate {rate} ml/min.")

# 10. Calibration (padding)
heading("10. Kalibreringsprosedyre", 1)
para("1. Koble driveren til kalibreringsvekt (0,01 g opplosning).")
para("2. Kjør 20 doser a 1,0 ml og vei totalen.")
para("3. Beregn korreksjonsfaktor = forventet vekt / malt vekt.")
para("4. Skaler firmware-konstanten tilsvarende; endre ALDRI registerets "
     "enhet — enheten er fastsatt i avsnitt 4.3.")
for i in range(1, 21):
    para(f"Trinn {i}. Bekreft at kanal {(i-1) % 4} leverer innenfor +/-1 % "
         f"av nominelt volum ved 1,0 ml, 5,0 ml og 12,5 ml. Logg avviket.")

# 11. Application notes (padding + distractor units)
heading("11. Applikasjonsnotater", 1)
para("11.1 EC og pH: EC-registeret (0x0052) er i 0,001 S/m. En avlest verdi "
     "1400 tilsvarer 1,4 S/m. pH leveres som egen analog kanal og er ikke "
     "en del av dette registerkartet.")
para("11.2 Temperatur: 0x0050 er i 0,1 grader C. Verdi 245 tilsvarer "
     "24,5 C. Negative temperaturer bruker to-komplement.")
para("11.3 Mot-trykk: 0x0051 er i 1 hPa. Verdi 1000 tilsvarer 1000 hPa "
     "(1 bar).")
para("11.4 Stromning: 0x0040..0x0043 er i 0,01 L/min. Verdi 120 tilsvarer "
     "1,20 L/min.")
para("11.5 Posisjon: 0x0030..0x0033 er i 1/256 omdreining. Verdi 256 "
     "tilsvarer en hel omdreining.")
for n in range(6, 200):
    para(f"11.{n} Generell anbefaling nr. {n}: overvak mot-trykk og "
         f"temperatur kontinuerlig, og kalibrer volum ved "
         f"{n * 3} dagers drift. Unnga luft i slangene ved a prime pumpene "
         f"etter hver 4. syklus. Kontroller RS-485-termineringen ved "
         f"installasjon og etter hver service.")

# Appendix A — register read/write examples (padding, distractor-rich)
heading("Tillegg A. Register-eksempler", 1)
para("Eksemplene under viser typiske Modbus-rammer. De er illustrative; "
     "enhetene er fastsatt i avsnitt 4.2 og 4.3.")
for ex in range(1, 120):
    para(f"A.{ex} Eksempel {ex}: skriv/les mot register "
         f"0x{(0x10 + (ex % 0x40)):04X}. Typisk verdi "
         f"{100 + ex * 7} (enhet per avsnitt 4.2). Bekreft tilbakemelding "
         f"med CRC16 og tolk feil-flagg i 0x0013 dersom respons uteblir.")


# 12. Compliance
heading("12. Samsvar og sikkerhet", 1)
para("PM-4-familien er CE-merket (EMC 2014/30/EU, LVD 2014/35/EU) og "
     "RoHS-kompatibel. IP-klasse IP42. Driftstemperatur -20..+70 C, "
     "lagring -40..+85 C.")

# 13. Ordering
heading("13. Bestillingsinformasjon", 1)
table([
    "Varenummer    | Beskrivelse",
    "--------------+--------------------------------",
    "PM4-4C-BASE   | 4-kanal driver, standard",
    "PM4-4C-HF     | 4-kanal driver, hoyvolum",
    "PM4-KIT-CAL   | Kalibreringssett (vekt + mal)",
    "PM4-CABLE-RS  | RS-485 kabel, 3 m, terminert",
])

# 14. FAQ (padding + one more distractor)
heading("14. Vanlige sporsmal (FAQ)", 1)
faqs = [
    ("Hvorfor doserer pumpen min 10x for lite?",
     "Sjekk at firmware ganger onsket ml med 10 for dosevolum-registeret "
     "skrives. Registeret er i 0,1 ml — a skrive hele ml gir 10x for lite."),
    ("Hva er enheten til dosevolum-registeret?",
     "0,1 milliliter. Se avsnitt 4.3."),
    ("Er enheten forskjellig for PM-4HF?",
     "Nei. PM-4HF bruker samme enhet (0,1 ml) for dosevolum."),
    ("Hva er enheten til stromnings-registeret?",
     "0,01 L/min (avsnitt 4.2). Ikke forveksle med dosevolum."),
    ("Hva er enheten til temperatur-registeret?",
     "0,1 grader C (avsnitt 4.2)."),
    ("Hvordan nullstiller jeg en pumpe?",
     "Skriv 0 til posisjons-registeret 0x0030..0x0033."),
    ("Kan jeg bruke 0x0020 for a lese dose?",
     "Nei, 0x0020..0x0023 er skriveregistre. Les posisjon fra "
     "0x0030..0x0033."),
]
for q, a in faqs:
    emit("Q: " + q, bold=True)
    para("A: " + a)

# 15. Glossary (padding)
heading("15. Ordliste", 1)
terms = [
    ("Dosevolum", "Onsket volum væske som pumpes i en syklus, angitt i ml."),
    ("Register", "16-bit Modbus-celle med fast enhet og retning."),
    ("Derating", "Reduksjon av tillatt drift ved hoy temperatur."),
    ("Peristaltisk", "Pumpeteknikk der væske drives ved a klemme en slange."),
    ("RS-485", "Differensiell seriell buss brukt av Modbus RTU."),
    ("Big-endian", "Byte-rekkefolge der mest signifikante byte kommer forst."),
]
for k, v in terms:
    emit(k + ": ", bold=True)
    para(v, indent=True)

doc.save(OUT)
doc.close()
print("saved", OUT)

# report extracted text size
import subprocess
txt = subprocess.run(["python3", ".pilot/pdf_extract.py", OUT, "2000000"],
                     capture_output=True, text=True).stdout
print("extracted text chars:", len(txt), "| est tokens (chars/4):", round(len(txt)/4))
print("pages:", fitz.open(OUT).page_count)
