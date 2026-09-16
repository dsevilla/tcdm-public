"""Generar un lote sintético de líneas de venta web para la sesión 8.

Simula la llegada periódica de pedidos nuevos sin ningún sistema de colas:
cada ejecución de este programa escribe un fichero Parquet nuevo bajo una
ruta de aterrizaje en HDFS, con el mismo esquema relevante que `web_sales`
más las columnas derivadas `sold_year`/`sold_month` que ya usa la tabla
Iceberg `iceberg.tcdm.web_sales` creada en S7. Spark Structured Streaming
recoge esos ficheros desde esa ruta con su fuente de ficheros Parquet.

El programa no depende de Spark ni de PySpark: habla con HDFS únicamente por
WebHDFS, con `fsspec` y `PyArrow`, igual que los lectores de la sesión 2
(`read_parquet_pyarrow.py`). Los rangos de claves surrogadas
(`ws_bill_customer_sk`, `ws_bill_addr_sk`, `ws_item_sk`, `ws_sold_date_sk`)
se calculan a partir de las tablas reales `customer`, `customer_address`,
`item` y `date_dim` de `/datalake/raw/tpcds`, nunca a partir de rangos
adivinados.

Cada lote mezcla dos tipos de líneas:

- **altas**: usan un par `(ws_order_number, ws_item_sk)` nuevo, que no
  colisiona con ningún pedido real ni con el de otra ejecución de este
  programa (los números de pedido de alta se generan a partir de una base
  muy por encima del rango real de TPC-DS SF1, más un contador por fila).
- **correcciones**: reutilizan deliberadamente un par
  `(ws_order_number, ws_item_sk)` que ya existe en el `web_sales` real de
  S2, con importes nuevos. `MERGE INTO` sólo compara esa clave compuesta,
  así que no hace falta que el resto de columnas coincida con la fila
  original: basta con la clave para que la operación la reconozca como una
  actualización, no como una fila nueva.

Este generador no pretende reproducir con fidelidad el modelo de precios de
TPC-DS: genera importes plausibles (cantidad, precio, descuento e importe
neto) sólo para poder demostrar el mecanismo de streaming e ingesta
incremental, no para un análisis de negocio real.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import fsspec
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from fsspec.spec import AbstractFileSystem

RAW_WEB_SALES: str = "/datalake/raw/tpcds/web_sales"
RAW_CUSTOMER: str = "/datalake/raw/tpcds/customer"
RAW_CUSTOMER_ADDRESS: str = "/datalake/raw/tpcds/customer_address"
RAW_ITEM: str = "/datalake/raw/tpcds/item"
RAW_DATE_DIM: str = "/datalake/raw/tpcds/date_dim"

# Base muy por encima de cualquier ws_order_number real de TPC-DS SF1
# (el máximo real está muy por debajo de 10 millones), para que las altas
# nunca puedan colisionar por casualidad con un pedido ya existente.
NEW_ORDER_NUMBER_BASE: int = 900_000_000

# Tamaño de la muestra de pares (ws_order_number, ws_item_sk) reales que se
# lee una sola vez del web_sales de S2 para poder simular correcciones.
EXISTING_KEY_SAMPLE_SIZE: int = 5_000


@dataclass(frozen=True, slots=True)
class GeneratorArguments:
    """Argumentos de la línea de órdenes del generador."""

    landing_path: str
    rows: int
    update_fraction: float
    namenode_host: str
    webhdfs_port: int
    user: str
    seed: int | None


def parse_arguments(argv: Sequence[str] | None = None) -> GeneratorArguments:
    """Convertir los argumentos de la línea de órdenes en un objeto tipado."""

    parser = argparse.ArgumentParser(
        description=(
            "Genera un lote Parquet sintético de líneas de venta web y lo "
            "escribe en la ruta de aterrizaje del streaming de la sesión 8."
        )
    )
    parser.add_argument(
        "--landing-path",
        default="/datalake/raw/streaming/web_sales_incremental",
        help="Ruta HDFS donde se escribe el nuevo fichero Parquet del lote",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=150,
        help="Número de líneas de venta que contendrá este lote",
    )
    parser.add_argument(
        "--update-fraction",
        type=float,
        default=0.3,
        help=(
            "Fracción (0-1) de líneas que corrigen un (ws_order_number, "
            "ws_item_sk) ya existente en vez de dar de alta uno nuevo"
        ),
    )
    parser.add_argument(
        "--namenode-host",
        default="namenode",
        help="Host del NameNode que expone WebHDFS",
    )
    parser.add_argument(
        "--webhdfs-port",
        type=int,
        default=9870,
        help="Puerto WebHDFS del NameNode",
    )
    parser.add_argument(
        "--user",
        default="luser",
        help="Identidad HDFS con la que se generan y validan los ficheros",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semilla opcional para hacer reproducible un lote concreto",
    )
    namespace: argparse.Namespace = parser.parse_args(argv)

    if not 0.0 <= namespace.update_fraction <= 1.0:
        parser.error("--update-fraction debe estar entre 0 y 1")
    if namespace.rows <= 0:
        parser.error("--rows debe ser positivo")

    return GeneratorArguments(
        landing_path=namespace.landing_path.rstrip("/"),
        rows=namespace.rows,
        update_fraction=namespace.update_fraction,
        namenode_host=namespace.namenode_host,
        webhdfs_port=namespace.webhdfs_port,
        user=namespace.user,
        seed=namespace.seed,
    )


def connect_webhdfs(host: str, port: int, user: str) -> AbstractFileSystem:
    """Abrir la misma conexión WebHDFS que usan los lectores de S2."""

    return fsspec.filesystem(
        "webhdfs",
        host=host,
        port=port,
        user=user,
        use_https=False,
    )


def list_data_files(webhdfs: AbstractFileSystem, table_path: str) -> list[str]:
    """Listar los ficheros de datos de una tabla Parquet, sin `_SUCCESS`."""

    files: list[str] = sorted(
        path for path in webhdfs.glob(f"{table_path}/*") if not path.endswith("/_SUCCESS")
    )
    if not files:
        raise SystemExit(f"No hay ficheros de datos en {table_path}")
    return files


def read_sk_bounds(
    arrow_fs: pafs.FileSystem,
    webhdfs: AbstractFileSystem,
    table_path: str,
    sk_column: str,
) -> tuple[int, int]:
    """Leer el mínimo y el máximo reales de una clave surrogada."""

    files: list[str] = list_data_files(webhdfs, table_path)
    column: pa.ChunkedArray = pq.read_table(files, filesystem=arrow_fs, columns=[sk_column])[
        sk_column
    ]
    minimum: int = pc.min(column).as_py()
    maximum: int = pc.max(column).as_py()
    return minimum, maximum


def read_date_dim(arrow_fs: pafs.FileSystem, webhdfs: AbstractFileSystem) -> list[tuple[int, date]]:
    """Leer la tabla completa `date_dim` como pares (d_date_sk, d_date).

    `date_dim` es pequeña (73 049 filas en SF1): leerla entera permite
    elegir, para cada línea generada, una fecha real ya materializada, en
    lugar de fabricar una clave de fecha que no exista en la tabla.
    """

    files: list[str] = list_data_files(webhdfs, RAW_DATE_DIM)
    table: pa.Table = pq.read_table(files, filesystem=arrow_fs, columns=["d_date_sk", "d_date"])
    return list(zip(table["d_date_sk"].to_pylist(), table["d_date"].to_pylist()))


def read_existing_key_sample(
    arrow_fs: pafs.FileSystem, webhdfs: AbstractFileSystem, sample_size: int
) -> list[tuple[int, int]]:
    """Leer una muestra de pares `(ws_order_number, ws_item_sk)` reales.

    Sólo se leen esas dos columnas del primer fragmento Parquet de
    `web_sales` (S2): basta para tener un conjunto de claves ya conocidas
    por la tabla Iceberg de S7 con las que simular correcciones, sin tener
    que leer la tabla completa (719 384 filas en SF1).
    """

    files: list[str] = list_data_files(webhdfs, RAW_WEB_SALES)
    table: pa.Table = pq.read_table(
        files[0], filesystem=arrow_fs, columns=["ws_order_number", "ws_item_sk"]
    )
    table = table.slice(0, sample_size)
    pairs: list[tuple[int, int]] = list(
        zip(table["ws_order_number"].to_pylist(), table["ws_item_sk"].to_pylist())
    )
    # De-duplicar conservando el orden, por si el fragmento repitiera pares.
    seen: set[tuple[int, int]] = set()
    unique_pairs: list[tuple[int, int]] = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            unique_pairs.append(pair)
    return unique_pairs


def money(value: float) -> Decimal:
    """Redondear un importe a dos decimales como `Decimal`, no como `float`.

    `pa.decimal128(7, 2)` exige valores `int`/`Decimal` exactos: un `float`
    redondeado con `round()` puede seguir arrastrando el error de
    representación binaria (por ejemplo, `round(2.675, 2)` da `2.67`, no
    `2.68`). Cuantizar un `Decimal` construido a partir de la representación
    en texto del `float` evita ese problema.
    """

    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def random_money_line(
    rng: random.Random,
) -> tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Generar cantidad e importes plausibles para una línea de venta.

    Devuelve (cantidad, precio_unitario, descuento, importe_neto_venta,
    importe_neto_pagado, beneficio_neto), todos los importes como `Decimal`
    de dos decimales, para que quepan en `DECIMAL(7, 2)` igual que en la
    tabla Iceberg de destino.
    """

    quantity: int = rng.randint(1, 20)
    list_price: Decimal = money(rng.uniform(1.0, 200.0))
    discount: Decimal = money(float(list_price) * rng.uniform(0.0, 0.3))
    ext_sales_price: Decimal = money(float(list_price - discount) * quantity)
    ext_discount_amt: Decimal = money(float(discount) * quantity)
    net_paid: Decimal = ext_sales_price
    # Un beneficio neto que puede ser negativo (línea con pérdida), como en
    # el `web_sales` real de TPC-DS.
    net_profit: Decimal = money(float(net_paid) * rng.uniform(-0.1, 0.4))
    return quantity, list_price, ext_discount_amt, ext_sales_price, net_paid, net_profit


