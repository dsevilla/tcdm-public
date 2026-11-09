# Entorno 26-27: Hadoop, data lake y warehouse

En la distribución para el alumnado, este directorio (`entorno/`) es hermano
de `s1/`, `s2/`, ..., `s8/`. Los notebooks lo referencian con `../entorno/...`
porque el directorio de trabajo del kernel de Jupyter es el propio directorio
del notebook (`sX/`), no la raíz de la distribución.

La distribución publicada incluye sólo las partes de este directorio que
necesitan las sesiones ya publicadas; la correspondencia está en
`SESIONES.txt`, que no se publica. Las órdenes de este documento se escriben
desde la raíz de la distribución con `make -C entorno ...`.

## Actualizar el material

Cada sesión nueva, y cada corrección de una ya publicada, llega con una
actualización del repositorio. Se trae con:

```bash
make -C entorno actualizar
```

Sustituye a `git pull`, que se niega a actualizar cuando se ha publicado una
corrección de un fichero que ya se había modificado en local, cosa habitual
porque ejecutar un notebook lo modifica (guarda sus salidas). `actualizar`
no fusiona nada, así que nunca deja conflictos que resolver:

- un fichero modificado en local que también cambia en la versión nueva se
  aparta como copia junto al original (`s2/s2.ipynb` pasa a
  `s2/s2.mio-<fecha>-<hora>.ipynb`) y el original se sustituye por el
  publicado;
- lo mismo ocurre con un fichero propio cuyo nombre coincida con uno que la
  versión nueva añade;
- los cambios locales en ficheros que la versión nueva no toca se quedan
  como están.

La orden lista los ficheros que aparta. El notebook publicado llega sin
salidas: las de la ejecución anterior están en la copia. No actúa sobre una
copia con commits propios: en ese caso lo indica y no cambia nada.

### Comprobar que la copia y el equipo están al día

`comprobar-entorno.sh` indica si una sesión tiene todo lo necesario. Se
teclea en una terminal del equipo, desde la raíz de la distribución, con la
sesión que se va a empezar:

```bash
bash entorno/comprobar-entorno.sh s3
```

Comprueba, por este orden:

- las herramientas del curso: `git`, `curl`, `make`, Python 3 con `venv`,
  Docker en marcha y Docker Compose v2, con la orden concreta para instalar
  lo que falte;
- cada fichero de `s1/` hasta la sesión indicada y de `entorno/`, comparado con
  la última versión publicada en `tcdm-public`. Los notebooks se comparan por
  el texto de sus celdas, así que guardar las salidas al ejecutarlos no los
  hace parecer desactualizados;
- si la copia es un clon de git: la rama (`26-27`) y el commit en que está,
  frente al último publicado.

Si algo está desactualizado o falta, lo dice fichero a fichero y propone
`make -C entorno actualizar`. Una copia que aún no tiene el comprobador, o la
que se quiere comprobar antes de actualizar, lo ejecuta directamente desde la
publicación, sin descargarlo antes:

```bash
curl -fsSL https://raw.githubusercontent.com/dsevilla/tcdm-public/26-27/entorno/comprobar-entorno.sh | bash -s s3
```

El comprobador lee `entorno/MANIFIESTO.txt` de la rama publicada. Ese
fichero lo genera la publicación del material, con la huella de cada fichero
de las sesiones publicadas y de `entorno/`; no se edita a mano.

## Jupyter en `namenode`

Desde S2 el kernel de Jupyter se ejecuta dentro de `namenode`. La imagen
incluye el entorno Python del curso en `/opt/tcdm/venv` (Jupyter Lab,
PySpark, PyArrow, Polars, DuckDB, `fsspec`, `hdfs-native`, `s3fs`, boto3 y el
cliente de Trino), pero Jupyter Lab no arranca solo. El alumnado entra en el
contenedor y lo lanza como `luser`:

```bash
docker exec -it namenode bash        # en el equipo
su - luser                           # dentro de namenode
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --IdentityProvider.token=tcdm
```

