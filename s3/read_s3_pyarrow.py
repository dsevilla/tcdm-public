"""Leer fragmentos Parquet de un bucket S3-compatible con PyArrow."""

from __future__ import annotations

import argparse
import os
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
    """Argumentos de la lectura y de la comprobación de consistencia."""

    bucket: str
    prefix: str
    key_column: str
    expected_rows: int


def parse_arguments(argv: Sequence[str] | None = None) -> ReaderArguments:
    """Analizar los argumentos de la línea de órdenes."""

    parser = argparse.ArgumentParser(
        description="Lee Parquet de un bucket S3-compatible con PyArrow."
    )
    parser.add_argument("bucket", help="Nombre del bucket, por ejemplo tcdm-datalake")
    parser.add_argument(
        "prefix",
        help="Prefijo de la tabla, por ejemplo raw/tpcds/date_dim",
    )
    parser.add_argument("--key-column", required=True)
    parser.add_argument("--expected-rows", required=True, type=int)
    namespace: argparse.Namespace = parser.parse_args(argv)
    return ReaderArguments(
        bucket=namespace.bucket,
        prefix=namespace.prefix.rstrip("/"),
        key_column=namespace.key_column,
        expected_rows=namespace.expected_rows,
    )


def create_s3_filesystem() -> AbstractFileSystem:
    """Crear un filesystem fsspec mediante el cliente estándar de AWS."""

    endpoint: str = os.environ.get("AWS_ENDPOINT_URL", "https://s3.amazonaws.com")
    region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    addressing_style: str = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path")
    return cast(
        AbstractFileSystem,
        fsspec.filesystem(
            "s3",
            key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            token=os.environ.get("AWS_SESSION_TOKEN"),
            client_kwargs={"endpoint_url": endpoint, "region_name": region},
            config_kwargs={"s3": {"addressing_style": addressing_style}},
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Leer los Parquet y mostrar una firma verificable."""

    args: ReaderArguments = parse_arguments(argv)
    filesystem: AbstractFileSystem = create_s3_filesystem()
    pattern: str = f"{args.bucket}/{args.prefix}/*"

    print("[ORDEN -> S3/fsspec] Listando objetos bajo:", pattern)
    files: list[str] = sorted(
        path
        for path in cast(list[str], filesystem.glob(pattern))
        if not path.endswith("/") and not path.endswith("/_SUCCESS")
    )
    if not files:
        raise SystemExit(f"No hay objetos de datos que coincidan con {pattern}")
    print("[RESULTADO <- S3/fsspec] Objetos que se leerán:")
    for path in files:
        info: dict[str, Any] = filesystem.info(path)
        print(f"  s3://{path} ({info['size']} bytes)")

    print("[ORDEN -> PyArrow] Adaptando s3fs mediante FSSpecHandler.")
    arrow_fs: pafs.FileSystem = pafs.PyFileSystem(pafs.FSSpecHandler(filesystem))
    print("[ORDEN -> PyArrow] Leyendo todos los fragmentos con read_table().")
    table: pa.Table = pq.read_table(
        files,
        filesystem=arrow_fs,
    )
    if args.key_column not in table.column_names:
        raise SystemExit(f"No existe la columna {args.key_column!r}")

    values: pa.ChunkedArray = table[args.key_column]
    summary: Summary = (
        table.num_rows,
        cast(int, pc.count(values).as_py()),
        cast(int | None, pc.min(values).as_py()),
        cast(int | None, pc.max(values).as_py()),
        cast(int | None, pc.sum(values).as_py()),
    )
    print(f"[RESULTADO <- PyArrow] Esquema:\n{table.schema}")
    print(f"[RESULTADO <- PyArrow] Primeras filas:\n{table.slice(0, 5)}")
    print(f"[RESULTADO <- PyArrow] filas, no nulos, mínimo, máximo, suma = {summary}")
    if summary[0] != args.expected_rows:
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y se han leído {summary[0]}")
    print("TCDM_SUMMARY\tpyarrow-s3\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