def build_batch_rows(
    args: GeneratorArguments,
    rng: random.Random,
    customer_sk_bounds: tuple[int, int],
    addr_sk_bounds: tuple[int, int],
    item_sk_bounds: tuple[int, int],
    date_dim_rows: list[tuple[int, date]],
    existing_keys: list[tuple[int, int]],
) -> tuple[list[dict[str, object]], list[tuple[int, int]], list[tuple[int, int]]]:
    """Construir las filas del lote y devolver también las claves usadas.

    Devuelve (filas, claves_actualizadas, claves_nuevas): las dos listas de
    claves sirven para que el notebook pueda enseñar, sin adivinar, una fila
    insertada y una fila corregida por el mismo `MERGE INTO`.
    """

    n_updates: int = min(round(args.rows * args.update_fraction), len(existing_keys))
    n_inserts: int = args.rows - n_updates

    updated_keys: list[tuple[int, int]] = (
        rng.sample(existing_keys, n_updates) if n_updates > 0 else []
    )

    run_base: int = NEW_ORDER_NUMBER_BASE + (time.time_ns() % 1_000_000) * 1_000
    new_keys: list[tuple[int, int]] = [
        (run_base + row_index, rng.randint(*item_sk_bounds)) for row_index in range(n_inserts)
    ]

    rows: list[dict[str, object]] = []
    for order_number, item_sk in updated_keys + new_keys:
        date_sk, sold_date = rng.choice(date_dim_rows)
        quantity, list_price, discount, ext_sales_price, net_paid, net_profit = random_money_line(
            rng
        )
        rows.append(
            {
                "ws_order_number": order_number,
                "ws_item_sk": item_sk,
                "ws_bill_customer_sk": rng.randint(*customer_sk_bounds),
                "ws_bill_addr_sk": rng.randint(*addr_sk_bounds),
                "ws_sold_date_sk": date_sk,
                "ws_sold_date": sold_date,
                "ws_quantity": quantity,
                "ws_list_price": list_price,
                "ws_ext_discount_amt": discount,
                "ws_ext_sales_price": ext_sales_price,
                "ws_net_paid": net_paid,
                "ws_net_profit": net_profit,
                "sold_year": sold_date.year,
                "sold_month": sold_date.month,
            }
        )
    return rows, updated_keys, new_keys


