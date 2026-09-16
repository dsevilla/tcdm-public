ARG SPARK_BASE_IMAGE=apache/spark:4.1.3-scala2.13-java21-python3-ubuntu
FROM ${SPARK_BASE_IMAGE}

ARG ICEBERG_VERSION=1.11.0

USER root

RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates curl \
    && curl --fail --silent --show-error --location \
        "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.1_2.13/${ICEBERG_VERSION}/iceberg-spark-runtime-4.1_2.13-${ICEBERG_VERSION}.jar" \
        --output "/opt/spark/jars/iceberg-spark-runtime-4.1_2.13-${ICEBERG_VERSION}.jar" \
    && curl --fail --silent --show-error --location \
        "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar" \
        --output "/opt/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar" \
    && rm -rf /var/lib/apt/lists/*

COPY spark-defaults.conf /opt/spark/conf/spark-defaults.conf

USER spark