Jupyter queda en primer plano. El token es siempre `tcdm` (el puerto 8888 sólo
se publica en `127.0.0.1`), por lo que la dirección que se pega en Visual
Studio Code es `http://127.0.0.1:8888/lab?token=tcdm`.
`make -C entorno jupyter` es un atajo que hace lo mismo en una orden. La lista
común `entorno/requirements.txt` reúne las dependencias usadas en S2-S8 y se
publica en este directorio desde S2. La celda `%pip` de cada notebook la
descarga desde la misma URL HTTPS de `tcdm-public`. Con la imagen al día, `%pip`
sólo confirma lo que ya está instalado. Los DataNodes no necesitan este
entorno: los ejecutores de Spark reciben por YARN el código de PySpark y los
`.jar`, y usan el `python3` de la imagen base.

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
          └── HDFS /warehouse ── tablas Hive e Iceberg (desde S6)
                    ▲
              Trino ─ Hive Metastore ─ PostgreSQL
```

La sesión 3 añade un Compose independiente en `compose-s3.yml`: sólo RustFS.
El bucket `tcdm-datalake` no lo crea el Compose, sino el
propio notebook con boto3. No contiene Trino ni un
catálogo, porque en esa sesión se estudia primero el almacenamiento de
objetos y los Parquet. Las tablas Iceberg de S7 y S8 viven en HDFS, con el
catálogo del warehouse de S6; S8 explica cómo cambiaría la configuración de
Spark si el almacenamiento fuera S3, GCS o Azure.

Para preparar la infraestructura S3 desde la raíz de la distribución:

```bash
make s3-up
```

Después se ejecuta `s3/s3.ipynb`. El notebook consume las 18 tablas que dejó
S2 y realiza la copia bajo el prefijo `raw/tpcds` mediante
`fsspec` (`hdfs-native` para leer de HDFS y `s3fs` para escribir en el bucket), sin
pasar los Parquet por el disco del host. Mantiene un prefijo por tabla, igual que la organización de HDFS.
En un almacenamiento de objetos, `raw` y `tpcds` son componentes de la clave
y no directorios reales.

## Parar, eliminar y borrar

El `Makefile` ofrece cuatro órdenes, de menos a más destructiva. Se aplican
a todos los Compose presentes en la distribución (Hadoop, warehouse y S3):

| Orden | Qué hace | Qué se conserva |
| --- | --- | --- |
| `make -C entorno stop` | Para los contenedores sin eliminarlos | Todo, incluido el interior de cada contenedor |
| `make -C entorno down` | Elimina los contenedores | Los volúmenes: HDFS, metadatos del Hive Metastore y objetos de S3 |
| `make -C entorno clean` | `down` y borra los volúmenes del Hive Metastore y de S3 | Sólo HDFS |
| `make -C entorno clean-hdfs` | `clean` y borra los volúmenes HDFS | Ningún dato |

Después de cualquiera de ellas se arranca de nuevo con `hadoop-up` o `s3-up`. Jupyter no vuelve solo: hay que lanzarlo otra vez
dentro de `namenode`. `make -C entorno status` lista los contenedores en
marcha y los parados.

## Solución de problemas

Los fallos más habituales al seguir las sesiones. Las órdenes `make` y
`docker` se teclean en una terminal del equipo, desde la raíz de la
distribución.

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| Una celda `!hdfs ...` responde `hdfs: command not found`, o falla un `import` de una biblioteca del curso, aunque el clúster está en marcha | El notebook está usando un kernel de tu equipo, no el de `namenode` | En Visual Studio Code: **Select Kernel → Select Another Kernel → Existing Jupyter Server**, con `http://127.0.0.1:8888/lab?token=tcdm`. Para comprobarlo, `import socket; socket.gethostname()` debe devolver `namenode` |
| Visual Studio Code no consigue conectar con `http://127.0.0.1:8888` | Jupyter no está arrancado: se cerró su terminal, se pulsó `Ctrl+C` o se pararon los contenedores | Volver a lanzarlo con `make -C entorno jupyter` (o `docker exec -it namenode bash`, `su - luser` y `jupyter lab ...`) y reconectar el kernel |
| `NameError` al usar una variable definida más arriba | El kernel se ha reiniciado y ha perdido su estado | Ejecutar de nuevo, en orden, las celdas anteriores de las que depende la sección |
| `make -C entorno status` no muestra en marcha `namenode` y los tres `datanodeN`, o `hdfs dfsadmin -report` lista menos de tres DataNodes | El clúster está parado o todavía arrancando | `make -C entorno hadoop-up`, esperar medio minuto y repetir la comprobación. Si sigue igual, `docker logs namenode --tail=120` |
| No sé si mi copia o mi equipo están listos para una sesión | Material sin actualizar, herramienta sin instalar o Docker parado | `bash entorno/comprobar-entorno.sh s3` (cambia `s3` por la sesión) |
| Errores de conexión con `rustfs:9000` (sesión 3) | RustFS no está arrancado | `make -C entorno s3-up` |
| Falla una descarga: `%pip install`, un fichero de `raw.githubusercontent.com` o el conector de Iceberg al crear la `SparkSession` de las sesiones 7 y 8 | El contenedor `namenode` no tiene salida a Internet | Comprobarlo con `docker exec namenode curl -sI https://github.com` y revisar la red, la VPN o el proxy de Docker |
| Un contenedor aparece como `Exited (137)`, o el kernel muere durante un cálculo | Docker se ha quedado sin memoria | Asignar más memoria a Docker (ver «Arrancar el clúster › Antes de empezar» en la sesión 1), parar los servicios que la sesión no use y cerrar otros notebooks que tengan una `SparkSession` abierta |
| Al arrancar, Docker responde `port is already allocated` | Otro contenedor o programa usa ya ese puerto (8888, 9000, 8080…) | Localizarlo con `docker ps` y pararlo. No deben estar arrancados a la vez dos laboratorios que publiquen el mismo puerto |
| Una sesión no encuentra rutas o tablas que debía dejar otra anterior | Esa sesión anterior no se completó, o se borraron sus datos con `clean` o `clean-hdfs` | Volver a ejecutar el notebook de la sesión anterior que indica el mensaje |

