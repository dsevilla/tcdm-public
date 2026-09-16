ARG HIVE_IMAGE=apache/hive:4.2.1

FROM scratch AS postgresql-jdbc
ARG POSTGRES_JDBC_VERSION=42.7.13
ADD --checksum=sha256:6e0e4cc2d8cae902084f8a2b18728b073a6fd9d1f87c9d8bff8f298c18185b93 \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar \
    /postgresql.jar

FROM ${HIVE_IMAGE}

USER root
COPY --from=postgresql-jdbc --chown=hive:hive /postgresql.jar /opt/hive/lib/postgres.jar
USER hive
