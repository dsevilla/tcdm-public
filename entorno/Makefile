# Compose reads .env automatically, but the upload script is a host process and
# needs the same bucket name explicitly. Include only the optional local file
# so a fresh checkout still works with the documented defaults.
-include .env

S3_BUCKET ?= tcdm-datalake
export S3_BUCKET

TPCDS_DATALAKE_ROOT ?= /datalake/raw/tpcds
TPCDS_SCALE ?= sf1
INE_MUNICIPALITIES_ROOT ?= /datalake/raw/ine/municipios
TPCDS_PATH := $(TPCDS_DATALAKE_ROOT)
export INE_MUNICIPALITIES_ROOT TPCDS_DATALAKE_ROOT TPCDS_SCALE TPCDS_TABLES

HADOOP_COMPOSE := docker compose -f compose-hadoop-cluster.yml
WAREHOUSE_COMPOSE := docker compose -f compose-warehouse-hdfs.yml
S3_COMPOSE := docker compose -f compose-s3.yml
.PHONY: network hadoop-up warehouse-up tpcds-init tpcds-size s3-up status stop clean

network:
	docker network inspect hadoop-cluster >/dev/null 2>&1 || docker network create hadoop-cluster

hadoop-up: network
	$(HADOOP_COMPOSE) up -d

warehouse-up: hadoop-up
	$(WAREHOUSE_COMPOSE) up -d --build

tpcds-init: warehouse-up
	$(WAREHOUSE_COMPOSE) run --rm tpcds-init
	$(MAKE) --no-print-directory tpcds-size

# Muestra el tamaño de los datos lógicos y el espacio realmente consumido por
# HDFS después de aplicar el factor de replicación.
tpcds-size: hadoop-up
	echo "[ORDEN -> namenode] hdfs dfs -du -h $(TPCDS_PATH)"
	docker exec namenode su - luser -c \
		"hdfs dfs -du -h '$(TPCDS_PATH)'"
	echo "[ORDEN -> namenode] hdfs dfs -du -h -s $(TPCDS_PATH)"
	echo '[INFO] Primera columna: tamaño lógico; segunda: espacio HDFS con réplicas.'
	docker exec namenode su - luser -c \
		"hdfs dfs -du -h -s '$(TPCDS_PATH)'"

s3-up: network
	$(S3_COMPOSE) up -d

status:
	$(HADOOP_COMPOSE) ps
	$(WAREHOUSE_COMPOSE) ps -a
	$(S3_COMPOSE) ps -a

stop:
	$(S3_COMPOSE) down
	$(WAREHOUSE_COMPOSE) down
	$(HADOOP_COMPOSE) down

clean:
	$(S3_COMPOSE) down -v
	$(WAREHOUSE_COMPOSE) down -v
	$(HADOOP_COMPOSE) down
