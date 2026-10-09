#!/bin/bash
# El entrypoint de apache/hive:3.1.3 ejecuta siempre `schematool -initSchema`,
# que falla si las tablas ya existen ("relation ... already exists"). Como el
# esquema vive en el volumen de PostgreSQL, eso rompe cualquier arranque
# posterior al primero (`make stop` + `warehouse-up`, o `down` + `warehouse-up`).
# El entrypoint de la imagen sólo se salta ese paso con IS_RESUME=true, así
# que aquí se comprueba antes si el esquema ya está creado.

schema_exists() {
    HADOOP_CLIENT_OPTS="${SERVICE_OPTS:-}" \
        "${HIVE_HOME}/bin/schematool" -dbType "${DB_DRIVER:-derby}" -info \
        >/dev/null 2>&1
}

if [[ -z "${IS_RESUME:-}" ]] && schema_exists; then
    echo "El esquema del metastore ya existe: no se vuelve a inicializar."
    export IS_RESUME=true
fi

exec /entrypoint.sh "$@"
