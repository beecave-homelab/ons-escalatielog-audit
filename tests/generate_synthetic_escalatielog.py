import argparse
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

HEADERS = [
    "Gebruiker",
    "Medewerkernummer",
    "Medewerkersteam",
    "Deskundigheid medewerker",
    "Gebruikersnaam",
    "Escalatie reden",
    "Tijdsduur (min.)",
    "Escalatiedoel type",
    "Escalatiedoel naam",
    "Escalatiedoel identificatienummer",
    "Hoofdlocatie cliënt",
    "Gestart op",
    "Geactiveerd op",
    "Bron",
]
MANUAL_REASONS = [
    "Acute ondersteuning buiten het vaste team",
    "Controle na overdracht van zorg",
    "Ondersteuning tijdens avond- of nachtdienst",
    "Synthetische reden voor geautomatiseerde layoutcontrole",
    "Tijdelijke vervanging binnen het testrooster",
    "Voorbereiding van een geplande synthetische handeling",
]
SYSTEM_REASONS = [
    "cliënt gekoppeld aan item in ons ketenverkeer",
    "systeemescalatie: sta 30 minuten toegang toe tot cliënt na aanmaken.",
    "toegang tot cliënt nadat deze is aangemaakt door ons ketenverkeer",
]
TEAMS = [
    "Synthetisch team Noord",
    "Synthetisch team Oost",
    "Synthetisch team West",
    "Synthetisch testteam met lange naam",
]
EXPERTISES = [
    "Begeleiding",
    "Nachtdienst",
    "Synthetische deskundigheid",
    "Verpleegkundige testfunctie",
]
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def worksheet_xml(rows: list[list[str]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = "".join(
            f'<c r="{column_name(column_index)}{row_index}" t="inlineStr">'
            f"<is><t>{escape(value)}</t></is></c>"
            for column_index, value in enumerate(row, 1)
        )
        xml_rows.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData></worksheet>"
    )


def format_date(value: datetime) -> str:
    return value.strftime("%d-%m-%Y, %H:%M:%S")


def layout_rows(row_count: int, rng: random.Random) -> list[list[str]]:
    rows = []
    for index in range(row_count):
        employee = index // 2 + 1
        attempt = index % 2 + 1
        rows.append(
            [
                f"Testmedewerker {employee:03d}",
                f"TEST-{employee:04d}",
                "Synthetisch testteam met lange naam",
                "Synthetische deskundigheid",
                f"testgebruiker{employee:03d}",
                rng.choice(MANUAL_REASONS),
                str(rng.choice((15, 30, 60))),
                "Cliënt",
                f"Testcliënt {employee:03d}-{attempt}",
                f"CLIENT-{employee:04d}-{attempt}",
                "Synthetische hoofdlocatie",
                f"01-05-2026, 00:{index % 60:02d}:00",
                "Niet geactiveerd",
                "Synthetische testfixture",
            ]
        )
    return rows


def mixed_rows(row_count: int, rng: random.Random) -> list[list[str]]:
    rows = []
    employee_count = max(12, min(250, row_count // 6 or 1))
    client_count = max(24, min(600, row_count // 3 or 1))
    base = datetime(2026, 5, 1)
    for _index in range(row_count):
        if rows and rng.random() < 0.025:
            rows.append(rows[-1].copy())
            continue
        employee = rng.randrange(1, employee_count + 1)
        target = rng.randrange(1, client_count + 1)
        started = base + timedelta(seconds=rng.randrange(31 * 24 * 60 * 60))
        system_event = rng.random() < 0.08
        reason = rng.choice(SYSTEM_REASONS if system_event else MANUAL_REASONS)
        duration = "30" if system_event else str(rng.choice((15, 30, 60, 120, 840)))
        target_type = "Locatie" if rng.random() < 0.1 else "Cliënt"
        if target_type == "Locatie":
            target_name = f"Synthetische locatie {target % 40 + 1:03d}"
            target_id = f"SYN-L-{target % 40 + 1:04d}"
        else:
            target_name = f"Synthetische cliënt {target:04d}"
            target_id = f"SYN-C-{target:05d}"
        if not system_event and rng.random() < 0.03:
            target_name, target_id = "", ""
        activation_roll = rng.random()
        if system_event:
            activated = format_date(started)
        elif activation_roll < 0.18:
            activated = "Niet geactiveerd"
        elif activation_roll < 0.21:
            activated = format_date(started - timedelta(minutes=rng.randrange(1, 31)))
        else:
            activated = format_date(started + timedelta(minutes=rng.randrange(0, 121)))
        rows.append(
            [
                f"Synthetische medewerker {employee:03d}",
                f"SYN-M-{employee:04d}",
                TEAMS[(employee - 1) % len(TEAMS)],
                EXPERTISES[(employee - 1) % len(EXPERTISES)],
                f"synthetisch{employee:03d}",
                reason,
                duration,
                target_type,
                target_name,
                target_id,
                f"Synthetische hoofdlocatie {target % 25 + 1:03d}",
                format_date(started),
                activated,
                "Synthetische generator",
            ]
        )
    return rows


def synthetic_rows(row_count: int, seed: int, profile: str = "mixed") -> list[list[str]]:
    if row_count < 1:
        raise ValueError("Het aantal regels moet minimaal 1 zijn.")
    rng = random.Random(seed)
    data = layout_rows(row_count, rng) if profile == "layout" else mixed_rows(row_count, rng)
    return [HEADERS, *data]


def workbook_files(rows: list[list[str]]) -> dict[str, str]:
    return {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Synthetische test" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
 Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/worksheets/sheet1.xml": worksheet_xml(rows),
    }


def create_workbook(path: Path, row_count: int, seed: int, profile: str = "mixed") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as workbook:
        for name, content in workbook_files(synthetic_rows(row_count, seed, profile)).items():
            info = ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            workbook.writestr(info, content.encode())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genereer een gegevensvrij synthetisch escalatielog."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--profile", choices=("mixed", "layout"), default="mixed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        digest = create_workbook(args.output, args.rows, args.seed, args.profile)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Bestand: {args.output.resolve()}")
    print(f"Regels: {args.rows}")
    print(f"Seed: {args.seed}")
    print(f"Profiel: {args.profile}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
