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

.PHONY: actualizar network hadoop-up warehouse-up tpcds-init tpcds-size s3-up jupyter status stop down clean clean-hdfs

# Trae la última versión publicada del material sin fusionar nada, para que
# nunca haya conflictos que resolver. Sustituye a `git pull`, que se niega a
# actualizar cuando se ha publicado una corrección de un fichero que ya se
# había modificado en local (ejecutar un notebook lo modifica, porque guarda
# sus salidas).
#
# Cada fichero modificado en local que también cambia en la versión nueva se
# aparta como copia junto al original (s2/s2.ipynb pasa a
# s2/s2.mio-<fecha>-<hora>.ipynb) y el original se sustituye por el publicado.
# Lo mismo se hace con un fichero propio cuyo nombre coincida con uno que la
# versión nueva añade. Los cambios locales en ficheros que la versión nueva no
# toca se quedan como están. No se borra ni se sobrescribe ningún trabajo.
actualizar:
	@set -eu; \
	cd "$$(git rev-parse --show-toplevel)"; \
	remoto=$$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || { \
		echo "ERROR: esta copia no sigue ninguna rama publicada; vuelve a clonar el material." >&2; \
		exit 1; \
	}; \
	git fetch --quiet; \
	if test -n "$$(git rev-list "$$remoto..HEAD")"; then \
		echo "ERROR: esta copia tiene commits propios, así que no se puede avanzar sin fusionar." >&2; \
		echo "Guarda tu trabajo en otra rama (git branch mi-trabajo) y vuelve a $$remoto con" >&2; \
		echo "  git reset --keep $$remoto" >&2; \
		exit 1; \
	fi; \
	if test -z "$$(git rev-list "HEAD..$$remoto")"; then \
		echo "El material ya está actualizado."; \
		exit 0; \
	fi; \
	marca=$$(date +%Y%m%d-%H%M%S); \
	apartados=0; \
	apartar() { \
		case "$${2##*/}" in \
			?*.*) copia="$${2%.*}.mio-$$marca.$${2##*.}" ;; \
			*) copia="$$2.mio-$$marca" ;; \
		esac; \
		$$1 -- "$$2" "$$copia"; \
		echo "  $$2 -> $$copia"; \
		apartados=$$((apartados + 1)); \
	}; \
	lista=$$(mktemp); \
	trap 'rm -f "$$lista"' EXIT; \
	git diff --name-only HEAD > "$$lista"; \
	while IFS= read -r fichero; do \
		git diff --quiet HEAD "$$remoto" -- "$$fichero" && continue; \
		if git cat-file -e "HEAD:$$fichero" 2>/dev/null; then \
			if test -e "$$fichero"; then apartar "cp -p" "$$fichero"; fi; \
			git checkout --quiet HEAD -- "$$fichero"; \
		else \
			git rm --cached --quiet -- "$$fichero"; \
			apartar mv "$$fichero"; \
		fi; \
	done < "$$lista"; \
	git diff --name-only --diff-filter=A HEAD "$$remoto" > "$$lista"; \
	while IFS= read -r fichero; do \
		test -e "$$fichero" || continue; \
		apartar mv "$$fichero"; \
	done < "$$lista"; \
	git merge --ff-only --quiet "$$remoto"; \
	echo "Material actualizado a la última versión publicada."; \
	if test "$$apartados" -gt 0; then \
		echo "Se han apartado $$apartados fichero(s) tuyos (líneas de arriba): tu versión está en la"; \
		echo "copia «.mio-$$marca» y el fichero original es ahora el publicado."; \
	fi

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
# `ps -a` muestra también los contenedores parados con `make stop`.
status:
	$(HADOOP_COMPOSE) ps -a
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) ps -a; fi
	if test -e compose-s3.yml; then $(S3_COMPOSE) ps -a; fi

# Parar y borrar: cuatro órdenes, de menos a más destructiva.
#
#   stop        para los contenedores       conserva todo
#   down        elimina los contenedores    conserva los volúmenes
#   clean       down + borra volúmenes      conserva sólo HDFS
#   clean-hdfs  clean + borra HDFS          no conserva ningún dato
#
# Después de cualquiera de ellas se vuelve a arrancar con `hadoop-up`,
# `warehouse-up` o `s3-up`.

# Para los contenedores sin eliminarlos. No se pierde nada: ni los volúmenes
# ni lo que hay dentro de cada contenedor (ficheros del directorio de trabajo
# de Jupyter en namenode, /tmp, histórico del Timeline Server). Un `up -d`
# posterior reanuda los mismos contenedores. Lo único que no vuelve solo es
# Jupyter, que hay que lanzar de nuevo.
stop:
	if test -e compose-s3.yml; then $(S3_COMPOSE) stop; fi
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) stop; fi
	$(HADOOP_COMPOSE) stop

# Elimina los contenedores y conserva los volúmenes. Sobreviven los datos
# HDFS (volúmenes namenode-data y datanodeN-data de
# compose-hadoop-cluster.yml), los metadatos del Hive Metastore y los objetos
# de S3: un `up -d` posterior crea contenedores nuevos sobre esos mismos
# volúmenes. Se pierde lo que vivía en la capa de escritura de los
# contenedores.
down:
	if test -e compose-s3.yml; then $(S3_COMPOSE) down; fi
	if test -e compose-warehouse-hdfs.yml; then $(WAREHOUSE_COMPOSE) down; fi
	$(HADOOP_COMPOSE) down

# Como `down`, y además borra el volumen de metadatos de PostgreSQL (Hive
# Metastore) y el de S3. El HDFS de Hadoop no se toca aquí: usa `clean-hdfs`
# para eso, de forma explícita y separada.
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
