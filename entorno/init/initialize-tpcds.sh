#!/usr/bin/env sh

set -eu

TRINO_SERVER="${TRINO_SERVER:-http://trino-hdfs:8080}"
TPCDS_SCALE="${TPCDS_SCALE:-sf3}"
TPCDS_TABLES="${TPCDS_TABLES:-}"
TPCDS_DATALAKE_ROOT="${TPCDS_DATALAKE_ROOT:-/datalake/raw/tpcds}"
INE_MUNICIPALITIES_ROOT="${INE_MUNICIPALITIES_ROOT:-/datalake/raw/ine/municipios}"
DATALAKE_PATH="${TPCDS_DATALAKE_ROOT}"
WEBHDFS_URL="http://namenode:9870/webhdfs/v1"
INE_MUNICIPALITIES_FILE="/opt/tcdm/data/ine/municipios-2026.csv.gz"

# Las tablas que no se materializan con un SELECT * tienen su consulta en
# sql/select-<tabla>.sql. Son las mismas consultas que construye s2/s2.ipynb,
# y las tres listas dicen qué corrección lleva cada una: la geografía del INE,
# la vigencia de las versiones (dimensiones con rec_start_date y
# rec_end_date, y hechos cuya clave se reasigna a la versión vigente) y las
# claves de fecha y hora convertidas en columnas date y timestamp.
LOCALIZED_TABLES=' customer_address store warehouse web_site '
VERSIONED_TABLES=' item store web_page web_site store_sales store_returns web_returns '
DATE_TABLES=' store_sales web_sales store_returns web_returns inventory customer store promotion web_page web_site '

# Tablas del generador que no se materializan: dbgen_version describe el
# generador (y su columna time(3) no la admite el escritor Hive que se usa
# aquí), el curso no usa el canal de catálogo, y las claves que apuntaban a
# date_dim y time_dim se guardan ya como fechas.
EXCLUDED_TABLES=' dbgen_version catalog_sales catalog_returns catalog_page call_center date_dim time_dim '

# Contenido del marcador _SUCCESS de una tabla: las correcciones que lleva.
success_marker() {
    marker=''
    case "${LOCALIZED_TABLES}" in
        *" $1 "*) marker='INE-2026' ;;
    esac
    case "${VERSIONED_TABLES}" in
        *" $1 "*) marker="${marker:+${marker}+}SCD2" ;;
    esac
    case "${DATE_TABLES}" in
        *" $1 "*) marker="${marker:+${marker}+}FECHAS" ;;
    esac
    printf '%s' "${marker}"
}

echo '[*] Esperando a que WebHDFS responda...'
attempt=0
until curl --fail --silent \
    "${WEBHDFS_URL}/datalake?op=GETFILESTATUS&user.name=luser" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "${attempt}" -ge 60 ]; then
        echo 'WebHDFS no respondió o no existe /datalake' >&2
        exit 1
    fi
    sleep 2
done

echo '[*] Esperando a que Trino acepte consultas...'
attempt=0
until trino --server "${TRINO_SERVER}" --user luser --execute 'SELECT 1' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "${attempt}" -ge 60 ]; then
        echo 'Trino no aceptó consultas en el tiempo esperado' >&2
        exit 1
    fi
    sleep 2
done

echo 'SQL> SELECT 1'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute 'SELECT 1'

echo '[*] Creando en HDFS el esquema temporal de materialización...'
echo "WebHDFS> PUT ${WEBHDFS_URL}/warehouse/tpcds_bootstrap.db?op=MKDIRS&user.name=luser"
echo '[SALIDA <- WebHDFS]'
curl --fail --silent --show-error --request PUT \
    "${WEBHDFS_URL}/warehouse/tpcds_bootstrap.db?op=MKDIRS&user.name=luser" \
    | tee /dev/stderr \
    | grep -q '"boolean"[[:space:]]*:[[:space:]]*true'
echo 'SQL> CREATE SCHEMA IF NOT EXISTS hive.tpcds_bootstrap'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'CREATE SCHEMA IF NOT EXISTS hive.tpcds_bootstrap'

echo '[*] Publicando en HDFS la instantánea 2026 de municipios del INE...'
echo "WebHDFS> PUT ${WEBHDFS_URL}${INE_MUNICIPALITIES_ROOT}?op=MKDIRS&user.name=luser"
echo '[SALIDA <- WebHDFS]'
curl --fail --silent --show-error --request PUT \
    "${WEBHDFS_URL}${INE_MUNICIPALITIES_ROOT}?op=MKDIRS&user.name=luser" \
    | tee /dev/stderr \
    | grep -q '"boolean"[[:space:]]*:[[:space:]]*true'
echo '[*] Retirando, si existe, la copia CSV sin comprimir anterior...'
# Si se repite la inicialización sobre un HDFS antiguo, no dejamos dos
# ficheros en la ubicación externa: Trino leería ambos y duplicaría las filas.
curl --fail --silent --show-error --request DELETE \
    "${WEBHDFS_URL}${INE_MUNICIPALITIES_ROOT}/municipios-2026.csv?op=DELETE&recursive=true&user.name=luser" \
    >/dev/null 2>&1 || true