Para saber en qué estado está el laboratorio antes de buscar más:
`make -C entorno status`.

## Bind mounts y Docker Desktop para macOS

Los ficheros de configuración y los scripts que entran en los contenedores se
montan siempre como directorios existentes del repositorio. Por ejemplo,
`trino-hdfs/etc` se monta en `/etc/trino` —incluyendo su subdirectorio
`etc/catalog`—, la configuración del metastore desde `hive-metastore/conf`
y el inicializador de catálogos desde `init`.

Esto evita una fuente habitual de errores con Docker Desktop para macOS: si la
ruta de origen de un bind mount de un fichero no existe exactamente, Docker
puede crear un directorio con ese nombre y el proceso termina con un error del
tipo «is a directory». Los montajes de directorios hacen visible de forma
inequívoca el conjunto de recursos y además no dependen de que Compose se
interprete igual desde distintos sistemas operativos. Todos los directorios
montados son de solo lectura; los datos que deben persistir usan volúmenes
nombrados, como `postgresql-metastore-data` y `rustfs-data`.

La configuración de Trino (`trino-hdfs/etc/catalog`) declara dos catálogos
sobre el mismo Hive Metastore: `hive`, por Thrift, y `iceberg`, por Iceberg
REST.

## Warehouse y catálogo sobre HDFS

`compose-warehouse-hdfs.yml` añade tres servicios permanentes sin convertirlos
en nodos de almacenamiento ni de ejecución YARN:

- PostgreSQL persiste exclusivamente la base de datos interna del metastore;
- Hive Metastore expone los esquemas, tablas, particiones y ubicaciones por
  dos puertos: Thrift (`9083`), para el conector `hive` de Trino y el soporte
  Hive de Spark, e Iceberg REST (`9001`, ruta `/iceberg`), para las tablas
  Iceberg de Trino y Spark;
- Trino consulta el metastore, pero lee y escribe directamente los bloques de
  HDFS a través del catálogo `hive` o `iceberg`.

El contenedor `catalog-init` es efímero y se ejecuta al arrancar el compose.
Espera a Trino, crea el esquema compartido `tcdm` bajo
`/warehouse/tcdm.db` —la convención de nombres de Hive— y
comprueba los catálogos. La sesión 6 es la primera que lo usa.

## Generación de TPC-DS en S2

S2 no necesita más servicios que el clúster de S1. El notebook genera las 18
tablas de TPC-DS SF3 que usa el curso con DuckDB, dentro de su propio kernel
en `namenode`, y las escribe como Parquet en HDFS con el cliente `hdfs-native`. Es la única
forma de obtenerlas: ningún objetivo de `make` ni servicio de Compose genera
datos.

