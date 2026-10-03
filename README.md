# tcdm-public

Sitio público para la asignatura Tecnología de Computación de datos Masivos (TCDM) del máster de big data de la UMU, curso 26-27.

## Por dónde empezar

Las sesiones se pueden leer en la web sin instalar nada:
<https://dsevilla.github.io/tcdm-public/>. Conviene leer allí la sesión 1
antes de ejecutar nada, porque empieza por los requisitos del equipo
(Docker, Visual Studio Code y, en Windows, WSL2).

Para ejecutar las sesiones hace falta una copia de este repositorio. En una
terminal del equipo (en Windows, la de Ubuntu de WSL2):

```bash
git clone --depth 1 --branch 26-27 https://github.com/dsevilla/tcdm-public.git ~/tcdm-public
cd ~/tcdm-public
python3 -m venv .venv
.venv/bin/python -m pip install ipykernel
code .
```

Después, en Visual Studio Code, abre `s1/s1.ipynb`, elige `.venv` como
kernel y sigue el notebook de arriba abajo. Las dos órdenes de Python crean
el entorno que ejecuta la sesión 1; desde la sesión 2 los notebooks se
ejecutan dentro del clúster y ese entorno ya no se usa.

Antes de empezar cada sesión nueva, actualiza la copia desde la raíz:

```bash
git pull
```

## Qué contiene

| Ruta | Contenido |
| --- | --- |
| `s1/`, `s2/`, … | Un directorio por sesión, con su notebook (`sN/sN.ipynb`) y sus ficheros auxiliares. Se publican a medida que avanza el curso |
| `entorno/` | Los ficheros Docker Compose y el `Makefile` del laboratorio. Su `README.md` explica cómo arrancar y parar el clúster y qué hacer si algo falla |
| `docs/` | Las páginas web del curso, generadas automáticamente: no se editan a mano |

Las órdenes de terminal de las sesiones se escriben siempre desde la raíz
de esta copia (`~/tcdm-public`), por ejemplo `make -C entorno hadoop-up`.
