ARG HIVE_IMAGE=apache/hive:standalone-metastore-4.2.1

FROM scratch AS postgresql-jdbc
ARG POSTGRES_JDBC_VERSION=42.7.13
ADD --checksum=sha256:6e0e4cc2d8cae902084f8a2b18728b073a6fd9d1f87c9d8bff8f298c18185b93 \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar \
    /postgresql.jar

# Imagen oficial del metastore independiente (multiarquitectura: amd64 y arm64).
# Sólo le falta el driver JDBC de PostgreSQL. Su entrypoint ejecuta
# `schematool -initOrUpgradeSchema`, que crea el esquema en el primer arranque
# y no hace nada en los siguientes, así que no necesita envoltorio.
FROM ${HIVE_IMAGE}

COPY --from=postgresql-jdbc --chown=hive:hive /postgresql.jar /opt/hive/lib/postgres.jar