DuckDB genera TPC-DS con `dsdgen`, de su extensión `tpcds`, en una base
temporal en el disco de `namenode` (`/tmp/tpcds/tpcds-sf3.duckdb`), con
`memory_limit` fijado a 1 GB porque `namenode` comparte su memoria con el
NameNode, el ResourceManager y Jupyter. La base se borra al terminar.

El notebook combina dos fuentes. Lee con `read_csv` de DuckDB el fichero de
municipios del Nomenclátor Geográfico del IGN, edición de 2026
(`data/ign/MUNICIPIOS.csv.gz`), con los códigos y la población del INE, la
superficie y las coordenadas, lo normaliza en una tabla de 8.132 municipios, la
valida, calcula la densidad de población y publica el CSV sin cambios en
`/datalake/raw/ign/municipios`. Después la cruza con las cuatro dimensiones que contienen direcciones:
`customer_address`, `store`, `warehouse` y `web_site`. Los municipios,
provincias, códigos provinciales y el país se sustituyen por valores
españoles; las claves de esas dimensiones y sus demás columnas no cambian.

También corrige la vigencia de las versiones. Cuatro dimensiones (`item`,
`store`, `web_page` y `web_site`) guardan varias versiones de
cada objeto con sus fechas `rec_start_date` y `rec_end_date`, y el generador
no enlaza siempre cada hecho con la versión vigente en su fecha: adelanta
esas fechas un número distinto de días en cada dimensión y, en algunos
hechos, no elige la versión por fecha. Una tabla temporal,
`vigencia_versiones`, deshace el adelanto y rellena las fechas de inicio
vacías de `item`; con ella se corrigen las fechas de las cuatro dimensiones
y se reasignan a la versión vigente `ss_store_sk`, `sr_store_sk`
y `wr_web_page_sk`.

Por último, guarda las fechas en las propias tablas. TPC-DS las representa
con claves hacia dos dimensiones, `date_dim` y `time_dim`, que el curso no
materializa: una clave de fecha sola pasa a ser una columna `date` con el
mismo nombre sin `_sk` (`ws_ship_date`, `inv_date`), y una clave de fecha
con su clave de hora se funden en una columna `timestamp`
(`ws_sold_timestamp`, `ss_sold_timestamp`, `sr_returned_timestamp`,
`wr_returned_timestamp`). Si falta la fecha queda `NULL`; si sólo falta la
hora, la marca de tiempo queda a medianoche. Diez tablas tienen claves de
este tipo.

Cada tabla se escribe con un `COPY ... TO ... (FORMAT PARQUET, COMPRESSION
ZSTD)` en un único fichero, `/datalake/raw/tpcds/<tabla>/<tabla>.parquet`,
con grupos de 122.880 filas (`ROW_GROUP_SIZE`, el valor por defecto de
DuckDB, escrito en el `COPY`), para que los hechos grandes tengan más grupos
que DataNodes y Spark pueda repartirlos entre los ejecutores. Los hechos se
escriben ordenados por fecha y, dentro de cada día, por ticket o pedido; las
dimensiones, por su clave. El marcador `_SUCCESS` de cada tabla guarda las
correcciones que lleva (`INE-2026`, `SCD2` y `FECHAS`, unidas con `+` cuando
son varias, o vacío), y una tabla cuyo marcador no coincide se vuelve a
generar. Al terminar hay datasets Parquet que todavía no son tablas de
ningún catálogo: se estudian directamente mediante `hdfs-native`,
`fsspec`, PyArrow, Polars y DuckDB, y se registran más adelante como tablas externas o
se reescriben como tablas Iceberg.

La ruta no contiene `sf3`: el curso mantiene una única escala y no necesita
otro nivel físico para distinguir versiones. `tpcds` identifica la fuente y
cada `<tabla>` es un directorio. De las 24 tablas que genera `dsdgen` se
excluyen las cuatro del canal de catálogo (`catalog_sales`,
`catalog_returns`, `catalog_page` y `call_center`), que el curso no usa, y
`date_dim` y `time_dim`, cuyas claves se guardan ya como fechas: se
materializan 18.

