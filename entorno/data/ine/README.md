# Municipios de España

`26codmun.xlsx` es una copia versionada de la **Relación de municipios y
códigos a 1 de enero de 2026** del Instituto Nacional de Estadística (INE),
tal como la publica el organismo:

<https://www.ine.es/daco/daco42/codmun/26codmun.xlsx>

Su SHA-256 es
`b4bea7c3cc1b295a73f7fa3ca68b2ef25c3a59833bd91ea5315ae25dcc1ca741`.

El libro tiene una hoja por provincia, llamada con su código (`01` a `52`).
En cada hoja, la fila 1 es el título del libro, la celda `A2` el nombre de la
provincia, la fila 3 la cabecera (`CPRO`, `CMUN`, `DC`, `NOMBRE`) y los
municipios empiezan en la fila 4.

S2 descarga este fichero, lo lee con la extensión `excel` de DuckDB, reúne
las 52 hojas en una tabla de 8.132 municipios, la valida y publica el libro
sin cambios en HDFS, en `/datalake/raw/ine/municipios/26codmun.xlsx`. La
normalización se hace en las celdas del notebook; no hay una versión
preparada aparte.

El curso conserva la copia porque el INE sustituye el fichero cuando publica
una edición nueva, y así todo el alumnado trabaja sobre la misma. Si se
adopta una edición posterior, se revisan el número de municipios y los
cambios de códigos o denominaciones, se sustituye aquí el fichero y se
actualizan su nombre, su huella y el recuento que comprueba S2.

La procedencia y las condiciones de reutilización deben atribuirse al INE. El
sitio del organismo identifica su contenido con licencia CC BY-SA 4.0:
<https://www.ine.es/aviso_legal>.
