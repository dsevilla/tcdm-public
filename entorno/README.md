# Entorno 26-27: Hadoop, data lake y warehouse

En la distribución para el alumnado, este directorio (`entorno/`) es hermano
de `s1/`, `s2/`, ..., `s8/`. Los notebooks lo referencian con `../entorno/...`
porque el directorio de trabajo del kernel de Jupyter es el propio directorio
del notebook (`sX/`), no la raíz de la distribución.

Este directorio contiene dos entornos complementarios que comparten la red
Docker `hadoop-cluster`. El primero es el camino principal del curso y utiliza
HDFS como almacenamiento:

```text
namenode + tres datanodeX
          │
          ├── HDFS /datalake
          │       ├── raw/tpcds ── Parquet fuente sin catálogo
          │       ├── silver    ── datos validados y enriquecidos
          │       └── gold      ── productos de datos
          └── HDFS /warehouse ── tablas Hive e Iceberg
                    ▲
              Trino ─ Hive Metastore ─ PostgreSQL
```

La sesión 3 añade un Compose independiente en `compose-s3.yml`: RustFS, la
inicialización de un bucket y un contenedor AWS CLI. No contiene Trino ni un
catálogo, porque en esa sesión se estudia primero el almacenamiento de
objetos y los Parquet. El laboratorio posterior definido en `compose-trino.yml`
añade Polaris, Spark, Trino e Iceberg sobre S3. No deben arrancarse dos
laboratorios que publiquen el mismo puerto local `9000` o `8080` a la vez.

Para preparar la infraestructura S3 desde la raíz de la distribución:

```bash
make s3-up
```

Después se ejecuta `s3/s3.ipynb`. El notebook consume las 24 tablas que dejó
S2 y realiza la copia bajo el prefijo `raw/tpcds` mediante
`hdfs dfs -cat` y `boto3.upload_fileobj`, sin pasar los Parquet por el disco
del host. Mantiene un prefijo por tabla, igual que la organización de HDFS.
En un almacenamiento de objetos, `raw` y `tpcds` son componentes de la clave
y no directorios reales.

## Bind mounts y Docker Desktop para macOS

Los ficheros de configuración y los scripts que entran en los contenedores se
montan siempre como directorios existentes del repositorio. Por ejemplo,
`trino-hdfs/etc` se monta en `/etc/trino` —incluyendo su subdirectorio
`etc/catalog`—; los inicializadores se montan desde `init` y el script de
Polaris desde `polaris`.

Esto evita una fuente habitual de errores con Docker Desktop para macOS: si la
ruta de origen de un bind mount de un fichero no existe exactamente, Docker
puede crear un directorio con ese nombre y el proceso termina con un error del
tipo «is a directory». Los montajes de directorios hacen visible de forma
inequívoca el conjunto de recursos y además no dependen de que Compose se
interprete igual desde distintos sistemas operativos. Todos los directorios
montados son de solo lectura; los datos que deben persistir usan volúmenes
nombrados, como `postgresql-metastore-data` y `rustfs-data`.

Hay dos configuraciones de Trino deliberadamente independientes:

| Servicio | Configuración montada | Almacén y catálogo |
| --- | --- | --- |
| `trino-hdfs` | `trino-hdfs/etc` (incluye `etc/catalog`) | HDFS + Hive Metastore por Thrift; catálogos `hive`, `iceberg` y `tpcds` |
| `trino` | `trino/etc` (incluye `etc/catalog`) | RustFS/S3 + Polaris mediante Iceberg REST |

No se debe reutilizar `trino/etc/catalog/iceberg.properties` en el servicio HDFS:
esa configuración apunta a Polaris y a un endpoint S3. Del mismo modo, la
configuración de `trino-hdfs` no debe copiarse al laboratorio S3. Los dos
Compose publican el puerto local `8080`, por lo que se arrancan por separado.

## Warehouse y catálogo sobre HDFS

`compose-warehouse-hdfs.yml` añade tres servicios permanentes sin convertirlos
en nodos de almacenamiento ni de ejecución YARN:

