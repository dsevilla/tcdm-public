# Municipios de España

`municipios-2026.csv.gz` es una copia normalizada, comprimida con gzip y
versionada de la **Relación de municipios y códigos a 1 de enero de 2026** del
Instituto Nacional de Estadística (INE). La fuente publicada es:

<https://www.ine.es/daco/daco42/codmun/26codmun.xlsx>

El Excel descargado para producir esta instantánea tenía SHA-256
`b4bea7c3cc1b295a73f7fa3ca68b2ef25c3a59833bd91ea5315ae25dcc1ca741`.
El CSV conserva los códigos como texto para no perder los ceros iniciales y
añade a cada municipio el nombre de la provincia que figura como cabecera de
su hoja en el libro del INE.

La instantánea ya preparada en este directorio es el único fichero que usa el
entorno y S2. El alumnado no necesita descargar ni regenerar la fuente: el
notebook comprueba y publica directamente este CSV gzip. El proceso de
mantenimiento de una futura edición queda explicado como referencia en S2,
pero no forma parte de la ejecución normal.

El gzip reduce el tamaño de la instantánea distribuida y se conserva también
al publicarla en HDFS como `municipios-2026.csv.gz`. Hadoop y Trino reconocen
la compresión por la extensión; para inspeccionarlo desde la consola se puede
usar `hdfs dfs -text`, y los lectores Python deben abrir el flujo con `gzip`.

El Excel descargado no se versiona. La lista puede cambiar aunque conserve
el mismo año de edición; por eso no se compara automáticamente con una
descarga posterior. Si el INE actualiza la publicación, se deben revisar el
checksum, el número de municipios y los cambios de códigos o denominaciones
antes de sustituir la instantánea usada por el curso.

La procedencia y las condiciones de reutilización deben atribuirse al INE. El
sitio del organismo identifica su contenido con licencia CC BY-SA 4.0:
<https://www.ine.es/aviso_legal>.
