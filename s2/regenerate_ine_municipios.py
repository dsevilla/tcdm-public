#!/usr/bin/env python3
"""Regenera la instantánea de municipios del INE usada en `s2.ipynb`.

Este script no forma parte del flujo de la sesión que sigue el alumnado: es
una herramienta de mantenimiento para quien deba actualizar
`entorno/data/ine/municipios-2026.csv.gz` cuando el INE publique una nueva
edición de la Relación de municipios y códigos. Descarga el XLSX oficial, lo
lee con `polars.read_excel` (una hoja por provincia) y normaliza sus filas al
mismo CSV que consume la sesión:
`municipio_id;provincia_id;codigo_municipio;digito_control;municipio;provincia`.

Con `--check` compara el resultado contra la instantánea ya versionada sin
escribir nada; es el modo usado para comprobar que la lectura con polars
sigue reproduciendo exactamente la copia distribuida antes de incorporar el
código a `s2.ipynb` como referencia.

Requiere el paquete Python `fastexcel` (motor `calamine` de
`polars.read_excel`), que no está en `requirements.txt` de la sesión porque
el alumnado no necesita ejecutar este script.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import polars as pl

INE_URL = "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx"
EXPECTED_SHEET_HEADER = ["CPRO", "CMUN", "DC", "NOMBRE"]
CSV_HEADER = (
    "municipio_id",
    "provincia_id",
    "codigo_municipio",
    "digito_control",
    "municipio",
    "provincia",
)
DEFAULT_SNAPSHOT = (
    Path(__file__).resolve().parent.parent.parent
    / "entorno"
    / "data"
    / "ine"
    / "municipios-2026.csv.gz"
)


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def read_municipalities(xlsx_path: Path) -> list[tuple[str, ...]]:
    municipalities: list[tuple[str, ...]] = []
    sheets = pl.read_excel(xlsx_path, sheet_id=0, has_header=False)
    for frame in sheets.values():
        header = [str(value) for value in frame.row(2)[:4]]
        assert header == EXPECTED_SHEET_HEADER, f"Cabecera de hoja inesperada: {header}"
        province = str(frame.row(1)[0])
        for row in frame[3:].iter_rows():
            province_id, municipality_code, check_digit, municipality = (
                "" if value is None else str(value) for value in row[:4]
            )
            if not all((province_id, municipality_code, check_digit, municipality)):
                continue
            municipality_id = f"{province_id}{municipality_code}"
            municipalities.append(
                (
                    municipality_id,
                    province_id,
                    municipality_code,
                    check_digit,
                    municipality,
                    province,
                )
            )
    municipalities.sort(key=lambda row: row[0])
    return municipalities


def check_contract(municipalities: list[tuple[str, ...]]) -> None:
    province_ids = {row[1] for row in municipalities}
    assert len(municipalities) == 8_132, f"Se esperaban 8.132 municipios, hay {len(municipalities)}"
    assert len({row[0] for row in municipalities}) == len(
        municipalities
    ), "Hay municipio_id repetidos"
    assert province_ids == {f"{code:02d}" for code in range(1, 53)}, "Faltan o sobran provincias"


def read_snapshot(gzip_path: Path) -> list[tuple[str, ...]]:
    with gzip.open(gzip_path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.reader(source, delimiter=";")
        header = tuple(next(reader))
        assert header == CSV_HEADER, f"Cabecera inesperada en {gzip_path}: {header}"
        return [tuple(row) for row in reader]


def write_snapshot(municipalities: list[tuple[str, ...]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(
        destination, "wt", encoding="utf-8", newline="", compresslevel=9, mtime=0
    ) as output:
        writer = csv.writer(output, delimiter=";", lineterminator="\n")
        writer.writerow(CSV_HEADER)
        writer.writerows(municipalities)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--xlsx", type=Path, help="XLSX ya descargado; si se omite, se descarga de INE_URL"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compara contra la instantánea ya versionada en vez de escribirla",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=f"Ruta del CSV gzip a comparar o escribir (por defecto {DEFAULT_SNAPSHOT})",
    )
    args = parser.parse_args()

    xlsx_path = args.xlsx
    if xlsx_path is None:
        xlsx_path = Path("/tmp/26codmun.xlsx")
        print(f"Descargando {INE_URL} -> {xlsx_path}")
        download(INE_URL, xlsx_path)

    municipalities = read_municipalities(xlsx_path)
    print(f"{len(municipalities)} municipios leídos con polars.read_excel")
    check_contract(municipalities)
    print("Contrato verificado: 8.132 municipios únicos, provincias 01-52")

    if args.check:
        expected = read_snapshot(args.snapshot)
        if municipalities != expected:
            print(f"DIFIERE de la instantánea versionada en {args.snapshot}", file=sys.stderr)
            return 1
        print(f"Coincide con la instantánea versionada en {args.snapshot}")
        return 0

    write_snapshot(municipalities, args.snapshot)
    print(f"Escrito {args.snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