- PostgreSQL persiste exclusivamente la base de datos interna del metastore;
- Hive Metastore expone por Thrift los esquemas, tablas, particiones y
  ubicaciones;
- Trino consulta el metastore, pero lee y escribe directamente los bloques de
  HDFS a través del catálogo `hive` o `iceberg`.

El contenedor `catalog-init` es efímero y se ejecuta al arrancar el compose.
Espera a Trino, crea el esquema compartido `tcdm` bajo
`/warehouse/tcdm.db` —la convención de nombres de Hive— y
comprueba los catálogos. La generación docente de TPC-DS se ejecuta dentro de
`s2/s2.ipynb`: así el uso de la instantánea gzip del INE, el cruce y la
materialización forman parte de la sesión y son exactamente lo que prueba CI.
El notebook conserva como Markdown el código de descarga y normalización para
explicar el proceso, pero no lo ejecuta: la relación puede cambiar y la copia
que recibe el alumnado ya está preparada en `data/ine`.

Desde `26-27/entorno`:

```bash
make warehouse-up
```

El objetivo `make` se ejecuta en el host y delega las operaciones en Docker
Compose. Primero crea la red si no existe, después arranca Hadoop y finalmente
PostgreSQL, el metastore y Trino.

Después se ejecuta `s2/s2.ipynb` completo desde Jupyter. El notebook genera
las 24 tablas de TPC-DS SF1 como Parquet y deja las fuentes preparadas para
S3–S8.

El objetivo siguiente se conserva como herramienta de infraestructura para
pruebas aisladas o recuperación sin Jupyter; no es el recorrido normal del
alumnado:

```bash
make tpcds-init
```

Tanto el notebook como el inicializador auxiliar combinan dos fuentes. Leen las tablas virtuales deterministas de
`tpcds.sf1` y publican en `/datalake/raw/ine/municipios` la instantánea gzip
normalizada de la Relación de municipios y códigos a 1 de enero de 2026 del
INE. Trino detecta la compresión por la extensión, registra temporalmente ese
CSV y lo cruza con las cinco dimensiones
que contienen direcciones: `customer_address`, `store`, `warehouse`,
`call_center` y `web_site`. Los municipios, provincias, códigos provinciales y
el país se sustituyen por valores españoles; las claves y las demás columnas
TPC-DS no cambian.

Después escribe tablas externas temporales y elimina sus metadatos. Los
ficheros de negocio se conservan bajo `/datalake/raw/tpcds/<tabla>`,
acompañados por `_SUCCESS`. Por tanto, al terminar hay datasets Parquet que
todavía no son tablas permanentes del catálogo. Se podrán estudiar
directamente mediante WebHDFS, `fsspec`, PyArrow y Polars, y registrar más
adelante como tablas externas o reescribirlos como tablas Iceberg.

La ruta no contiene `sf1`: el curso mantiene una única escala, indicada por
`TPCDS_SCALE`, y no necesita otro nivel físico para distinguir versiones.
`tpcds` identifica la fuente y cada `<tabla>` es un directorio con uno o más
fragmentos Parquet. Los nombres `raw` y `tpcds` los fija el inicializador; Trino
escribe en la ubicación externa que recibe.

El catálogo virtual de Trino también muestra la tabla técnica
`dbgen_version`. El inicializador la excluye de forma intencionada: no es una
tabla de negocio y su columna `time(3)` no es compatible con el escritor Hive
que materializa estos Parquet. SF1 queda así formado por las 24 tablas de
negocio del benchmark.
Los nombres que genera Trino pueden no terminar en `.parquet`: el formato lo
determinan el contenido y sus metadatos (un fichero Parquet comienza y termina
con la firma `PAR1`), no la extensión.

El inicializador auxiliar puede limitarse a algunas tablas:

```bash
TPCDS_TABLES="date_dim customer item" make tpcds-init
```

La generación es determinista en sus filas para una escala, versión de Trino
y edición versionada del INE dadas. La asignación ordena los 8.132 municipios
por su código y selecciona uno aplicando `crc32` a la pareja ciudad-estado
original de TPC-DS. No usa aleatoriedad y conserva todas las claves. El origen,
checksum y proceso de normalización del Excel están documentados en
`data/ine/README.md`.