La generación es determinista en sus filas para una escala, versión de DuckDB
y edición versionada del Nomenclátor dadas. La asignación ordena los 8.132 municipios
por su código y selecciona uno con la huella `md5_number` de la pareja
ciudad-estado original de TPC-DS. No usa aleatoriedad y conserva todas las
claves. El origen, la huella y la licencia del CSV están documentados en
`data/ign/README.md`. El tamaño exacto de los ficheros puede variar si cambia
DuckDB, por lo que la igualdad que se exige al alumnado es lógica, no una
identidad byte a byte de los Parquet.

### Identidades HDFS

No se configura Kerberos, `hadoop.proxyuser` ni `doAs`. Jupyter, Polars y el
driver de Spark se ejecutarán como `luser` dentro de `namenode`. Trino fija
también `HADOOP_USER_NAME=luser`, y el metastore utiliza esa identidad para las
operaciones auxiliares que realiza contra HDFS. `/datalake`, sus capas `raw`,
`silver` y `gold`, y `/warehouse` pertenecen a `luser:hadoop` y tienen permisos
`775`: «otros» necesita `r-x` para que la interfaz web del NameNode, que entra
como usuario anónimo (`dr.who`), pueda listarlos. Un entorno creado con una
imagen anterior (permisos `770`) se corrige con la orden de `hdadmin` de S2 y S3.

Los notebooks acceden a HDFS desde Python con `hdfs-native`, un cliente
nativo escrito en Rust que no necesita Java: habla con el NameNode por RPC en
`namenode:9000` y lee y escribe los bloques directamente en `datanode1`,
`datanode2` o `datanode3` (puerto `9866`). Esas direcciones sólo se alcanzan
dentro de la red `hadoop-cluster`, así que el cliente debe ejecutarse ahí, como
el Jupyter de `namenode`. Toma la identidad de `HADOOP_USER_NAME` o, si no
está definida, la del usuario del proceso (`luser`). El puerto `9870`
publicado en el host sirve para la interfaz web del NameNode.

### Versiones fijadas y compatibilidad

| Componente | Valor por defecto | Criterio |
| --- | --- | --- |
| Trino | `483` | Release reproducible; `TRINO_VERSION` permite ensayar una actualización explícita |
| Hive Metastore | `4.2.1` | Imagen oficial `apache/hive:standalone-metastore-4.2.1` (amd64 y arm64); ver justificación abajo |
| PostgreSQL | `17-alpine` | Rama mantenida, sin el cambio de ruta de volumen de PostgreSQL 18 |
| pgJDBC | `42.7.13` | Driver actual fijado por versión y suma SHA-256 durante la construcción |
| Apache Iceberg | `1.11.0` | `iceberg-spark-runtime-4.1_2.13`, compatible con el PySpark `4.1.x` de la imagen. La imagen de `namenode` lo trae en `/opt/tcdm/jars` (descargado de Maven Central y comprobado con su SHA-256 en `make-images/install-python-environment.sh`), y S7 y S8 lo pasan con `spark.jars`; con una imagen anterior, usan `spark.jars.packages` y Spark lo descarga en la primera sesión |

Spark 4.2 es más reciente, pero Iceberg 1.11.0 sólo publica el runtime para
Spark 4.1 (`iceberg-spark-runtime-4.1_2.13`); por eso se prioriza una
combinación compatible y reproducible. Cuando Iceberg publique el runtime para
Spark 4.2, podrán actualizarse juntos PySpark (`requirements.txt` y la imagen)
y la coordenada de los notebooks.

El Hive Metastore no se usa aquí como motor de consulta: sólo mantiene el
catálogo de bases de datos, tablas, esquemas y particiones que consultan
Spark y Trino. La política general del curso es preferir versiones recientes
de cada componente, tanto para evitar la obsolescencia como para acercarse a
lo que puede encontrarse en un proveedor gestionado (por ejemplo AWS Glue
Data Catalog), siempre que Spark, Trino e Iceberg sigan funcionando sin
fricción en las operaciones interesantes del curso.

