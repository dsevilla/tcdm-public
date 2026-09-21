"""Comprobar un bucket S3 mediante el cliente estándar de AWS (boto3)."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config


def main(argv: Sequence[str] | None = None) -> int:
    """Listar objetos, consultar sus metadatos y leer una cabecera Parquet."""

    parser = argparse.ArgumentParser(description="Comprueba operaciones S3 básicas con boto3.")
    parser.add_argument("bucket")
    parser.add_argument("prefix")
    parser.add_argument("--minimum-objects", type=int, default=1)
    args: argparse.Namespace = parser.parse_args(argv)

    endpoint: str = os.environ.get("AWS_ENDPOINT_URL", "https://s3.amazonaws.com")
    region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    addressing_style: str = os.environ.get("AWS_S3_ADDRESSING_STYLE", "path")
    client: BaseClient = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        config=Config(s3={"addressing_style": addressing_style}),
    )

    print("[ORDEN -> API S3] list_buckets()")
    buckets: list[dict[str, Any]] = client.list_buckets().get("Buckets", [])
    print("[RESULTADO <- API S3] Buckets:", [item["Name"] for item in buckets])
    if not any(item["Name"] == args.bucket for item in buckets):
        raise SystemExit(f"El bucket {args.bucket!r} no aparece en list_buckets()")

    print(f"[ORDEN -> API S3] list_objects_v2(Bucket={args.bucket!r}, Prefix={args.prefix!r})")
    response: dict[str, Any] = client.list_objects_v2(
        Bucket=args.bucket,
        Prefix=args.prefix.rstrip("/") + "/",
    )
    objects: list[dict[str, Any]] = response.get("Contents", [])
    print("[RESULTADO <- API S3] Objetos:")
    for item in objects:
        print(f"  {item['Key']} ({item['Size']} bytes)")
    if len(objects) < args.minimum_objects:
        raise SystemExit(f"Se esperaban al menos {args.minimum_objects} objetos")

    first_key: str = str(objects[0]["Key"])
    print(f"[ORDEN -> API S3] head_object(Bucket={args.bucket!r}, Key={first_key!r})")
    metadata: dict[str, Any] = client.head_object(Bucket=args.bucket, Key=first_key)
    print(
        "[RESULTADO <- API S3] Metadata:",
        {"ContentLength": metadata["ContentLength"], "ETag": metadata["ETag"]},
    )
    print(f"[ORDEN -> API S3] get_object(Range='bytes=0-3') sobre {first_key!r}")
    body: bytes = client.get_object(
        Bucket=args.bucket,
        Key=first_key,
        Range="bytes=0-3",
    )["Body"].read()
    print("[RESULTADO <- API S3] Cabecera:", body)
    if body != b"PAR1":
        raise SystemExit("El objeto no comienza por la firma PAR1 de Parquet")
    print("TCDM_S3_API_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