La división física en ficheros Parquet puede variar si cambia Trino o el grado
de paralelismo, por lo que la igualdad que se exige al alumnado es lógica, no
una identidad byte a byte de los Parquet.

### Identidades HDFS

No se configura Kerberos, `hadoop.proxyuser` ni `doAs`. Jupyter, Polars y el
driver de Spark se ejecutarán como `luser` dentro de `namenode`. Trino fija
también `HADOOP_USER_NAME=luser`, y el metastore utiliza esa identidad para las
operaciones auxiliares que realiza contra HDFS. `/datalake`, sus capas `raw`,
`silver` y `gold`, y `/warehouse` pertenecen a `luser:hadoop` y tienen permisos
`770`.

WebHDFS devuelve redireccionamientos hacia `datanode1`, `datanode2` o
`datanode3`. Esos nombres funcionan desde Jupyter porque `namenode` está en la
misma red Docker. El puerto `9870` publicado en el host sirve para la interfaz
del NameNode, pero un cliente WebHDFS que siga redireccionamientos debe
ejecutarse normalmente dentro de `hadoop-cluster`.

### Versiones fijadas y compatibilidad

| Componente | Valor por defecto | Criterio |
| --- | --- | --- |
| Trino | `483` | Release reproducible; `TRINO_VERSION` permite ensayar una actualización explícita |
| Hive Metastore | `3.1.3` | Ver justificación abajo |
| PostgreSQL | `17-alpine` | Rama mantenida, sin el cambio de ruta de volumen de PostgreSQL 18 |
| pgJDBC | `42.7.13` | Driver actual fijado por versión y suma SHA-256 durante la construcción |

El Hive Metastore no se usa aquí como motor de consulta: sólo mantiene el
catálogo de bases de datos, tablas, esquemas y particiones que Spark, Trino e
Iceberg consultan por Thrift. La política general del curso es preferir
versiones recientes de cada componente, tanto para evitar la obsolescencia
como para acercarse a lo que puede encontrarse en un proveedor gestionado
(por ejemplo AWS Glue Data Catalog). Esa preferencia cede, sin embargo, en
cuanto una versión más reciente deja de ser compatible con alguna de las
características que la asignatura necesita mostrar: lo que importa no es la
versión exacta del metastore, sino que Spark, Trino e Iceberg funcionen sin
fricción en la mayoría de las operaciones interesantes del curso.

Se probó primero Hive Metastore `4.2.1` (revisión de seguridad de la rama
4.x). Con esa versión, el catálogo Iceberg de Spark (`spark.sql.catalog.*` de
tipo `hive`) no puede acceder por nombre a ninguna tabla Iceberg: falla con
`org.apache.thrift.TApplicationException: Invalid method name: 'get_table'`,
porque `iceberg-spark-runtime` incluye su propio cliente
`hive-metastore-2.3.10.jar`, que sólo sabe invocar el RPC Thrift clásico
`get_table`, retirado en Hive Metastore 4.x en favor de `get_table_req`. Es un
problema conocido y sin resolver en Iceberg (`apache/iceberg#12878`, `#13572`,
`#13628`), y sólo afecta al catálogo Iceberg: el catálogo Hive nativo de Spark
(`enableHiveSupport()`) sí puede compensarlo con un *shim* de compatibilidad
de versión (`spark.sql.hive.metastore.version`/`.jars=maven`), pero
`HiveCatalog` de Iceberg no usa ese mecanismo.

Se cambió entonces a Hive Metastore `3.1.3`, la última versión de la rama 3.x
y una de las dos que Iceberg declara oficialmente soportadas (junto con
`2.3.10`). Verificado en este entorno: el catálogo Iceberg de Spark funciona
por nombre sin ningún workaround (`SELECT`, `MERGE INTO`, `CREATE TABLE`), el
catálogo Hive nativo de Spark deja de necesitar el *shim* de versión, y Trino
no sufre ninguna regresión (creación/lectura de tablas Hive e Iceberg,
`ANALYZE` repetido varias veces seguidas, `EXECUTE optimize`,
`EXECUTE expire_snapshots`). El fallo de repetición de `ANALYZE` documentado
antes para HMS `4.0.x` es específico de esa versión y no aparece en `3.1.3`
(comprobado ejecutando `ANALYZE` tres veces seguidas sobre la misma tabla).

