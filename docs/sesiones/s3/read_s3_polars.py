"""Leer fragmentos Parquet de un bucket S3-compatible con Polars."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import fsspec
import polars as pl
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
        description="Lee Parquet de un bucket S3-compatible con Polars."
    )
    parser.add_argument("bucket")
    parser.add_argument("prefix")
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
    """Crear el acceso S3 con la implementación estándar de fsspec."""

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
    """Leer los objetos, imprimir una muestra y resumir una clave."""

    args: ReaderArguments = parse_arguments(argv)
    filesystem: AbstractFileSystem = create_s3_filesystem()
    pattern: str = f"{args.bucket}/{args.prefix}/*"
    files: list[str] = sorted(
        path
        for path in cast(list[str], filesystem.glob(pattern))
        if not path.endswith("/") and not path.endswith("/_SUCCESS")
    )
    if not files:
        raise SystemExit(f"No hay objetos de datos que coincidan con {pattern}")
    print(f"[ORDEN -> S3/fsspec] Se han encontrado {len(files)} objeto(s).")

    frames: list[pl.DataFrame] = []
    for path in files:
        print(f"[ORDEN -> Polars] Leyendo s3://{path} con read_parquet().")
        with filesystem.open(path, "rb") as stream:
            frames.append(pl.read_parquet(stream))
    dataframe: pl.DataFrame = pl.concat(frames, how="vertical_relaxed")
    if args.key_column not in dataframe.columns:
        raise SystemExit(f"No existe la columna {args.key_column!r}")

    print(f"[RESULTADO <- Polars] Esquema: {dataframe.schema}")
    print(f"[RESULTADO <- Polars] Primeras filas:\n{dataframe.head(5)}")
    key: pl.Expr = pl.col(args.key_column)
    values: dict[str, int | None] = dataframe.select(
        pl.len().alias("rows"),
        key.count().alias("non_null_keys"),
        key.min().alias("minimum_key"),
        key.max().alias("maximum_key"),
        key.sum().alias("key_sum"),
    ).row(0, named=True)
    summary: Summary = (
        int(values["rows"] or 0),
        int(values["non_null_keys"] or 0),
        cast(int | None, values["minimum_key"]),
        cast(int | None, values["maximum_key"]),
        cast(int | None, values["key_sum"]),
    )
    print(f"[RESULTADO <- Polars] filas, no nulos, mínimo, máximo, suma = {summary}")
    if summary[0] != args.expected_rows:
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y se han leído {summary[0]}")
    print("TCDM_SUMMARY\tpolars-s3\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
