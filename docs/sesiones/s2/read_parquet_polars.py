"""Leer una tabla Parquet de HDFS con WebHDFS, fsspec y Polars."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import fsspec
import polars as pl
from fsspec.spec import AbstractFileSystem

type Summary = tuple[int, int, int | None, int | None, int | None]


@dataclass(frozen=True, slots=True)
class ReaderArguments:
    """Argumentos comunes de los lectores de la sesión."""

    table_path: str
    key_column: str
    expected_rows: int
    columns: list[str] | None


def parse_arguments(argv: Sequence[str] | None = None) -> ReaderArguments:
    """Convertir los argumentos de la línea de órdenes en un objeto tipado."""

    parser = argparse.ArgumentParser(
        description="Lee fragmentos Parquet remotos y los combina en un DataFrame Polars."
    )
    parser.add_argument(
        "table_path",
        help="Ruta HDFS del directorio de la tabla, por ejemplo /datalake/raw/tpcds/date_dim",
    )
    parser.add_argument(
        "--key-column",
        required=True,
        help="Columna numérica que se usará para el resumen de consistencia",
    )
    parser.add_argument(
        "--expected-rows",
        required=True,
        type=int,
        help="Número de filas esperado para esta tabla y escala",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        help="Columnas que se quieren leer; si se omite, se leen todas",
    )
    namespace: argparse.Namespace = parser.parse_args(argv)
    table_path: str = namespace.table_path.rstrip("/")
    key_column: str = namespace.key_column
    expected_rows: int = namespace.expected_rows
    columns: list[str] | None = cast(list[str] | None, namespace.columns)

    if columns and key_column not in columns:
        parser.error("--key-column debe estar incluido en --columns")

    return ReaderArguments(
        table_path=table_path,
        key_column=key_column,
        expected_rows=expected_rows,
        columns=columns,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Leer los Parquet y mostrar un resumen verificable."""

    args = parse_arguments(argv)
    table_name: str = args.table_path.rsplit("/", maxsplit=1)[-1]

    print("[ORDEN -> fsspec] Conectando a WebHDFS con la identidad luser.")
    webhdfs: AbstractFileSystem = fsspec.filesystem(
        "webhdfs",
        host="namenode",
        port=9870,
        user="luser",
        use_https=False,
    )

    print(f"[ORDEN -> fsspec] Listando {args.table_path}/* y excluyendo _SUCCESS.")
    files: list[str] = sorted(
        path for path in webhdfs.glob(f"{args.table_path}/*") if not path.endswith("/_SUCCESS")
    )
    if not files:
        raise SystemExit(f"No hay ficheros de datos en {args.table_path}")
    if not webhdfs.exists(f"{args.table_path}/_SUCCESS"):
        raise SystemExit(f"Falta el marcador _SUCCESS en {args.table_path}")

    print("[RESULTADO <- fsspec] Ficheros que se leerán:")
    for path in files:
        info: dict[str, Any] = webhdfs.info(path)
        print(f"  {path} ({info['size']} bytes)")
    print(f"[RESULTADO <- fsspec] Total: {len(files)} fichero(s) Parquet.")

    print("[ORDEN -> Polars] Abriendo cada fichero con webhdfs.open().")
    fragments: list[pl.DataFrame] = []
    for path in files:
        with webhdfs.open(path, "rb") as source:
            fragments.append(pl.read_parquet(source, columns=args.columns))

    print("[ORDEN -> Polars] Concatenando los fragmentos en un único DataFrame.")
    polars_table: pl.DataFrame = pl.concat(fragments, how="vertical")
    if args.key_column not in polars_table.columns:
        raise SystemExit(
            f"La columna clave {args.key_column!r} no aparece en el esquema: "
            f"{polars_table.columns}"
        )

    key_values: pl.Series = polars_table.get_column(args.key_column)
    summary: Summary = (
        polars_table.height,
        key_values.len() - key_values.null_count(),
        cast(int | None, key_values.min()),
        cast(int | None, key_values.max()),
        cast(int | None, key_values.sum()),
    )
    print(f"[RESULTADO <- Polars] Esquema: {polars_table.schema}")
    print(f"[RESULTADO <- Polars] Primeras filas:\n{polars_table.head(5)}")
    print("[RESULTADO <- Polars] " f"filas, no nulos, mínimo, máximo, suma = {summary}")
    if summary[0] != args.expected_rows:
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y Polars ha leído {summary[0]}")

    print(f"TCDM_SUMMARY\tpolars\t{table_name}\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