La rama 3.x del proyecto Hive recibe parches de seguridad igual que cualquier
rama mantenida, y `apache/hive:3.1.3` sigue siendo la imagen oficial del
proyecto para esa versión. Su JDK empaquetado es más antiguo que el Java 21
del contenedor oficial de Hive 4.2.x, pero eso no afecta a las imágenes
Hadoop del curso (Java 17): el metastore es un proceso independiente que sólo
se comunica con ellas mediante Thrift y HDFS. Si en el futuro una versión más
reciente de Hive Metastore soluciona la incompatibilidad con el catálogo
Iceberg de Spark, esta decisión debe revisarse; mientras tanto, se documenta
aquí para que no se pierda por qué se descartó la rama 4.x candidata. La
comparación puede repetirse sin editar el compose:

```bash
HIVE_VERSION=4.2.1 docker compose -f compose-warehouse-hdfs.yml up -d --build
```

Los metadatos PostgreSQL permanecen en el volumen
`tcdm-26-27-postgresql-metastore-data`. Los datos de las tablas permanecen en
HDFS y, por tanto, tienen el mismo ciclo de vida que los contenedores Hadoop de
este laboratorio.

## Laboratorio posterior con S3 e Iceberg REST

## Versiones fijadas

Las versiones por defecto están en [.env.example](.env.example):

| Componente | Imagen o versión | Motivo |
| --- | --- | --- |
| Trino | `trinodb/trino:483` | Misma versión fijada que el entorno HDFS |
| Apache Polaris | `apache/polaris:1.7.0` | Catálogo Iceberg REST con guías oficiales para Trino y Spark |
| RustFS | `rustfs/rustfs:1.0.0-beta.12` | Almacén S3-compatible; versión candidata validada por las pruebas del curso |
| Spark | `apache/spark:4.1.3-scala2.13-java21-python3-ubuntu` | Cliente compatible con el runtime Iceberg 4.1/Scala 2.13 |
| Apache Iceberg | `1.11.0` | Runtime publicado para Spark 4.1/Scala 2.13 |
| AWS CLI auxiliar | `amazon/aws-cli:2.36.14` | Sólo crea el bucket local de las sesiones |

Spark 4.2.0 es más reciente, pero Apache Iceberg 1.11.0 publica el runtime
`iceberg-spark-runtime-4.1_2.13`; por eso aquí se prioriza una combinación
compatible y reproducible. Cuando Iceberg publique el runtime para Spark 4.2,
se podrá actualizar `SPARK_BASE_IMAGE` y la dependencia conjuntamente.

## Arranque

Desde la raíz del repositorio:

```bash
cp 26-27/entorno/.env.example 26-27/entorno/.env
docker network inspect hadoop-cluster >/dev/null 2>&1 || \
  docker network create hadoop-cluster

docker compose -f 26-27/entorno/compose-hadoop-cluster.yml up -d
docker compose -f 26-27/entorno/compose-trino.yml up -d --build
```

El segundo comando inicia:

- RustFS y el bucket `tcdm-iceberg`.
- Polaris y el catálogo `quickstart_catalog`, con el namespace `demo`.
- Trino con el catálogo Iceberg REST `iceberg`.
- Un contenedor Spark preparado para Iceberg 1.11.0.

## Recursos del clúster Hadoop

Los límites del clúster Hadoop están fijados en
[`compose-hadoop-cluster.yml`](compose-hadoop-cluster.yml):

| Contenedor | Límite Docker | Recursos YARN anunciados |
| --- | --- | --- |
| `namenode` | 2 vCPU, 4096 MB | NameNode, ResourceManager y Timeline Server; no ejecuta NodeManager |
| Cada `datanodeX` | 2 vCPU, 3072 MB | 2 vcores y 2560 MB para contenedores YARN |

