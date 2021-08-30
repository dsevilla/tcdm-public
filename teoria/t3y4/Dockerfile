FROM apache/zeppelin:0.10.0
MAINTAINER dsevilla@um.es
USER root
ENV LANG=es_ES.UTF-8 \ 
    JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV ZEPPELIN_ADDR=0.0.0.0
RUN echo "Instalando locales" && \
    apt-get -y update && \
    apt-get install -y locales 

RUN locale-gen $LANG &&\
    update-locale LANG=$LANG

RUN echo "Instalando paquetes adicionales" && \
    apt-get install -y netcat-openbsd 

ENV SPARK_VERSION=2.4.5 \
    HADOOP_VERSION=2.7 \
    SPARK_DIR=/usr/local 
ENV SPARK_HOME=${SPARK_DIR}/spark
RUN echo "Instalando Spark" && \ 
    mkdir -p ${SPARK_DIR} && \
    wget -O /tmp/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -zxf /tmp/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    rm -rf /tmp/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    mv -f spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_DIR} && \
    ln -s ${SPARK_DIR}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME}

EXPOSE 8080
EXPOSE 4040