def rows_to_table(rows: list[dict[str, object]]) -> pa.Table:
    """Construir la tabla PyArrow con el esquema de `web_sales_incremental`."""

    schema: pa.Schema = pa.schema(
        [
            pa.field("ws_order_number", pa.int64(), nullable=False),
            pa.field("ws_item_sk", pa.int64(), nullable=False),
            pa.field("ws_bill_customer_sk", pa.int64()),
            pa.field("ws_bill_addr_sk", pa.int64()),
            pa.field("ws_sold_date_sk", pa.int64()),
            pa.field("ws_sold_date", pa.date32()),
            pa.field("ws_quantity", pa.int32()),
            pa.field("ws_list_price", pa.decimal128(7, 2)),
            pa.field("ws_ext_discount_amt", pa.decimal128(7, 2)),
            pa.field("ws_ext_sales_price", pa.decimal128(7, 2)),
            pa.field("ws_net_paid", pa.decimal128(7, 2)),
            pa.field("ws_net_profit", pa.decimal128(7, 2)),
            pa.field("sold_year", pa.int32()),
            pa.field("sold_month", pa.int32()),
        ]
    )
    columns: dict[str, list[object]] = {field.name: [] for field in schema}
    for row in rows:
        for field in schema:
            columns[field.name].append(row[field.name])
    arrays: list[pa.Array] = [pa.array(columns[field.name], type=field.type) for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)