**Dos protocolos, un catálogo.** Desde Hive 4.1, el metastore publica,
además del Thrift clásico, la API Iceberg REST (`metastore.catalog.servlet.port`,
aquí `http://hive-metastore:9001/iceberg`). El curso la usa para todas las
tablas Iceberg, desde Trino (`iceberg.catalog.type=rest`) y desde Spark
(`spark.sql.catalog.iceberg.type=rest`). Thrift queda para las tablas Hive de
la sesión 6: el conector `hive` de Trino y el soporte Hive de Spark
(`enableHiveSupport()`). Las dos vías escriben en la misma base de datos del
metastore, así que una tabla Iceberg creada por REST aparece también en
`TBLS` con `table_type=ICEBERG`.

**Por qué no el catálogo Iceberg de tipo `hive`.** El catálogo Iceberg de
Spark de tipo `hive` habla Thrift directamente y no funciona contra Hive
Metastore 4.x: falla con `org.apache.thrift.TApplicationException: Invalid
method name: 'get_table'`, porque `iceberg-spark-runtime` incluye su propio
cliente `hive-metastore-2.3.10.jar`, que sólo sabe invocar el RPC clásico
`get_table`, retirado en Hive 4 en favor de `get_table_req`. Es un problema
conocido y abierto en Iceberg Java (`apache/iceberg#12878`, `#13572`,
`#13628`); iceberg-rust ya lo corrigió en su propio cliente. Con REST el
cliente no depende de la versión del servidor: Spark envía peticiones HTTP y
el metastore las resuelve con su propio código Hive. Hasta noviembre de 2026
el curso esquivaba el fallo fijando Hive Metastore `3.1.3`, con una imagen
multiarquitectura propia (`dsevilla/hive:3.1.3`) porque la oficial sólo
existía para amd64; esa imagen ya no se usa.

**Soporte Hive de Spark contra Hive 4.** El catálogo Hive nativo de Spark
(sesiones 6 y 7) también incluye por defecto un cliente 2.3.10 y falla con
el mismo `get_table`. A diferencia del de Iceberg, admite cargar otro
cliente de forma aislada, y así lo hacen los notebooks con
`spark.sql.hive.metastore.version=4.1.0`, la versión más reciente que admite
Spark 4.1. Ese cliente son 279 jars (unos 395 MB). La imagen de `namenode` los
trae en `/opt/tcdm/hive-metastore-client/4.1.0`: los descarga
`make-images/download-hive-metastore-client.py` durante la construcción,
llamando al mismo mecanismo de Spark que `jars=maven`
(`IsolatedClientLoader.forVersion`), para que el conjunto de jars sea el que
espera la versión de PySpark instalada. Los notebooks usan ese directorio con
`spark.sql.hive.metastore.jars=path` si existe y, con una imagen anterior que
no lo tenga, `jars=maven`: Spark descarga el cliente de Maven Central en la
primera sesión y lo guarda en la caché de Ivy de `luser`. La versión del
cliente está en `make-images/install-python-environment.sh` y en
`HIVE_CLIENT_VERSION` de `s6.ipynb` y `s7.ipynb`, y debe coincidir.

**Configuración del metastore** (`hive-metastore/conf/metastore-site.xml`):

- Hive 4 separa la raíz de las tablas administradas
  (`metastore.warehouse.dir`) de la de las externas
  (`metastore.warehouse.external.dir`). Las dos apuntan a
  `hdfs://namenode:9000/warehouse`: todas las tablas creadas sin ubicación
  quedan en `/warehouse/<esquema>.db/<tabla>`, como con Hive 3. El
  `HiveCatalog` de Iceberg que hay detrás del catálogo REST lee la clave
  `hive.metastore.warehouse.external.dir`, que por eso se repite con ese
  nombre.
- `metastore.metadata.transformer.class` en blanco desactiva el
  transformador de metadatos de Hive 4. Ese transformador convierte toda
  tabla administrada que no sea ACID en `EXTERNAL_TABLE` con
  `external.table.purge=true`, y exige que las dos raíces del warehouse sean
  distintas. Sin él, una tabla creada sin `LOCATION` es `MANAGED_TABLE` y
  `DROP TABLE` borra sus datos, mientras que una externa los conserva: la
  distinción que enseña la sesión 6.
- El entrypoint de la imagen enlaza los ficheros de `HIVE_CUSTOM_CONF_DIR`
  sobre `/opt/hive/conf`, de modo que este `metastore-site.xml` sustituye al
  de la imagen y repite lo que hacía falta de él, incluido
  `metastore.task.threads.always` (sin esa propiedad aparece en el log un
  `NoClassDefFoundError` de YARN, sin más efecto).
