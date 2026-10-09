"""Consulta del esquema de TPC-DS SF1 desde cualquier notebook del curso.

El catálogo de las 24 tablas —qué significa cada columna, su tipo y sus
claves— está escrito una sola vez, en el apéndice de `s2/s2.ipynb`. Este
módulo lo lee de ahí y lo muestra a petición, para no tener que ir al
apéndice cada vez que una consulta usa una tabla que no se recuerda:

    %load_ext tcdm_esquema

    %esquema                        las 24 tablas, con su papel y descripción
    %esquema web_sales              la tabla completa, con todas sus columnas
    %esquema web_sales date         las columnas de web_sales que contienen «date»
    %esquema ws_sold_date_sk        esa columna y ninguna otra
    %esquema item_sk                todas las columnas «item_sk», tabla a tabla
    %esquema web_sales customer     varias tablas seguidas

`%%esquema` hace lo mismo con una tabla, columna o filtro por línea, y
admite comentarios con `#`. Desde Python, `esquema("web_sales", "date")`
devuelve el mismo resultado.

El kernel de las sesiones se ejecuta en `namenode`, que no ve la copia local
de la distribución: el apéndice se descarga del repositorio público
`dsevilla/tcdm-public`, una vez por kernel. Si hay un `s2.ipynb` en el
directorio de trabajo, se usa ese.

Como programa, comprueba que el apéndice de un notebook sigue teniendo el
formato que este módulo sabe leer (lo usa el CI):

    python tcdm_esquema.py --check s2/s2.ipynb
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, cast
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.display import Markdown

type Role = Literal["dimensión", "hecho"]
type ForeignKey = tuple[str, str]
type NotebookJson = dict[str, Any]
type NotebookSource = str | Path

S2_URL: Final[str] = "https://raw.githubusercontent.com/dsevilla/tcdm-public/26-27/s2/s2.ipynb"
S2_LOCAL: Final[tuple[Path, ...]] = (Path("s2.ipynb"), Path("../s2/s2.ipynb"))

APPENDIX_ANCHOR: Final[str] = 'id="apendice-tpcds-sf1"'
SECTIONS: Final[dict[str, Role]] = {
    "### Dimensiones y tablas auxiliares": "dimensión",
    "### Tablas de hechos": "hecho",
}
TABLE_HEADING: Final[re.Pattern[str]] = re.compile(r"^#### `(\w+)`\s*$")
FOREIGN_KEY: Final[re.Pattern[str]] = re.compile(r"^FK → (\w+)\.(\w+)$")
PRIMARY_KEY: Final[re.Pattern[str]] = re.compile(r"^PK(?: \((\d+)/(\d+)\))?$")
EXPECTED_TABLES: Final[dict[Role, int]] = {"dimensión": 17, "hecho": 7}
PLAIN_KEYS: Final[frozenset[str]] = frozenset({"BK", "—"})


@dataclass(frozen=True, slots=True)
class Column:
    """Una fila de la tabla Markdown de una tabla del apéndice."""

    name: str
    type: str
    description: str
    key: str
    # La fila tal como está escrita en el apéndice, para mostrarla igual.
    row: str

    @property
    def key_parts(self) -> list[str]:
        return [part.strip() for part in self.key.split(";")]

    @property
    def is_primary_key(self) -> bool:
        return any(PRIMARY_KEY.match(part) for part in self.key_parts)

    @property
    def is_business_key(self) -> bool:
        return "BK" in self.key_parts

    @property
    def references(self) -> list[ForeignKey]:
        """Pares (tabla, columna) a los que apunta esta columna como clave ajena."""
        matches: Iterator[re.Match[str] | None] = (
            FOREIGN_KEY.match(part) for part in self.key_parts
        )
        return [(match[1], match[2]) for match in matches if match]


@dataclass(slots=True)
class Table:
    """Una tabla del apéndice: su texto, la cabecera de la tabla Markdown y sus columnas."""

    name: str
    role: Role
    description: str = ""
    header: list[str] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)

    @property
    def primary_key(self) -> list[str]:
        return [column.name for column in self.columns if column.is_primary_key]


type Schema = dict[str, Table]


@dataclass(frozen=True, slots=True)
class Arguments:
    """Argumentos de la línea de órdenes."""

    terms: list[str]
    notebook: str | None
    check: str | None


class SchemaError(Exception):
    """El apéndice no tiene el formato que este módulo sabe leer."""


def appendix_cells(notebook: NotebookJson) -> list[str]:
    """Texto de las celdas Markdown del apéndice de esquema de un notebook."""
    cells: list[str] = [
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"
    ]
    for index, text in enumerate(cells):
        if APPENDIX_ANCHOR in text:
            return cells[index:]
    raise SchemaError(f"El notebook no tiene el apéndice de esquema ({APPENDIX_ANCHOR}).")


def parse_appendix(cells: Sequence[str]) -> Schema:
    """Convierte las celdas del apéndice en tablas, en el orden en que aparecen."""
    tables: Schema = {}
    role: Role | None = None
    for text in cells:
        lines: list[str] = text.strip().splitlines()
        if not lines:
            continue
        if lines[0] in SECTIONS:
            role = SECTIONS[lines[0]]
            continue
        heading: re.Match[str] | None = TABLE_HEADING.match(lines[0])
        if not heading:
            continue
        name: str = heading[1]
        if role is None:
            raise SchemaError(f"`{name}` aparece antes de las secciones de dimensiones y hechos.")
        if name in tables:
            raise SchemaError(f"`{name}` aparece dos veces en el apéndice.")
        tables[name] = _parse_table(name, role, lines[1:])
    return tables


def _parse_table(name: str, role: Role, lines: Sequence[str]) -> Table:
    rows: list[str] = [line for line in lines if line.startswith("|")]
    prose: list[str] = [line for line in lines if not line.startswith("|")]
    table: Table = Table(name, role, description=" ".join(" ".join(prose).split()), header=rows[:2])
    for row in rows[2:]:
        cells: list[str] = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != 4:
            raise SchemaError(f"`{name}`: se esperaban 4 celdas en la fila {row!r}.")
        column, type_, description, key = cells
        table.columns.append(Column(column.strip("`"), type_.strip("`"), description, key, row))
    return table


def check_schema(tables: Schema) -> list[str]:
    """Problemas del apéndice que harían fallar o mentir a `%esquema`."""
    problems: list[str] = []
    for role, expected in EXPECTED_TABLES.items():
        found: int = sum(1 for table in tables.values() if table.role == role)
        if found != expected:
            problems.append(f"Hay {found} tablas con papel «{role}» y se esperaban {expected}.")
    for table in tables.values():
        names: list[str] = [column.name for column in table.columns]
        if not table.description:
            problems.append(f"`{table.name}` no tiene texto de descripción.")
        if len(table.header) != 2 or not names:
            problems.append(f"`{table.name}` no tiene una tabla Markdown de columnas.")
        if len(names) != len(set(names)):
            problems.append(f"`{table.name}` repite alguna columna.")
        if not table.primary_key:
            problems.append(f"`{table.name}` no marca ninguna columna como PK.")
        for column in table.columns:
            problems.extend(_check_column(tables, table, column))
    return problems


def _check_column(tables: Schema, table: Table, column: Column) -> list[str]:
    where: str = f"`{table.name}.{column.name}`"
    key_size: int = len(table.primary_key)
    problems: list[str] = []
    if not column.type or not column.description:
        problems.append(f"{where} no tiene tipo o descripción.")
    for part in column.key_parts:
        primary: re.Match[str] | None = PRIMARY_KEY.match(part)
        if primary and primary[2] and int(primary[2]) != key_size:
            problems.append(f"{where} dice «{part}», pero la tabla marca {key_size} PK.")
        if not (primary or FOREIGN_KEY.match(part) or part in PLAIN_KEYS):
            problems.append(f"{where}: no se entiende la clave «{part}».")
    for target_table, target_column in column.references:
        target: Table | None = tables.get(target_table)
        if target is None or target_column not in {c.name for c in target.columns}:
            problems.append(f"{where} apunta a `{target_table}.{target_column}`, que no existe.")
    return problems


_schema: Schema | None = None


def load_schema(source: NotebookSource | None = None) -> Schema:
    """Lee el apéndice de `source` (ruta o URL), o del `s2.ipynb` local o publicado.

    Sin `source`, el resultado se conserva: el apéndice se lee una vez por kernel.
    """
    global _schema
    if source is not None:
        return parse_appendix(appendix_cells(_read_notebook(source)))
    if _schema is None:
        default: NotebookSource = next((path for path in S2_LOCAL if path.is_file()), S2_URL)
        _schema = parse_appendix(appendix_cells(_read_notebook(default)))
    return _schema


def _read_notebook(source: NotebookSource) -> NotebookJson:
    try:
        if isinstance(source, Path) or "://" not in source:
            return cast(NotebookJson, json.loads(Path(source).read_text(encoding="utf-8")))
        request: Request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            return cast(NotebookJson, json.loads(response.read()))
    except OSError as error:
        raise SchemaError(
            f"No se ha podido leer el apéndice de esquema de {source}: {error}. "
            "Si es una descarga, comprueba la conexión del contenedor y vuelve a "
            "ejecutar la celda."
        ) from error


def schema_markdown(*terms: str, source: NotebookSource | None = None) -> str:
    """Markdown con las tablas y columnas que piden `terms`.

    Un término que es el nombre de una tabla la selecciona. Los demás filtran
    columnas, dentro de las tablas seleccionadas o, si no se ha seleccionado
    ninguna, en las 24: el nombre completo de una columna la elige a ella, y
    cualquier otro texto, a las columnas cuyo nombre lo contiene. Sin términos,
    lista las tablas.
    """
    tables: Schema = load_schema(source)
    if not terms:
        return _index_markdown(tables)

    names: list[str] = [term for term in terms if term in tables]
    filters: list[str] = [term.lower() for term in terms if term not in tables]
    selected: list[Table] = [tables[name] for name in dict.fromkeys(names)] or list(tables.values())
    # Un filtro que es el nombre completo de una columna sólo la elige a ella:
    # `ws_net_paid` no trae también `ws_net_paid_inc_tax`.
    known: set[str] = {column.name for table in selected for column in table.columns}
    exact: set[str] = {text for text in filters if text in known}
    partial: list[str] = [text for text in filters if text not in exact]
    blocks: list[str] = []
    for table in selected:
        columns: list[Column] = [
            column
            for column in table.columns
            if not filters
            or column.name in exact
            or any(text in column.name.lower() for text in partial)
        ]
        if columns:
            blocks.append(_table_markdown(table, columns))
    if blocks:
        return "\n\n".join(blocks)
    return _not_found_markdown(tables, filters, names)


def _index_markdown(tables: Schema) -> str:
    lines: list[str] = ["| Tabla | Papel | Columnas | Descripción |", "| --- | --- | ---: | --- |"]
    lines += [
        f"| `{table.name}` | {table.role} | {len(table.columns)} | {table.description} |"
        for table in tables.values()
    ]
    return "\n".join(lines)


def _table_markdown(table: Table, columns: Sequence[Column]) -> str:
    title: str = f"#### `{table.name}` — {table.role}"
    rows: list[str] = [*table.header, *(column.row for column in columns)]
    if len(columns) == len(table.columns):
        return "\n".join([title, "", table.description, "", *rows])
    return "\n".join([f"{title} ({len(columns)} de {len(table.columns)} columnas)", "", *rows])


def _not_found_markdown(tables: Schema, filters: Sequence[str], names: Sequence[str]) -> str:
    known: list[str] = [
        *tables,
        *(column.name for table in tables.values() for column in table.columns),
    ]
    close: list[str] = [
        match for text in filters for match in difflib.get_close_matches(text, known, n=4)
    ]
    wanted: str = " o ".join(f"«{text}»" for text in filters)
    where: str = " en " + ", ".join(f"`{name}`" for name in names) if names else ""
    hint: str = (
        " Quizá buscabas " + ", ".join(f"`{match}`" for match in dict.fromkeys(close)) + "."
        if close
        else " `%esquema` sin argumentos lista las 24 tablas."
    )
    return f"No hay ninguna columna cuyo nombre contenga {wanted}{where}.{hint}"


def esquema(*terms: str) -> Markdown:
    """Como `%esquema`, desde Python: `esquema("web_sales", "date")`."""
    from IPython.display import Markdown

    return Markdown(schema_markdown(*terms))


def _magic(line: str, cell: str | None = None) -> None:
    from IPython.display import display

    # En `%%esquema`, lo que sigue a `#` en una línea es un comentario.
    body: str = " ".join(text.partition("#")[0] for text in (cell or "").splitlines())
    terms: list[str] = [term for term in re.split(r"[\s,]+", f"{line} {body}") if term]
    display(esquema(*terms))


_magic.__doc__ = __doc__


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """Registra `%esquema` y `%%esquema`; lo llama `%load_ext tcdm_esquema`."""
    # Se registra en el gestor de magias y no con `ipython.register_magic_function`,
    # que hace lo mismo pero está declarado con la firma del método del gestor:
    # un comprobador de tipos toma ahí la función por `self` y echa en falta `func`.
    ipython.magics_manager.register_function(_magic, magic_kind="line_cell", magic_name="esquema")


def parse_arguments(argv: Sequence[str] | None = None) -> Arguments:
    """Convertir los argumentos de la línea de órdenes en un objeto tipado."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Consulta o comprueba el esquema TPC-DS del curso."
    )
    parser.add_argument(
        "terms", nargs="*", help="tablas, columnas o partes del nombre de una columna"
    )
    parser.add_argument(
        "--notebook", help="ruta o URL de s2.ipynb (por defecto, el local o el publicado)"
    )
    parser.add_argument(
        "--check",
        metavar="NOTEBOOK",
        help="comprueba que el apéndice de NOTEBOOK tiene el formato esperado",
    )
    namespace: argparse.Namespace = parser.parse_args(argv)
    return Arguments(
        terms=cast(list[str], namespace.terms),
        notebook=cast(str | None, namespace.notebook),
        check=cast(str | None, namespace.check),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Mostrar lo que se pide o, con `--check`, comprobar el apéndice."""
    args: Arguments = parse_arguments(argv)
    try:
        if args.check is None:
            print(schema_markdown(*args.terms, source=args.notebook))
            return 0
        tables: Schema = load_schema(args.check)
    except SchemaError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    problems: list[str] = check_schema(tables)
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    columns: int = sum(len(table.columns) for table in tables.values())
    print(f"{args.check}: {len(tables)} tablas, {columns} columnas, {len(problems)} problema(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
