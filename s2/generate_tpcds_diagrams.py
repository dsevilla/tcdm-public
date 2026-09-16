#!/usr/bin/env python3
"""Regenera los diagramas de referencia del esquema TPC-DS SF1 usados en `s2.ipynb`.

Este script no forma parte del flujo de la sesión que sigue el alumnado: es
una herramienta de mantenimiento para quien edite el apéndice de esquema del
notebook. Produce tres imágenes PNG en `img/`:

- `tpcds_er_overview.png`: diagrama entidad-relación de las 24 tablas (clave
  primaria de cada una y aristas FK -> PK entre tablas).
- `tpcds_reference_dimensiones.png`: ficha de referencia rápida de las 17
  tablas de dimensiones (PK, BK y FK columna a columna).
- `tpcds_reference_hechos.png`: ficha de referencia rápida de las 7 tablas de
  hechos (PK compuesta y FK columna a columna).

Los datos de columnas, claves y relaciones están tomados del apéndice
"Esquema completo de TPC-DS SF1" del propio `s2.ipynb`; si ese apéndice
cambia, hay que actualizar `TABLES` aquí para mantener la coherencia.

Requiere el binario `dot` de Graphviz (paquete del sistema) y el paquete
Python `matplotlib`, ninguno de los cuales está en `requirements.txt` de la
sesión porque el alumnado no necesita ejecutar este script.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

IMG_DIR = Path(__file__).parent / "img"

# category: "dim" | "fact"
# pk: columnas de la clave primaria (compuesta en las tablas de hechos)
# bk: columna de clave de negocio, o None
# fks: lista de (columna_origen, tabla_destino, columna_destino)
TABLES: dict[str, dict] = {
    "date_dim": {
        "category": "dim",
        "pk": ["d_date_sk"],
        "bk": "d_date_id",
        "fks": [],
        "title": "Calendario",
    },
    "time_dim": {
        "category": "dim",
        "pk": ["t_time_sk"],
        "bk": "t_time_id",
        "fks": [],
        "title": "Hora del dia",
    },
    "item": {
        "category": "dim",
        "pk": ["i_item_sk"],
        "bk": "i_item_id",
        "fks": [],
        "title": "Producto",
    },
    "customer": {
        "category": "dim",
        "pk": ["c_customer_sk"],
        "bk": "c_customer_id",
        "fks": [
            ("c_current_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("c_current_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("c_current_addr_sk", "customer_address", "ca_address_sk"),
            ("c_first_shipto_date_sk", "date_dim", "d_date_sk"),
            ("c_first_sales_date_sk", "date_dim", "d_date_sk"),
            ("c_last_review_date_sk", "date_dim", "d_date_sk"),
        ],
        "title": "Cliente",
    },
    "customer_address": {
        "category": "dim",
        "pk": ["ca_address_sk"],
        "bk": "ca_address_id",
        "fks": [],
        "title": "Domicilio",
    },
    "customer_demographics": {
        "category": "dim",
        "pk": ["cd_demo_sk"],
        "bk": None,
        "fks": [],
        "title": "Demografia cliente",
    },
    "household_demographics": {
        "category": "dim",
        "pk": ["hd_demo_sk"],
        "bk": None,
        "fks": [("hd_income_band_sk", "income_band", "ib_income_band_sk")],
        "title": "Demografia hogar",
    },
    "income_band": {
        "category": "dim",
        "pk": ["ib_income_band_sk"],
        "bk": None,
        "fks": [],
        "title": "Tramo de ingresos",
    },
    "store": {
        "category": "dim",
        "pk": ["s_store_sk"],
        "bk": "s_store_id",
        "fks": [("s_closed_date_sk", "date_dim", "d_date_sk")],
        "title": "Tienda",
    },
    "warehouse": {
        "category": "dim",
        "pk": ["w_warehouse_sk"],
        "bk": "w_warehouse_id",
        "fks": [],
        "title": "Almacen",
    },
    "call_center": {
        "category": "dim",
        "pk": ["cc_call_center_sk"],
        "bk": "cc_call_center_id",
        "fks": [
            ("cc_closed_date_sk", "date_dim", "d_date_sk"),
            ("cc_open_date_sk", "date_dim", "d_date_sk"),
        ],
        "title": "Centro de llamadas",
    },
    "catalog_page": {
        "category": "dim",
        "pk": ["cp_catalog_page_sk"],
        "bk": "cp_catalog_page_id",
        "fks": [
            ("cp_start_date_sk", "date_dim", "d_date_sk"),
            ("cp_end_date_sk", "date_dim", "d_date_sk"),
        ],
        "title": "Pagina de catalogo",
    },
    "promotion": {
        "category": "dim",
        "pk": ["p_promo_sk"],
        "bk": "p_promo_id",
        "fks": [
            ("p_start_date_sk", "date_dim", "d_date_sk"),
            ("p_end_date_sk", "date_dim", "d_date_sk"),
            ("p_item_sk", "item", "i_item_sk"),
        ],
        "title": "Promocion",
    },
    "reason": {
        "category": "dim",
        "pk": ["r_reason_sk"],
        "bk": "r_reason_id",
        "fks": [],
        "title": "Motivo de devolucion",
    },
    "ship_mode": {
        "category": "dim",
        "pk": ["sm_ship_mode_sk"],
        "bk": "sm_ship_mode_id",
        "fks": [],
        "title": "Modo de envio",
    },
    "web_page": {
        "category": "dim",
        "pk": ["wp_web_page_sk"],
        "bk": "wp_web_page_id",
        "fks": [
            ("wp_creation_date_sk", "date_dim", "d_date_sk"),
            ("wp_access_date_sk", "date_dim", "d_date_sk"),
            ("wp_customer_sk", "customer", "c_customer_sk"),
        ],
        "title": "Pagina web",
    },
    "web_site": {
        "category": "dim",
        "pk": ["web_site_sk"],
        "bk": "web_site_id",
        "fks": [
            ("web_open_date_sk", "date_dim", "d_date_sk"),
            ("web_close_date_sk", "date_dim", "d_date_sk"),
        ],
        "title": "Sitio web",
    },
    "store_sales": {
        "category": "fact",
        "pk": ["ss_item_sk", "ss_ticket_number"],
        "bk": None,
        "fks": [
            ("ss_sold_date_sk", "date_dim", "d_date_sk"),
            ("ss_sold_time_sk", "time_dim", "t_time_sk"),
            ("ss_item_sk", "item", "i_item_sk"),
            ("ss_customer_sk", "customer", "c_customer_sk"),
            ("ss_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("ss_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("ss_addr_sk", "customer_address", "ca_address_sk"),
            ("ss_store_sk", "store", "s_store_sk"),
            ("ss_promo_sk", "promotion", "p_promo_sk"),
        ],
        "title": "Venta en tienda",
    },
    "catalog_sales": {
        "category": "fact",
        "pk": ["cs_item_sk", "cs_order_number"],
        "bk": None,
        "fks": [
            ("cs_sold_date_sk", "date_dim", "d_date_sk"),
            ("cs_sold_time_sk", "time_dim", "t_time_sk"),
            ("cs_ship_date_sk", "date_dim", "d_date_sk"),
            ("cs_bill_customer_sk", "customer", "c_customer_sk"),
            ("cs_bill_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("cs_bill_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("cs_bill_addr_sk", "customer_address", "ca_address_sk"),
            ("cs_ship_customer_sk", "customer", "c_customer_sk"),
            ("cs_ship_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("cs_ship_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("cs_ship_addr_sk", "customer_address", "ca_address_sk"),
            ("cs_call_center_sk", "call_center", "cc_call_center_sk"),
            ("cs_catalog_page_sk", "catalog_page", "cp_catalog_page_sk"),
            ("cs_ship_mode_sk", "ship_mode", "sm_ship_mode_sk"),
            ("cs_warehouse_sk", "warehouse", "w_warehouse_sk"),
            ("cs_item_sk", "item", "i_item_sk"),
            ("cs_promo_sk", "promotion", "p_promo_sk"),
        ],
        "title": "Venta por catalogo",
    },
    "web_sales": {
        "category": "fact",
        "pk": ["ws_item_sk", "ws_order_number"],
        "bk": None,
        "fks": [
            ("ws_sold_date_sk", "date_dim", "d_date_sk"),
            ("ws_sold_time_sk", "time_dim", "t_time_sk"),
            ("ws_ship_date_sk", "date_dim", "d_date_sk"),
            ("ws_item_sk", "item", "i_item_sk"),
            ("ws_bill_customer_sk", "customer", "c_customer_sk"),
            ("ws_bill_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("ws_bill_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("ws_bill_addr_sk", "customer_address", "ca_address_sk"),
            ("ws_ship_customer_sk", "customer", "c_customer_sk"),
            ("ws_ship_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("ws_ship_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("ws_ship_addr_sk", "customer_address", "ca_address_sk"),
            ("ws_web_page_sk", "web_page", "wp_web_page_sk"),
            ("ws_web_site_sk", "web_site", "web_site_sk"),
            ("ws_ship_mode_sk", "ship_mode", "sm_ship_mode_sk"),
            ("ws_warehouse_sk", "warehouse", "w_warehouse_sk"),
            ("ws_promo_sk", "promotion", "p_promo_sk"),
        ],
        "title": "Venta web",
    },
    "store_returns": {
        "category": "fact",
        "pk": ["sr_item_sk", "sr_ticket_number"],
        "bk": None,
        "fks": [
            ("sr_returned_date_sk", "date_dim", "d_date_sk"),
            ("sr_return_time_sk", "time_dim", "t_time_sk"),
            ("sr_item_sk", "item", "i_item_sk"),
            ("sr_item_sk", "store_sales", "ss_item_sk"),
            ("sr_customer_sk", "customer", "c_customer_sk"),
            ("sr_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("sr_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("sr_addr_sk", "customer_address", "ca_address_sk"),
            ("sr_store_sk", "store", "s_store_sk"),
            ("sr_reason_sk", "reason", "r_reason_sk"),
            ("sr_ticket_number", "store_sales", "ss_ticket_number"),
        ],
        "title": "Devolucion en tienda",
    },
    "catalog_returns": {
        "category": "fact",
        "pk": ["cr_item_sk", "cr_order_number"],
        "bk": None,
        "fks": [
            ("cr_returned_date_sk", "date_dim", "d_date_sk"),
            ("cr_returned_time_sk", "time_dim", "t_time_sk"),
            ("cr_item_sk", "item", "i_item_sk"),
            ("cr_item_sk", "catalog_sales", "cs_item_sk"),
            ("cr_refunded_customer_sk", "customer", "c_customer_sk"),
            ("cr_refunded_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("cr_refunded_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("cr_refunded_addr_sk", "customer_address", "ca_address_sk"),
            ("cr_returning_customer_sk", "customer", "c_customer_sk"),
            ("cr_returning_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("cr_returning_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("cr_returning_addr_sk", "customer_address", "ca_address_sk"),
            ("cr_call_center_sk", "call_center", "cc_call_center_sk"),
            ("cr_catalog_page_sk", "catalog_page", "cp_catalog_page_sk"),
            ("cr_ship_mode_sk", "ship_mode", "sm_ship_mode_sk"),
            ("cr_warehouse_sk", "warehouse", "w_warehouse_sk"),
            ("cr_reason_sk", "reason", "r_reason_sk"),
            ("cr_order_number", "catalog_sales", "cs_order_number"),
        ],
        "title": "Devolucion de catalogo",
    },
    "web_returns": {
        "category": "fact",
        "pk": ["wr_item_sk", "wr_order_number"],
        "bk": None,
        "fks": [
            ("wr_returned_date_sk", "date_dim", "d_date_sk"),
            ("wr_returned_time_sk", "time_dim", "t_time_sk"),
            ("wr_item_sk", "item", "i_item_sk"),
            ("wr_item_sk", "web_sales", "ws_item_sk"),
            ("wr_refunded_customer_sk", "customer", "c_customer_sk"),
            ("wr_refunded_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("wr_refunded_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("wr_refunded_addr_sk", "customer_address", "ca_address_sk"),
            ("wr_returning_customer_sk", "customer", "c_customer_sk"),
            ("wr_returning_cdemo_sk", "customer_demographics", "cd_demo_sk"),
            ("wr_returning_hdemo_sk", "household_demographics", "hd_demo_sk"),
            ("wr_returning_addr_sk", "customer_address", "ca_address_sk"),
            ("wr_web_page_sk", "web_page", "wp_web_page_sk"),
            ("wr_reason_sk", "reason", "r_reason_sk"),
            ("wr_order_number", "web_sales", "ws_order_number"),
        ],
        "title": "Devolucion web",
    },
    "inventory": {
        "category": "fact",
        "pk": ["inv_date_sk", "inv_item_sk", "inv_warehouse_sk"],
        "bk": None,
        "fks": [
            ("inv_date_sk", "date_dim", "d_date_sk"),
            ("inv_item_sk", "item", "i_item_sk"),
            ("inv_warehouse_sk", "warehouse", "w_warehouse_sk"),
        ],
        "title": "Inventario diario",
    },
}

assert len(TABLES) == 24, "El esquema debe tener las 24 tablas de negocio de TPC-DS SF1"

DIM_FILL, DIM_HEADER, DIM_BORDER = "#d7e8f5", "#2f6690", "#9dc1de"
FACT_FILL, FACT_HEADER, FACT_BORDER = "#fbe1ce", "#b3441e", "#eab48f"
TEXT_DARK, TEXT_MUTED = "#1e2530", "#5b6572"
LINE_H = 0.30


def render_overview_diagram() -> None:
    """Diagrama E-R de las 24 tablas (Graphviz `dot`, una arista por par FK -> PK)."""
    lines = [
        "digraph tpcds_overview {",
        '  layout=fdp; overlap=false; splines=curved; K=1.1;',
        '  graph [fontname="Helvetica", nodesep=0.35, ranksep=1.1, concentrate=false, bgcolor="white"];',
        '  node [fontname="Helvetica", shape=box, style="rounded,filled", margin="0.12,0.08"];',
        '  edge [fontname="Helvetica", color="#9aa5b1", arrowsize=0.7, penwidth=0.9];',
    ]
    for name, t in TABLES.items():
        fill, border = (
            (FACT_FILL, FACT_BORDER) if t["category"] == "fact" else (DIM_FILL, DIM_BORDER)
        )
        pk = ", ".join(t["pk"])
        label = (
            '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="13"><B>{name}</B></FONT></TD></TR>'
            f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="9">PK: {pk}</FONT></TD></TR>'
            "</TABLE>>"
        )
        lines.append(
            f'  "{name}" [label={label}, fillcolor="{fill}", color="{border}", penwidth=1.4];'
        )

    seen = set()
    for name, t in TABLES.items():
        for _col, dst, _dstcol in t["fks"]:
            pair = (name, dst)
            if pair in seen or name == dst:
                continue
            seen.add(pair)
            lines.append(f'  "{name}" -> "{dst}";')

    lines += [
        "  subgraph cluster_legend {",
        '    label="Leyenda"; fontname="Helvetica"; fontsize=11; color="#c7ccd1"; style="rounded"; margin=12;',
        f'    legend_dim [label="dimension", shape=box, style="rounded,filled", fillcolor="{DIM_FILL}", color="{DIM_BORDER}"];',
        f'    legend_fact [label="hecho", shape=box, style="rounded,filled", fillcolor="{FACT_FILL}", color="{FACT_BORDER}"];',
        "    legend_dim -> legend_fact [style=invis];",
        "  }",
        "}",
    ]

    dot_path = IMG_DIR / "tpcds_er_overview.dot"
    dot_path.write_text("\n".join(lines))
    out_path = IMG_DIR / "tpcds_er_overview.png"
    subprocess.run(
        ["dot", "-Kfdp", "-Tpng", "-Gdpi=140", str(dot_path), "-o", str(out_path)], check=True
    )
    dot_path.unlink()
    print(f"generado {out_path}")


def _card_lines(t: dict) -> list[tuple[str, str]]:
    entries = [("desc", t["title"]), ("pk", "PK  " + ", ".join(t["pk"]))]
    if t["bk"]:
        entries.append(("bk", "BK  " + t["bk"]))
    for col, dst, dstcol in t["fks"]:
        entries.append(("fk", f"FK  {col} -> {dst}.{dstcol}"))
    return entries


def _draw_card(ax, x: float, y: float, w: float, h: float, name: str, t: dict) -> None:
    is_fact = t["category"] == "fact"
    fill, header, border = (
        (FACT_FILL, FACT_HEADER, FACT_BORDER) if is_fact else (DIM_FILL, DIM_HEADER, DIM_BORDER)
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y - h),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=0.08",
            linewidth=1.3,
            edgecolor=border,
            facecolor=fill,
            zorder=1,
        )
    )
    header_h = 0.34
    ax.add_patch(
        FancyBboxPatch(
            (x, y - header_h),
            w,
            header_h,
            boxstyle="round,pad=0,rounding_size=0.08",
            linewidth=0,
            edgecolor="none",
            facecolor=header,
            zorder=2,
        )
    )
    ax.add_patch(
        Rectangle((x, y - header_h), w, header_h / 2, facecolor=header, edgecolor="none", zorder=2)
    )
    ax.text(
        x + 0.12,
        y - header_h / 2,
        name,
        ha="left",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        color="white",
        zorder=3,
        family="monospace",
    )

    ty = y - header_h - 0.12
    for kind, text in _card_lines(t):
        if kind == "desc":
            ax.text(
                x + 0.12,
                ty,
                text,
                ha="left",
                va="top",
                fontsize=8.6,
                color=TEXT_MUTED,
                style="italic",
                family="sans-serif",
                zorder=3,
            )
        else:
            color = {"pk": "#8a5a00", "bk": "#3a5a1e", "fk": TEXT_DARK}[kind]
            weight = "bold" if kind == "pk" else "normal"
            ax.text(
                x + 0.12,
                ty,
                text,
                ha="left",
                va="top",
                fontsize=8.0,
                color=color,
                family="monospace",
                fontweight=weight,
                zorder=3,
            )
        ty -= LINE_H


def render_dimension_cards() -> None:
    """Ficha de referencia en rejilla para las tablas de dimensiones."""
    dims = {k: v for k, v in TABLES.items() if v["category"] == "dim"}
    n_lines = {k: len(_card_lines(v)) for k, v in dims.items()}
    header_h = 0.34
    card_w = 3.55
    cols = 4
    gap_x, gap_y = 0.32, 0.30
    names = list(dims.keys())
    rows = -(-len(names) // cols)

    row_heights = []
    for r in range(rows):
        chunk = names[r * cols : (r + 1) * cols]
        row_heights.append(header_h + 0.12 + LINE_H * max(n_lines[n] for n in chunk) + 0.16)

    fig_w = cols * card_w + (cols - 1) * gap_x + 0.6
    fig_h = sum(row_heights) + (rows - 1) * gap_y + 1.0

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(
        0.3,
        fig_h - 0.35,
        "TPC-DS SF1 — Tablas de dimensiones",
        ha="left",
        va="top",
        fontsize=20,
        fontweight="bold",
        color=TEXT_DARK,
        family="sans-serif",
    )
    ax.text(
        0.3,
        fig_h - 0.72,
        "PK = clave primaria   BK = clave de negocio   FK = clave ajena (columna -> tabla.columna)",
        ha="left",
        va="top",
        fontsize=11,
        color=TEXT_MUTED,
        family="sans-serif",
    )

    y_cursor = fig_h - 1.15
    for r in range(rows):
        chunk = names[r * cols : (r + 1) * cols]
        h = row_heights[r]
        for c, name in enumerate(chunk):
            x = 0.3 + c * (card_w + gap_x)
            _draw_card(ax, x, y_cursor, card_w, h, name, dims[name])
        y_cursor -= h + gap_y

    plt.tight_layout(pad=0.4)
    out_path = IMG_DIR / "tpcds_reference_dimensiones.png"
    plt.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"generado {out_path}")


def render_fact_cards() -> None:
    """Ficha de referencia en dos columnas para las tablas de hechos."""
    facts = {k: v for k, v in TABLES.items() if v["category"] == "fact"}
    header_h = 0.34
    card_w = 7.6
    gap_x, gap_y = 0.4, 0.32
    cols = 2

    n_lines = {k: len(_card_lines(v)) for k, v in facts.items()}
    heights = {k: header_h + 0.12 + LINE_H * n + 0.16 for k, n in n_lines.items()}

    order = sorted(facts.keys(), key=lambda k: -n_lines[k])
    col_totals = [0.0] * cols
    col_items: list[list[str]] = [[] for _ in range(cols)]
    for name in order:
        ci = min(range(cols), key=lambda i: col_totals[i])
        col_items[ci].append(name)
        col_totals[ci] += heights[name] + gap_y

    fig_w = cols * card_w + (cols - 1) * gap_x + 0.6
    fig_h = max(col_totals) + 1.0

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(
        0.3,
        fig_h - 0.35,
        "TPC-DS SF1 — Tablas de hechos",
        ha="left",
        va="top",
        fontsize=20,
        fontweight="bold",
        color=TEXT_DARK,
        family="sans-serif",
    )
    ax.text(
        0.3,
        fig_h - 0.72,
        "PK = clave primaria compuesta   FK = clave ajena (columna -> tabla.columna).",
        ha="left",
        va="top",
        fontsize=11,
        color=TEXT_MUTED,
        family="sans-serif",
    )

    for ci, names in enumerate(col_items):
        x = 0.3 + ci * (card_w + gap_x)
        y = fig_h - 1.15
        for name in names:
            h = heights[name]
            _draw_card(ax, x, y, card_w, h, name, facts[name])
            y -= h + gap_y

    plt.tight_layout(pad=0.4)
    out_path = IMG_DIR / "tpcds_reference_hechos.png"
    plt.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"generado {out_path}")


if __name__ == "__main__":
    IMG_DIR.mkdir(exist_ok=True)
    render_overview_diagram()
    render_dimension_cards()
    render_fact_cards()