`cpus: 2.0` es un límite de uso del contenedor, no una reserva permanente de
dos núcleos físicos. La configuración de YARN de la imagen anuncia el mismo
número de vcores para que el planificador no crea que el nodo tiene más CPU de
la que Docker permite utilizar.

Los dos vcores por DataNode son intencionados para las pruebas distribuidas de
Spark. Cada executor solicita un vcore y el ApplicationMaster solicita otro;
con tres DataNodes de un solo vcore no cabrían simultáneamente tres executors y
el ApplicationMaster. Con dos vcores, un DataNode puede alojar el
ApplicationMaster y un executor, mientras los otros dos ejecutan los demás
executors. No significa que los ejercicios de las sesiones deban lanzar tareas
con dos cores: los executors de la sesión solicitan un solo core.

La memoria YARN también está fijada en las imágenes: cada DataNode anuncia
2560 MB y el ResourceManager acepta contenedores de hasta 2560 MB. Los 512 MB
restantes del límite Docker quedan fuera del planificador para que puedan
trabajar el DataNode, el NodeManager y los procesos auxiliares. Este presupuesto
permite, por ejemplo, un executor Spark con 2 GiB de heap y su sobrecarga, o
varios contenedores más pequeños. La prueba Spark usa 768 MB por executor
(512 MB de memoria más 256 MB de overhead) y 512 MB para el ApplicationMaster
(256 MB más 256 MB de overhead).

El límite máximo conjunto de los cuatro contenedores Hadoop es de 8 vCPU y
13 GiB de memoria. Docker no suele consumir esos máximos de forma continua,
pero se recomienda asignarle al menos 14 GiB para ejecutar cargas Spark que se
acerquen a los límites. En equipos más ajustados pueden ejecutarse las primeras
sesiones porque el límite no es una reserva, aunque conviene cerrar otros
contenedores. Si se ejecutan simultáneamente Trino, Polaris, RustFS y Spark,
será necesario asignar más memoria a Docker o arrancar sólo los servicios de la
sesión que se esté realizando.

Interfaces locales:

| Servicio | URL |
| --- | --- |
| Trino | <http://localhost:8080> |
| YARN Timeline Server | <http://localhost:8188/applicationhistory/> |
| Polaris REST | <http://localhost:8181> |
| Polaris health/metrics | <http://localhost:8182> |
| RustFS S3 | <http://localhost:9000> |
| RustFS console | <http://localhost:9001> |
| Spark UI, mientras haya una aplicación | <http://localhost:4040> |

Las credenciales incluidas son sólo para el laboratorio local. Cambia el
fichero `.env` si el entorno va a ser accesible desde una red. No se deben usar
estas credenciales en producción.

## Primera prueba con Trino

```bash
docker exec -it tcdm-trino trino
```

En la consola de Trino:

```sql
SHOW CATALOGS;
SHOW SCHEMAS FROM iceberg;
CREATE SCHEMA iceberg.demo;
CREATE TABLE iceberg.demo.events (
    event_id BIGINT,
    event_type VARCHAR,
    created_at TIMESTAMP(6) WITH TIME ZONE
)
WITH (format = 'PARQUET');
INSERT INTO iceberg.demo.events VALUES
    (1, 'page_view', TIMESTAMP '2026-08-21 10:00:00 UTC'),
    (2, 'purchase',  TIMESTAMP '2026-08-21 10:05:00 UTC');
SELECT * FROM iceberg.demo.events ORDER BY event_id;
```

La tabla y sus datos se registran a través de Polaris y se almacenan en
RustFS. El mismo nombre `iceberg.demo.events` debe estar disponible desde
Spark.

## Primera prueba con Spark

El contenedor permanece arrancado para poder abrir una shell Spark cuando se
quiera:

```bash
docker exec -it tcdm-spark-iceberg spark-sql
```

En `spark-sql`:

```sql
SHOW NAMESPACES;
SHOW TABLES IN demo;
SELECT * FROM demo.events ORDER BY event_id;
CREATE TABLE demo.events_from_spark (
    event_id BIGINT,
    source STRING
) USING iceberg;
INSERT INTO demo.events_from_spark VALUES (3, 'spark');
```