- El entrypoint ejecuta `schematool -initOrUpgradeSchema`: crea el esquema
  en el primer arranque y no hace nada en los siguientes.

El fallo de repetición de `ANALYZE` de Trino documentado para Hive Metastore
`4.0.x` no aparece con `4.2.1` (comprobado ejecutando `ANALYZE` dos veces
seguidas sobre la misma tabla).

Los metadatos PostgreSQL permanecen en el volumen
`tcdm-26-27-postgresql-metastore-data`. Los datos de las tablas permanecen en
HDFS y, por tanto, tienen el mismo ciclo de vida que los contenedores Hadoop de
este laboratorio.

### Limitaciones a revisar al actualizar versiones

Estas limitaciones de las versiones fijadas (Trino `483`, Iceberg `1.11.0`,
Spark `4.1.x`, Hive Metastore `4.2.1`) condicionan lo que las sesiones 7 y 8
pueden demostrar. Los notebooks las enuncian como un hecho; aquí queda el
detalle para comprobar, cada vez que se actualice una versión, si alguna ha
dejado de aplicarse.

**Z-order (sesión 7).** La sección «Z-order» se presenta sin ejecutar.

- El conector Iceberg de Trino no ofrece Z-order: `ALTER TABLE ... EXECUTE
  optimize` sólo compacta por tamaño de fichero.
- Desde Spark, la llamada

  ```text
  CALL iceberg.system.rewrite_data_files(
      table => 'tcdm.web_sales_lab_sorted',
      strategy => 'sort',
      sort_order => 'zorder(ws_item_sk, ws_net_paid)',
      options => map('rewrite-all', 'true')
  )
  ```

  falla con `IllegalArgumentException: Cannot use column ws_net_paid of type
  DecimalType(7,2) in ZOrdering, the type is unsupported`: Z-order no admite
  columnas `DECIMAL`.