def main(argv: Sequence[str] | None = None) -> int:
    """Generar un lote y escribirlo como Parquet nuevo en la ruta de aterrizaje."""

    args: GeneratorArguments = parse_arguments(argv)
    rng: random.Random = random.Random(args.seed)

    print("[ORDEN -> fsspec] Conectando a WebHDFS con la identidad luser.")
    webhdfs: AbstractFileSystem = connect_webhdfs(args.namenode_host, args.webhdfs_port, args.user)
    arrow_fs: pafs.FileSystem = pafs.PyFileSystem(pafs.FSSpecHandler(webhdfs))

    print("[ORDEN -> PyArrow] Calculando rangos reales de claves surrogadas.")
    customer_sk_bounds: tuple[int, int] = read_sk_bounds(
        arrow_fs, webhdfs, RAW_CUSTOMER, "c_customer_sk"
    )
    addr_sk_bounds: tuple[int, int] = read_sk_bounds(
        arrow_fs, webhdfs, RAW_CUSTOMER_ADDRESS, "ca_address_sk"
    )
    item_sk_bounds: tuple[int, int] = read_sk_bounds(arrow_fs, webhdfs, RAW_ITEM, "i_item_sk")
    print(f"[RESULTADO <- PyArrow] c_customer_sk: {customer_sk_bounds}")
    print(f"[RESULTADO <- PyArrow] ca_address_sk: {addr_sk_bounds}")
    print(f"[RESULTADO <- PyArrow] i_item_sk: {item_sk_bounds}")

    print("[ORDEN -> PyArrow] Leyendo date_dim completa para fechas reales.")
    date_dim_rows: list[tuple[int, date]] = read_date_dim(arrow_fs, webhdfs)
    print(f"[RESULTADO <- PyArrow] date_dim: {len(date_dim_rows)} fechas disponibles.")

    print(
        "[ORDEN -> PyArrow] Muestreando pares (ws_order_number, ws_item_sk) "
        "reales para simular correcciones."
    )
    existing_keys: list[tuple[int, int]] = read_existing_key_sample(
        arrow_fs, webhdfs, EXISTING_KEY_SAMPLE_SIZE
    )
    print(f"[RESULTADO <- PyArrow] {len(existing_keys)} pares reales disponibles.")

    rows, updated_keys, new_keys = build_batch_rows(
        args,
        rng,
        customer_sk_bounds,
        addr_sk_bounds,
        item_sk_bounds,
        date_dim_rows,
        existing_keys,
    )
    table: pa.Table = rows_to_table(rows)

    batch_id: str = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    batch_path: str = f"{args.landing_path}/batch-{batch_id}.parquet"

    print(f"[ORDEN -> PyArrow] Escribiendo {len(rows)} filas en {batch_path}.")
    pq.write_table(table, batch_path, filesystem=arrow_fs)
    print(f"[RESULTADO <- PyArrow] Lote escrito: {batch_path}")
    print(
        f"[RESULTADO <- PyArrow] {len(updated_keys)} corrección(es), " f"{len(new_keys)} alta(s)."
    )

    summary: dict[str, object] = {
        "batch_path": batch_path,
        "rows": len(rows),
        "updated_keys": [list(pair) for pair in updated_keys],
        "inserted_keys_sample": [list(pair) for pair in new_keys[:5]],
    }
    print(f"TCDM_BATCH_JSON\t{json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
