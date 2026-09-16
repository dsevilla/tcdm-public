#!/usr/bin/env sh

set -eu

TRINO_SERVER="${TRINO_SERVER:-http://trino-hdfs:8080}"
TPCDS_SCALE="${TPCDS_SCALE:-sf1}"
TPCDS_TABLES="${TPCDS_TABLES:-}"
TPCDS_DATALAKE_ROOT="${TPCDS_DATALAKE_ROOT:-/datalake/raw/tpcds}"
INE_MUNICIPALITIES_ROOT="${INE_MUNICIPALITIES_ROOT:-/datalake/raw/ine/municipios}"
DATALAKE_PATH="${TPCDS_DATALAKE_ROOT}"
WEBHDFS_URL="http://namenode:9870/webhdfs/v1"
INE_MUNICIPALITIES_FILE="/opt/tcdm/data/ine/municipios-2026.csv.gz"

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
         count(*) OVER () AS total_municipios,
         municipio_id,
         provincia_id,
         municipio,
         provincia
     FROM hive.tpcds_bootstrap.ine_municipios'

if [ -z "${TPCDS_TABLES}" ]; then
    echo "SQL> SHOW TABLES FROM tpcds.${TPCDS_SCALE}"
    echo '[SALIDA <- trino]'
    tpcds_tables="$(trino --server "${TRINO_SERVER}" --user luser \
        --output-format TSV --execute "SHOW TABLES FROM tpcds.${TPCDS_SCALE}" \
    )"
    printf '%s\n' "${tpcds_tables}"
    TPCDS_TABLES="$(printf '%s\n' "${tpcds_tables}" | grep -v '^dbgen_version$')"
fi

# TPCDS_TABLES es deliberadamente una lista de identificadores sin espacios.
# shellcheck disable=SC2086
for table_name in ${TPCDS_TABLES}; do
    # dbgen_version is metadata from the TPC-DS generator, not a business
    # table. Its time(3) column is not supported by the Hive writer used here.
    if [ "${table_name}" = 'dbgen_version' ]; then
        echo '[=] dbgen_version: tabla técnica excluida de la materialización'
        continue
    fi

    success_url="${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=GETFILESTATUS&user.name=luser"
    table_url="${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}?op=DELETE&recursive=true&user.name=luser"
    localization_query="/opt/tcdm/init/sql/localize-${table_name}.sql"

    if curl --fail --silent "${success_url}" >/dev/null 2>&1; then
        if ! test -e "${localization_query}" \
            || curl --fail --silent --location \
                "${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=OPEN&user.name=luser" \
                | grep -q '^INE-2026$'; then
            echo "[=] ${table_name}: ya está materializada"
            continue
        fi
        echo "[*] ${table_name}: existe sin la localización INE 2026; se regenerará"
    fi

    echo "[*] ${table_name}: generando Parquet desde tpcds.${TPCDS_SCALE}.${table_name}"
    echo "SQL> DROP TABLE IF EXISTS hive.tpcds_bootstrap.${table_name}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "DROP TABLE IF EXISTS hive.tpcds_bootstrap.${table_name}"
    echo "WebHDFS> DELETE ${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}?op=DELETE&recursive=true&user.name=luser"
    curl --fail --silent --request DELETE "${table_url}" >/dev/null 2>&1 || true
    if test -e "${localization_query}"; then
        echo "[*] ${table_name}: cruzando sus lugares con el catálogo municipal del INE"
        select_query="$(sed "s/__TPCDS_SCALE__/${TPCDS_SCALE}/g" "${localization_query}")"
    else
        select_query="SELECT * FROM tpcds.${TPCDS_SCALE}.${table_name}"
    fi
    echo "SQL> CREATE TABLE hive.tpcds_bootstrap.${table_name} WITH (format = 'PARQUET', external_location = 'hdfs://namenode:9000${DATALAKE_PATH}/${table_name}') AS ${select_query}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "CREATE TABLE hive.tpcds_bootstrap.${table_name} WITH (format = 'PARQUET', external_location = 'hdfs://namenode:9000${DATALAKE_PATH}/${table_name}') AS ${select_query}"

    echo "WebHDFS> PUT ${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=CREATE&overwrite=true&user.name=luser"
    echo '[SALIDA <- WebHDFS]'
    success_content=''
    if test -e "${localization_query}"; then
        success_content='INE-2026'
    fi
    curl --fail --silent --location --request PUT \
        --header 'Content-Type: application/octet-stream' \
        --data-binary "${success_content}" \
        "${WEBHDFS_URL}${DATALAKE_PATH}/${table_name}/_SUCCESS?op=CREATE&overwrite=true&user.name=luser" \
        | tee /dev/stderr >/dev/null
    echo "SQL> DROP TABLE hive.tpcds_bootstrap.${table_name}"
    echo '[SALIDA <- trino]'
    trino --server "${TRINO_SERVER}" --user luser --execute \
        "DROP TABLE hive.tpcds_bootstrap.${table_name}"
done

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