echo "WebHDFS> PUT ${WEBHDFS_URL}${INE_MUNICIPALITIES_ROOT}/municipios-2026.csv.gz?op=CREATE&overwrite=true&user.name=luser"
echo '[SALIDA <- WebHDFS]'
curl --fail --silent --show-error --location --request PUT \
    --header 'Content-Type: application/gzip' \
    --data-binary "@${INE_MUNICIPALITIES_FILE}" \
    "${WEBHDFS_URL}${INE_MUNICIPALITIES_ROOT}/municipios-2026.csv.gz?op=CREATE&overwrite=true&user.name=luser" \
    | tee /dev/stderr >/dev/null

echo 'SQL> Creando una tabla externa temporal sobre el CSV gzip del INE'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP VIEW IF EXISTS hive.tpcds_bootstrap.ine_municipios_ordenados'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP TABLE IF EXISTS hive.tpcds_bootstrap.ine_municipios'
trino --server "${TRINO_SERVER}" --user luser --execute \
    "CREATE TABLE hive.tpcds_bootstrap.ine_municipios (
        municipio_id varchar,
        provincia_id varchar,
        codigo_municipio varchar,
        digito_control varchar,
        municipio varchar,
        provincia varchar
    ) WITH (
        format = 'CSV',
        csv_separator = ';',
        skip_header_line_count = 1,
        external_location = 'hdfs://namenode:9000${INE_MUNICIPALITIES_ROOT}'
    )"

municipality_count="$(trino --server "${TRINO_SERVER}" --user luser \
    --output-format TSV --execute \
    'SELECT count(*) FROM hive.tpcds_bootstrap.ine_municipios')"
if [ "${municipality_count}" -ne 8132 ]; then
    echo "El catálogo del INE debía contener 8132 municipios y contiene ${municipality_count}" >&2
    exit 1
fi
echo "[OK] Catálogo del INE: ${municipality_count} municipios"

echo 'SQL> Creando una vista con una posición estable para cada código INE'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'CREATE VIEW hive.tpcds_bootstrap.ine_municipios_ordenados AS
     SELECT
         row_number() OVER (ORDER BY municipio_id) AS posicion,
         municipio_id,
         provincia_id,
         municipio,
         provincia
     FROM hive.tpcds_bootstrap.ine_municipios'

echo 'SQL> Creando una vista con la vigencia corregida de las versiones'
echo '[SALIDA <- trino]'
# El generador adelanta las fechas de vigencia de cada dimensión un número
# distinto de días respecto al primer día de datos (1998-01-01) y deja sin
# fecha de inicio algunas versiones de item. La vista deshace el adelanto y
# rellena esas fechas; la usan las dimensiones para corregir sus fechas y los
# hechos para apuntar a la versión vigente en la fecha de cada fila.
# También deja abierta la última versión de cada objeto: si el generador corta
# una dimensión en mitad de las versiones de un objeto (por ejemplo, 32 filas de
# store en sf3), la última que queda conserva su fecha de fin sin tener
# sucesora, y las ventas posteriores se quedarían sin versión vigente.
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP VIEW IF EXISTS hive.tpcds_bootstrap.vigencia_versiones'
trino --server "${TRINO_SERVER}" --user luser --execute \
    "CREATE VIEW hive.tpcds_bootstrap.vigencia_versiones AS
    WITH versiones AS (
        SELECT 'item' AS dimension, i_item_sk AS clave, i_item_id AS clave_negocio,
               i_rec_start_date AS inicio, i_rec_end_date AS fin
        FROM tpcds.${TPCDS_SCALE}.item
        UNION ALL
        SELECT 'store' AS dimension, s_store_sk AS clave, s_store_id AS clave_negocio,
               s_rec_start_date AS inicio, s_rec_end_date AS fin
        FROM tpcds.${TPCDS_SCALE}.store
        UNION ALL
        SELECT 'web_page' AS dimension, wp_web_page_sk AS clave, wp_web_page_id AS clave_negocio,
               wp_rec_start_date AS inicio, wp_rec_end_date AS fin
        FROM tpcds.${TPCDS_SCALE}.web_page
        UNION ALL
        SELECT 'web_site' AS dimension, web_site_sk AS clave, web_site_id AS clave_negocio,
               web_rec_start_date AS inicio, web_rec_end_date AS fin
        FROM tpcds.${TPCDS_SCALE}.web_site
    ),
    desplazadas AS (
        SELECT
            dimension,
            clave,
            clave_negocio,
            date_add('day', adelanto, inicio) AS inicio,
            date_add('day', adelanto, fin) AS fin
        FROM (
            SELECT
                *,
                date_diff(
                    'day', min(inicio) OVER (PARTITION BY dimension), DATE '1998-01-01'
                ) AS adelanto
            FROM versiones
        )
    )
    SELECT
        dimension,
        clave,
        clave_negocio,
        coalesce(
            inicio,
            date_add('day', 1, lag(fin) OVER (PARTITION BY dimension, clave_negocio ORDER BY clave)),
            DATE '1998-01-01'
        ) AS vigente_desde,
        CASE
            WHEN lead(clave) OVER (PARTITION BY dimension, clave_negocio ORDER BY clave) IS NULL
            THEN NULL
            ELSE fin
        END AS vigente_hasta
    FROM desplazadas"

