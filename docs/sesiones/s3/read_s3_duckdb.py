"""Consultar Parquet de un bucket S3-compatible con DuckDB y httpfs."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import boto3
import duckdb
from botocore.client import BaseClient
from botocore.config import Config

type Summary = tuple[int, int, int | None, int | None, int | None]
type QueryRow = tuple[Any, ...]


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
        description="Consulta Parquet S3-compatible con SQL de DuckDB."
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


def create_s3_client() -> BaseClient:
    """Crear el cliente boto3 que enumera los objetos del prefijo."""

    endpoint: str = os.environ.get("AWS_ENDPOINT_URL", "https://s3.amazonaws.com")
    region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    addressing_style: str = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path")
    return cast(
        BaseClient,
        boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
            config=Config(s3={"addressing_style": addressing_style}),
        ),
    )


def sql_string(value: str) -> str:
    """Representar una cadena como literal SQL de DuckDB."""

    return "'" + value.replace("'", "''") + "'"


def configure_duckdb_s3(connection: duckdb.DuckDBPyConnection) -> None:
    """Cargar httpfs y configurar sus credenciales para S3-compatible."""

    endpoint_url: str = os.environ.get("AWS_ENDPOINT_URL", "https://s3.amazonaws.com")
    endpoint: str = endpoint_url.removeprefix("http://").removeprefix("https://")
    endpoint = endpoint.rstrip("/")
    region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    addressing_style: str = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path")
    access_key: str | None = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key: str | None = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token: str | None = os.environ.get("AWS_SESSION_TOKEN")
    use_ssl: str = str(endpoint_url.startswith("https://")).lower()

    print("[ORDEN -> DuckDB] Cargando la extensión nativa httpfs.")
    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")

    credential_fields: str
    if access_key is not None and secret_key is not None:
        credential_fields = (
            f"PROVIDER config,\n"
            f"        KEY_ID {sql_string(access_key)},\n"
            f"        SECRET {sql_string(secret_key)}"
        )
        if session_token is not None:
            credential_fields += f",\n        SESSION_TOKEN {sql_string(session_token)}"
    else:
        credential_fields = "PROVIDER credential_chain"

    connection.execute(f"""CREATE OR REPLACE SECRET tcdm_s3 (
        TYPE S3,
        {credential_fields},
        REGION {sql_string(region)},
        ENDPOINT {sql_string(endpoint)},
        URL_STYLE {sql_string(addressing_style)},
        USE_SSL {use_ssl}
    )""")


def list_s3_objects(client: BaseClient, bucket: str, prefix: str) -> list[str]:
    """Enumerar los objetos de datos bajo un prefijo mediante la API S3."""

    paginator: Any = client.get_paginator("list_objects_v2")
    return sorted(
        str(item["Key"])
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix.rstrip("/") + "/")
        for item in page.get("Contents", [])
        if not str(item["Key"]).endswith("/") and not str(item["Key"]).endswith("/_SUCCESS")
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecutar una muestra y una agregación SQL sobre todos los Parquet."""

    args = parse_arguments(argv)
    client: BaseClient = create_s3_client()
    files: list[str] = list_s3_objects(client, args.bucket, args.prefix)
    if not files:
        raise SystemExit(f"No hay objetos de datos bajo s3://{args.bucket}/{args.prefix}")
    urls: list[str] = [f"s3://{args.bucket}/{path}" for path in files]
    print(f"[RESULTADO <- API S3] Objetos: {urls}")

    connection: duckdb.DuckDBPyConnection = duckdb.connect()
    configure_duckdb_s3(connection)
    print("[ORDEN -> DuckDB] DESCRIBE de read_parquet().")
    description: list[QueryRow] = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)", [urls]
    ).fetchall()
    print(f"[RESULTADO <- DuckDB] Esquema: {description}")

    print("[ORDEN -> DuckDB] SELECT de las primeras cinco filas.")
    sample: list[QueryRow] = connection.execute(
        "SELECT * FROM read_parquet(?) LIMIT 5", [urls]
    ).fetchall()
    print(f"[RESULTADO <- DuckDB] Primeras filas: {sample}")

    print("[ORDEN -> DuckDB] Agregando filas y la columna clave.")
    result: QueryRow | None = connection.execute(
        f"""SELECT count(*) AS rows,
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
        raise SystemExit(f"Se esperaban {args.expected_rows} filas y se han leído {summary[0]}")
    print("TCDM_SUMMARY\tduckdb-s3\t" + "\t".join(map(str, summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