La configuración de Spark está en
[`spark/spark-defaults.conf`](spark/spark-defaults.conf) y descarga durante la
construcción los dos artefactos necesarios: el runtime Spark de Iceberg y el
bundle AWS para `S3FileIO`.

## Parada y borrado del laboratorio

```bash
docker compose -f 26-27/entorno/compose-trino.yml down
docker compose -f 26-27/entorno/compose-hadoop-cluster.yml down
```

`down` conserva el volumen de RustFS. Para empezar de cero, eliminando las
tablas y objetos del laboratorio:

```bash
docker compose -f 26-27/entorno/compose-trino.yml down -v
```

## Catálogos HTTP considerados

No hay un catálogo universalmente “más desarrollado” en todos los aspectos;
la elección depende de si se necesitan ramas, gobierno, persistencia o una
instalación mínima.

| Catálogo | Situación para TCDM 26-27 | Decisión |
| --- | --- | --- |
| **Apache Polaris** | Implementación centrada en Iceberg REST, con ejemplos oficiales de Trino y Spark, OAuth2, RBAC y credential vending. | **Elegido** para esta primera versión. |
| **Apache Gravitino** | Plataforma de metadatos más amplia y con servidor Iceberg REST independiente. Añade capacidades, pero también más superficie y configuración. | Alternativa para una fase de gobierno/metadatos federados. |
| **Project Nessie** | Catálogo REST compatible con Iceberg y API propia con semántica Git de ramas y commits. Sigue teniendo releases activas, pero sus ramas no son necesarias para el primer laboratorio. | Mantener como alternativa para enseñar branching/versionado. |
| **Hive Metastore/JDBC** | Opciones muy conocidas y maduras, pero no son un catálogo HTTP REST estándar. | Útiles para comparar con el modelo clásico, no para este camino REST. |
| **Catálogos gestionados** | Unity Catalog, BigLake o servicios equivalentes reducen la operación, pero dejan de ser un entorno local autocontenido. | Considerarlos sólo al estudiar despliegues cloud. |

Polaris usa aquí el metastore en memoria porque permite arrancar con las
imágenes publicadas sin construir una imagen adicional. Es suficiente para la
primera sesión, pero reiniciar el servicio pierde la definición del catálogo
(los objetos de RustFS permanecen). La siguiente evolución debe usar el
backend JDBC de Polaris con PostgreSQL; la propia documentación de Polaris
recomienda PostgreSQL para persistencia y documenta el bootstrap separado del
servidor.

## Fuentes de versiones y compatibilidad

- [Versiones oficiales de Apache Hive](https://hive.apache.org/general/downloads/)
- [Compatibilidad de Spark con Hive Metastore](https://github.com/apache/spark/blob/master/docs/sql-migration-guide.md#compatibility-with-apache-hive)
- [Fallo de `ANALYZE` con Hive Metastore 4.0.x](https://github.com/trinodb/trino/issues/26214)
- [Conector Hive de Trino](https://trino.io/docs/current/connector/hive.html)
- [Acceso de Trino a HDFS](https://trino.io/docs/current/object-storage/file-system-hdfs.html)
- [Versiones de pgJDBC](https://jdbc.postgresql.org/download/)
- [Contenedor oficial de Trino](https://trino.io/docs/current/installation/containers.html)
- [Catálogos REST en Trino 483](https://trino.io/docs/current/object-storage/metastores.html)
- [Versiones de Apache Polaris](https://polaris.apache.org/downloads/)
- [Guía oficial Polaris + Trino](https://polaris.apache.org/guides/trino/)
- [Guía oficial Polaris + Spark](https://polaris.apache.org/guides/spark/)
- [Spark 4.1.3](https://spark.apache.org/docs/4.1.3/)
- [Versiones de Apache Iceberg](https://iceberg.apache.org/releases/)
- [Instalación de RustFS](https://docs.rustfs.com/en/installation)
- [Apache Gravitino Iceberg REST](https://gravitino.apache.org/docs/next/iceberg-rest-service/)
- [Descargas de Project Nessie](https://projectnessie.org/downloads/)
