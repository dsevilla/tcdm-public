# Municipios de España

`MUNICIPIOS.csv.gz` es el fichero `MUNICIPIOS.csv` del **Nomenclátor
Geográfico de Municipios y Entidades de Población (NGMEP)**, edición de 2026
(base `202603_NGMEP`), que publica el Instituto Geográfico Nacional (IGN) en el
Centro de Descargas del CNIG, comprimido con GZIP y sin ninguna otra
modificación:

<https://centrodedescargas.cnig.es/CentroDescargas/nomenclator-geografico-municipios-entidades-poblacion>

## Cómo se obtiene

La página ofrece la descarga como un fichero ZIP, `BD_Municipios-Entidades.zip`
(unos 9,6 MB), después de elegir la licencia de uso. El ZIP contiene cinco
tablas en CSV (`PROVINCIAS`, `MUNICIPIOS`, `ENTIDADES`, `EATIMS` y
`COMJURIDIC`), la misma base en formato Access (`202603_NGMEP.mdb`) y la
memoria `Memoria_NGMEP_2026.pdf`, que describe cada columna. El curso sólo usa
`MUNICIPIOS.csv`, y es el que se guarda aquí:

```bash
unzip BD_Municipios-Entidades.zip MUNICIPIOS.csv
gzip -n -9 MUNICIPIOS.csv        # deja MUNICIPIOS.csv.gz
```

Huellas SHA-256:

| Fichero | SHA-256 |
| --- | --- |
| `MUNICIPIOS.csv` (dentro del ZIP) | `00784dfae9d601fd1d3cf2ac7e00e497e755922b260a103b6f01705041bb65a5` |
| `MUNICIPIOS.csv.gz` | `bcb50ab3dd0ebe22a9d8821fc49abf8b69c97e6c986d3bb3b5bb8cb8a467a9ea` |

## Contenido

Una fila por municipio: 8.132, los mismos que la Relación de municipios del
INE a 1 de enero de 2026. Es un CSV con separador `;`, codificado en
ISO-8859-1, con coma decimal y finales de línea CRLF, y con estas columnas:

| Columna | Contenido |
| --- | --- |
| `COD_INE` | Código INE, de 11 dígitos; en esta tabla los cinco primeros identifican el municipio (provincia y municipio) y los seis últimos son siempre `000000`. |
| `ID_REL`, `COD_GEO` | Identificadores del Registro de Entidades Locales y del IGN. |
| `COD_PROV`, `PROVINCIA` | Código y nombre de la provincia. |
| `NOMBRE_ACTUAL` | Denominación del municipio en el Registro de Entidades Locales. |
| `POBLACION_MUNI` | Población total, publicada por el INE. Cambia cada año con el padrón. |
| `SUPERFICIE` | Superficie del término municipal, **en hectáreas**. |
| `PERIMETRO` | Perímetro del término municipal, en metros. |
| `COD_INE_CAPITAL`, `CAPITAL`, `POBLACION_CAPITAL` | La capital del municipio y su población. |
| `HOJA_MTN25` | Hoja del Mapa Topográfico Nacional 1:25.000. |
| `LONGITUD_ETRS89_REGCAN95`, `LATITUD_ETRS89_REGCAN95` | Coordenadas en grados: ETRS89 en la península, Baleares, Ceuta y Melilla, y REGCAN95 en Canarias; compatibles con WGS84. |
| `ORIGENCOOR` | Fuente de las coordenadas: 7.184 son de «detección automática» (centroides), y el resto, de GPS, mapas o investigación. |
| `ALTITUD`, `ORIGENALTITUD` | Altitud en metros y su fuente. |

S2 lo lee con `read_csv` de DuckDB (`delim = ';'`, `encoding = 'latin-1'`,
`decimal_separator = ','`, y `COD_INE` y `COD_PROV` como texto), lo normaliza en
una tabla de 8.132 municipios, la valida y publica el fichero sin cambios en
HDFS, en `/datalake/raw/ign/municipios/MUNICIPIOS.csv.gz`. De la población y
la superficie salen los cálculos de densidad. La normalización se hace en las
celdas del notebook; no hay una versión preparada aparte.

## Actualización

El curso conserva la copia porque el IGN sustituye el fichero cuando publica
una edición nueva, y así todo el alumnado trabaja sobre la misma. Si se
adopta una edición posterior, se revisan el número de municipios y los cambios
de códigos o denominaciones, se sustituye aquí el fichero y se actualizan su
huella, la edición citada y el recuento que comprueba S2.

## Licencia y reconocimiento

El uso de los productos del CNIG se rige por la licencia que figura en su
página de descarga, compatible con **CC BY 4.0**, que obliga a reconocer y
mencionar el origen. Para un producto sin modificar, la fórmula que indica el
CNIG es:

> NGMEP CC-BY 4.0 ign.es

y, cuando se genera un producto nuevo a partir de él:

> Obra derivada de NGMEP CC-BY 4.0 ign.es

La población procede del INE (<https://www.ine.es/aviso_legal>).
