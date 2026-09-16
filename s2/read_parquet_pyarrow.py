"""Leer una tabla Parquet de HDFS con WebHDFS, fsspec y PyArrow."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import fsspec
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq
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
        description="Lee todos los fragmentos Parquet de una tabla mediante WebHDFS."
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

    args: ReaderArguments = parse_arguments(argv)
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

    print("[ORDEN -> PyArrow] Adaptando el filesystem fsspec mediante FSSpecHandler.")
    arrow_fs: pafs.FileSystem = pafs.PyFileSystem(pafs.FSSpecHandler(webhdfs))
    print("[ORDEN -> PyArrow] Leyendo todos los fragmentos con read_table().")
    arrow_table: pa.Table = pq.read_table(
        files,
        filesystem=arrow_fs,
        columns=args.columns,
    )

    if args.key_column not in arrow_table.column_names:
        raise SystemExit(
            f"La columna clave {args.key_column!r} no aparece en el esquema: "
            f"{arrow_table.column_names}"
        )

    key_values: pa.ChunkedArray = arrow_table[args.key_column]
    summary: Summary = (
        arrow_table.num_rows,
        cast(int, pc.count(key_values).as_py()),
        cast(int | None, pc.min(key_values).as_py()),
        cast(int | None, pc.max(key_values).as_py()),
        cast(int | None, pc.sum(key_values).as_py()),
    )
    print(f"[RESULTADO <- PyArrow] Esquema:\n{arrow_table.schema}")
    print(f"[RESULTADO <- PyArrow] Primeras filas:\n{arrow_table.slice(0, 5)}")
    print("[RESULTADO <- PyArrow] " f"filas, no nulos, mínimo, máximo, suma = {summary}")
    if summary[0] != args.expected_rows:
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y PyArrow ha leído {summary[0]}")

    print(f"TCDM_SUMMARY\tpyarrow\t{table_name}\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