if [ -z "${TPCDS_TABLES}" ]; then
    echo "SQL> SHOW TABLES FROM tpcds.${TPCDS_SCALE}"
    echo '[SALIDA <- trino]'
    tpcds_tables="$(trino --server "${TRINO_SERVER}" --user luser \
        --output-format TSV --execute "SHOW TABLES FROM tpcds.${TPCDS_SCALE}" \
    )"
    printf '%s\n' "${tpcds_tables}"
    TPCDS_TABLES="${tpcds_tables}"
fi

# TPCDS_TABLES es deliberadamente una lista de identificadores sin espacios.
# shellcheck disable=SC2086
for table_name in ${TPCDS_TABLES}; do
    case "${EXCLUDED_TABLES}" in
        *" ${table_name} "*)
            echo "[=] ${table_name}: excluida de la materialización"
            continue
            ;;
    esac

    success_url="${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=GETFILESTATUS&user.name=luser"
    table_url="${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}?op=DELETE&recursive=true&user.name=luser"
    select_file="/opt/tcdm/init/sql/select-${table_name}.sql"
    expected_marker="$(success_marker "${table_name}")"

    if curl --fail --silent "${success_url}" >/dev/null 2>&1; then
        actual_marker="$(curl --fail --silent --location \
            "${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=OPEN&user.name=luser")"
        if [ "${actual_marker}" = "${expected_marker}" ]; then
            echo "[=] ${table_name}: ya está materializada"
            continue
        fi
        echo "[*] ${table_name}: su marcador es '${actual_marker}' y debe ser '${expected_marker}'; se regenerará"
    fi

    echo "[*] ${table_name}: generando Parquet desde tpcds.${TPCDS_SCALE}.${table_name}"
    echo "SQL> DROP TABLE IF EXISTS hive.tpcds_bootstrap.${table_name}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "DROP TABLE IF EXISTS hive.tpcds_bootstrap.${table_name}"
    echo "WebHDFS> DELETE ${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}?op=DELETE&recursive=true&user.name=luser"
    curl --fail --silent --request DELETE "${table_url}" >/dev/null 2>&1 || true
    if test -e "${select_file}"; then
        echo "[*] ${table_name}: aplicando sus correcciones (${expected_marker})"
        # El total de municipios se sustituye por su valor, contado arriba: si la
        # unión comparase con una columna de la otra tabla, Trino no podría
        # resolverla como unión por igualdad y compararía cada fila con los 8132
        # municipios.
        select_query="$(sed \
            -e "s/__TPCDS_SCALE__/${TPCDS_SCALE}/g" \
            -e "s/__TOTAL_MUNICIPIOS__/${municipality_count}/g" \
            "${select_file}")"
    else
        select_query="SELECT * FROM tpcds.${TPCDS_SCALE}.${table_name}"
    fi
    echo "SQL> CREATE TABLE hive.tpcds_bootstrap.${table_name} WITH (format = 'PARQUET', external_location = 'hdfs://namenode:9000${DATALAKE_PATH}/${table_name}') AS ${select_query}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "CREATE TABLE hive.tpcds_bootstrap.${table_name} WITH (format = 'PARQUET', external_location = 'hdfs://namenode:9000${DATALAKE_PATH}/${table_name}') AS ${select_query}"

    echo "WebHDFS> PUT ${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=CREATE&overwrite=true&user.name=luser"
    echo '[SALIDA <- WebHDFS]'
    curl --fail --silent --location --request PUT \
        --header 'Content-Type: application/octet-stream' \
        --data-binary "${expected_marker}" \
        "${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=CREATE&overwrite=true&user.name=luser" \
        | tee /dev/stderr >/dev/null
    echo "SQL> DROP TABLE hive.tpcds_bootstrap.${table_name}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "DROP TABLE hive.tpcds_bootstrap.${table_name}"
done

echo 'SQL> DROP VIEW de la vigencia corregida'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP VIEW hive.tpcds_bootstrap.vigencia_versiones'

echo 'SQL> DROP VIEW y TABLE de lectura temporal del catálogo del INE'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP VIEW hive.tpcds_bootstrap.ine_municipios_ordenados'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP TABLE hive.tpcds_bootstrap.ine_municipios'

echo 'SQL> DROP SCHEMA IF EXISTS hive.tpcds_bootstrap'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'DROP SCHEMA IF EXISTS hive.tpcds_bootstrap'

echo "[OK] TPC-DS ${TPCDS_SCALE} está disponible como Parquet sin registrar en ${DATALAKE_PATH}"
