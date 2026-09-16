"""Consultar una tabla Parquet de HDFS con WebHDFS, fsspec y DuckDB."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import duckdb
import fsspec
from fsspec.spec import AbstractFileSystem

type Summary = tuple[int, int, int | None, int | None, int | None]
type QueryRow = tuple[Any, ...]


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
        description="Consulta ficheros Parquet remotos con SQL de DuckDB."
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
        help="Columnas que se quieren consultar; si se omite, se consultan todas",
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

    urls: list[str] = [f"webhdfs://{path}" for path in files]
    connection: duckdb.DuckDBPyConnection = duckdb.connect()
    print("[ORDEN -> DuckDB] Registrando el filesystem fsspec en la conexión.")
    duckdb.register_filesystem(webhdfs, connection=connection)
    selected_columns: str = ", ".join(args.columns) if args.columns else "*"

    print("[ORDEN -> DuckDB] DESCRIBE de la lectura Parquet.")
    description: list[QueryRow] = connection.execute(
        f"DESCRIBE SELECT {selected_columns} FROM read_parquet(?)",
        [urls],
    ).fetchall()
    print(f"[RESULTADO <- DuckDB] Esquema: {description}")

    print("[ORDEN -> DuckDB] SELECT de las primeras cinco filas.")
    sample: list[QueryRow] = connection.execute(
        f"SELECT {selected_columns} FROM read_parquet(?) LIMIT 5",
        [urls],
    ).fetchall()
    print(f"[RESULTADO <- DuckDB] Primeras filas: {sample}")

    print("[ORDEN -> DuckDB] Agregando filas y la columna clave sobre todos los ficheros.")
    result: QueryRow | None = connection.execute(
        f"""SELECT
                count(*) AS rows,
                count({args.key_column}) AS non_null_keys,
                min({args.key_column}) AS minimum_key,
                max({args.key_column}) AS maximum_key,
                sum({args.key_column}) AS key_sum
            FROM read_parquet(?)""",
        [urls],
    ).fetchone()
    if result is None:
        raise SystemExit("DuckDB no devolvió el resumen esperado")

    summary: Summary = cast(Summary, result)
    print(f"[RESULTADO <- DuckDB] filas, no nulos, mínimo, máximo, suma = {summary}")
    if summary[0] != args.expected_rows:
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y DuckDB ha leído {summary[0]}")

    print(f"TCDM_SUMMARY\tduckdb\t{table_name}\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
