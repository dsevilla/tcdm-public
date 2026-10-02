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

# Nombres explícitos declarados en compose-hadoop-cluster.yml; deben
# coincidir con los `volumes:.name:` de ese fichero.
HDFS_VOLUMES := tcdm-26-27-namenode-data tcdm-26-27-datanode1-data \
	tcdm-26-27-datanode2-data tcdm-26-27-datanode3-data

.PHONY: network hadoop-up warehouse-up tpcds-init tpcds-size s3-up jupyter status stop clean clean-hdfs

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

# Arranca Jupyter Lab dentro de namenode como luser, con el entorno Python del
# curso (/opt/tcdm/venv). El token es siempre «tcdm» (el puerto 8888 sólo se
# publica en 127.0.0.1), así que la dirección que hay que pegar en Visual
# Studio Code es http://127.0.0.1:8888/lab?token=tcdm. Queda en primer plano y
# se detiene con Ctrl+C; la terminal debe quedar abierta mientras se trabaja
# con el notebook.
jupyter:
	docker exec -it namenode su - luser -c 'jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --IdentityProvider.token=tcdm'

# La distribución de cada sesión sólo incluye los Compose que ya se usan. Los
# de sesiones posteriores se omiten sin error mientras no se hayan publicado.
status:
	$(HADOOP_COMPOSE) ps
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) ps -a; fi
	if test -e compose-s3.yml; then $(S3_COMPOSE) ps -a; fi

# Elimina los contenedores. Los datos HDFS sobreviven porque viven en los
# volúmenes con nombre de compose-hadoop-cluster.yml (namenode-data,
# datanodeN-data), no en la capa de escritura de los contenedores: un
# `up -d` posterior los reutiliza tal cual. Usa `clean-hdfs` para borrarlos.
stop:
	if test -e compose-s3.yml; then $(S3_COMPOSE) down; fi
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) down; fi
	$(HADOOP_COMPOSE) down

# Además de parar y eliminar los contenedores, borra el volumen de
# metadatos de PostgreSQL (Hive Metastore) y el de S3. El HDFS de Hadoop no
# se toca aquí: usa `clean-hdfs` para eso, de forma explícita y separada.
clean:
	if test -e compose-s3.yml; then $(S3_COMPOSE) down -v; fi
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) down -v; fi
	$(HADOOP_COMPOSE) down

# Borra también los datos HDFS (namenode y los tres datanode). Es la única
# orden de este Makefile que destruye el dataset TPC-DS/INE ya materializado
# junto con el espacio de nombres; requiere que los contenedores ya estén
# eliminados, así que primero ejecuta `clean`.
clean-hdfs: clean
	docker volume rm -f $(HDFS_VOLUMES)