- Con dos columnas `BIGINT` (`zorder(ws_item_sk, ws_order_number)`) sobre la
  misma tabla, creada por Trino con `sorted_by = ARRAY['ws_item_sk']`, falla
  con `IllegalArgumentException: Cannot use output sort order id 0 because
  the table does not contain a sort order with that id`. Coincide con
  incompatibilidades ya comunicadas entre `rewrite_data_files` y el *sort
  order* declarado de una tabla
  ([apache/iceberg#10346](https://github.com/apache/iceberg/issues/10346)).
  No se ha probado sobre una tabla de laboratorio sin `sorted_by`.

Cuando una versión lo resuelva, la sección debe pasar a ser una demostración
ejecutada y medida (inventario de ficheros y plan antes y después), y las
preguntas y evidencias de la sesión que la mencionan deben actualizarse.

***Copy-on-write* desde Trino (sesión 8).** El conector Iceberg de Trino
sólo implementa *merge-on-read* para `UPDATE`, `DELETE` y `MERGE`, y rechaza
las propiedades de modo de escritura: declarar `write.merge.mode` en
`extra_properties` da `TrinoUserError: Illegal keys in extra_properties:
[write.merge.mode]`
([trinodb/trino#17272](https://github.com/trinodb/trino/issues/17272)). Por
eso las tablas de laboratorio `web_sales_lab_cow` y `web_sales_lab_mor` se
crean y se modifican con Spark. Si Trino llega a admitir *copy-on-write*, la
comparación puede hacerse también desde Trino.

**Catálogo Iceberg de tipo `hive` (sesiones 7 y 8).** El catálogo Iceberg
de Spark por Thrift no funciona con Hive Metastore 4.x (ver arriba), y por eso
los notebooks usan el catálogo REST. Si `HiveCatalog` de Iceberg pasa a usar
`get_table_req`, ambos caminos serían posibles, pero REST sigue siendo el
preferido por interoperabilidad.

**`expire_snapshots` en Spark local.** Con Spark `4.1.3` e Iceberg `1.11.0`,
`CALL iceberg.system.expire_snapshots(...)` se queda bloqueado
indefinidamente si la sesión usa `master("local[*]")`, con cualquier tipo de
catálogo (también `hadoop`): el job de *broadcast* queda esperando sin tareas
en ejecución. En YARN, que es lo que usan los notebooks, termina en segundos.
Si alguna vez se prueba un notebook en modo local, conviene tenerlo en
cuenta.

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
contenedores. Si se ejecutan a la vez el warehouse (PostgreSQL, Hive
Metastore y Trino) y RustFS, puede hacer falta asignar más memoria a Docker o
arrancar sólo los servicios de la sesión que se esté realizando.

Interfaces locales:

| Servicio | URL |
| --- | --- |
| Trino | <http://localhost:8080> |
| YARN Timeline Server | <http://localhost:8188/applicationhistory/> |
| Spark UI, mientras haya una aplicación | <http://localhost:4040> |

Las credenciales incluidas son sólo para el laboratorio local. Cambia el
fichero `.env` si el entorno va a ser accesible desde una red. No se deben usar
estas credenciales en producción.

## Catálogos HTTP considerados

No hay un catálogo universalmente “más desarrollado” en todos los aspectos;
la elección depende de si se necesitan ramas, gobierno, persistencia o una
instalación mínima.

| Catálogo | Situación para TCDM 26-27 | Decisión |
| --- | --- | --- |
| **Apache Polaris** | Implementación centrada en Iceberg REST, con ejemplos oficiales de Trino y Spark, OAuth2, RBAC y credential vending. No admite HDFS como almacenamiento. | Referencia para almacenamiento de objetos (S3, GCS, Azure); S8 muestra cómo se configuraría Spark. |
| **Apache Gravitino** | Plataforma de metadatos más amplia y con servidor Iceberg REST independiente. Añade capacidades, pero también más superficie y configuración. | Alternativa para una fase de gobierno/metadatos federados. |
| **Project Nessie** | Catálogo REST compatible con Iceberg y API propia con semántica Git de ramas y commits. Sigue teniendo releases activas, pero sus ramas no son necesarias para el primer laboratorio. | Mantener como alternativa para enseñar branching/versionado. |
| **Hive Metastore** | Desde Hive 4.1 publica también la API Iceberg REST sobre el mismo metastore que usan las tablas Hive. | **Elegido** para el camino principal sobre HDFS (sesiones 6-8): un único catálogo con Thrift para Hive y REST para Iceberg. |
| **JDBC** | Catálogo Iceberg sobre una base de datos relacional; maduro, pero no es un catálogo HTTP REST. | Útil para comparar, no para el camino REST. |
| **Catálogos gestionados** | Unity Catalog, BigLake o servicios equivalentes reducen la operación, pero dejan de ser un entorno local autocontenido. | Considerarlos sólo al estudiar despliegues cloud. |

## Fuentes de versiones y compatibilidad

- [Versiones oficiales de Apache Hive](https://hive.apache.org/general/downloads/)
- [API Iceberg REST de Hive Metastore](https://hive.apache.org/docs/latest/admin/iceberg-rest-catalog/)
- [Fallo `get_table` de Iceberg con Hive Metastore 4](https://github.com/apache/iceberg/issues/12878)
- [Compatibilidad de Spark con Hive Metastore](https://github.com/apache/spark/blob/master/docs/sql-migration-guide.md#compatibility-with-apache-hive)
- [Fallo de `ANALYZE` con Hive Metastore 4.0.x](https://github.com/trinodb/trino/issues/26214)
- [Conector Hive de Trino](https://trino.io/docs/current/connector/hive.html)
- [Acceso de Trino a HDFS](https://trino.io/docs/current/object-storage/file-system-hdfs.html)
- [Versiones de pgJDBC](https://jdbc.postgresql.org/download/)
- [Contenedor oficial de Trino](https://trino.io/docs/current/installation/containers.html)
- [Catálogos REST en Trino 483](https://trino.io/docs/current/object-storage/metastores.html)
- [Guía oficial Polaris + Spark](https://polaris.apache.org/guides/spark/)
- [Spark 4.1.3](https://spark.apache.org/docs/4.1.3/)
- [Versiones de Apache Iceberg](https://iceberg.apache.org/releases/)
- [Instalación de RustFS](https://docs.rustfs.com/en/installation)
- [Apache Gravitino Iceberg REST](https://gravitino.apache.org/docs/next/iceberg-rest-service/)
- [Descargas de Project Nessie](https://projectnessie.org/downloads/)
