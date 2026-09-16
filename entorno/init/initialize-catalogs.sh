#!/usr/bin/env sh

set -eu

TRINO_SERVER="${TRINO_SERVER:-http://trino-hdfs:8080}"
WEBHDFS_SERVER="${WEBHDFS_SERVER:-http://namenode:9870}"

echo '[*] Esperando a que WebHDFS responda...'
attempt=0
until curl --fail --silent \
    "${WEBHDFS_SERVER}/webhdfs/v1/warehouse?op=GETFILESTATUS&user.name=luser" \
    >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "${attempt}" -ge 60 ]; then
        echo 'WebHDFS no respondió o no existe /warehouse' >&2
        exit 1
    fi
    sleep 2
done

echo '[*] Creando en HDFS la ubicación convencional del esquema tcdm...'
echo "WebHDFS> PUT ${WEBHDFS_SERVER}/webhdfs/v1/warehouse/tcdm.db?op=MKDIRS&user.name=luser"
warehouse_response="$(curl --fail --silent --show-error --request PUT \
    "${WEBHDFS_SERVER}/webhdfs/v1/warehouse/tcdm.db?op=MKDIRS&user.name=luser" \
    )"
echo '[SALIDA <- WebHDFS]'
printf '%s\n' "$warehouse_response"
printf '%s\n' "$warehouse_response" \
    | grep -Eq '"boolean"[[:space:]]*:[[:space:]]*true'

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

echo '[*] Creando el espacio de nombres compartido por Hive e Iceberg...'
echo 'SQL> CREATE SCHEMA IF NOT EXISTS hive.tcdm'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'CREATE SCHEMA IF NOT EXISTS hive.tcdm'

echo '[*] Comprobando los tres catálogos docentes...'
echo "SQL> SHOW SCHEMAS FROM hive LIKE 'tcdm'"
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    "SHOW SCHEMAS FROM hive LIKE 'tcdm'"
echo "SQL> SHOW SCHEMAS FROM iceberg LIKE 'tcdm'"
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    "SHOW SCHEMAS FROM iceberg LIKE 'tcdm'"
echo 'SQL> SHOW SCHEMAS FROM tpcds'
echo '[SALIDA <- trino]'
trino --server "${TRINO_SERVER}" --user luser --execute \
    'SHOW SCHEMAS FROM tpcds'

echo '[OK] Hive Metastore, HDFS, Trino y los catálogos responden correctamente'
