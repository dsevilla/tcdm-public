# tcdm-public

Sitio público para la asignatura Tecnología de Computación de datos Masivos (TCDM) del máster de big data de la UMU, curso 26-27.

## Por dónde empezar

Las sesiones se pueden leer en la web sin instalar nada:
<https://dsevilla.github.io/tcdm-public/>. Para ejecutarlas hay que preparar
el equipo una sola vez, obtener una copia de este repositorio y abrir la
sesión 1. Las tres secciones siguientes lo explican en ese orden.

## Preparar el equipo

Hace falta, en cualquier sistema:

- Docker con Docker Compose v2, instalado y en ejecución;
- Visual Studio Code con las extensiones **Python** y **Jupyter**;
- `make`, que se usa a partir de la sesión 2 (`make -C entorno ...`);
- Python 3 con soporte de entornos virtuales, para el kernel de la sesión 1.

### Windows: WSL2 y Docker Desktop

En Windows todo se ejecuta dentro de WSL2, y `docker` **no funciona solo con
WSL2 instalado**: hace falta además Docker Desktop, correctamente
configurado.

1. **Instala WSL2.** Abre PowerShell como administrador y ejecuta:

   ```powershell
   wsl --install
   ```

   Esto instala WSL2 y una distribución Ubuntu por defecto, que ya trae
   Python 3. Reinicia el equipo si te lo pide.

2. **Instala Docker Desktop para Windows** desde
   [docker.com](https://www.docker.com/products/docker-desktop/) y, durante
   o después de la instalación, comprueba en Settings → General que
   **"Use the WSL 2 based engine"** está activado.

3. **Activa la integración WSL para tu distribución.** En Docker Desktop, ve
   a Settings → Resources → WSL Integration y activa el interruptor junto al
   nombre de tu distribución (por ejemplo, `Ubuntu`). **Este paso es el que
   más se olvida**: sin él, `docker` no se encuentra dentro de WSL2 aunque
   Docker Desktop esté instalado y en ejecución.

4. **Arranca Docker Desktop** y espera a que quede en marcha (no basta con
   tenerlo instalado; el motor debe estar realmente arrancado).

5. **Instala Visual Studio Code** con las extensiones **WSL**, **Python** y
   **Jupyter**. El material se abre siempre *desde dentro* de WSL2 —con
   "Connect to WSL" desde la paleta de comandos, o ejecutando `code .` en una
   terminal de Ubuntu—, no como una carpeta nativa de Windows.

6. **Instala `make` y el soporte de entornos virtuales de Python** en Ubuntu
   de WSL2. Sin `python3-venv`, Visual Studio Code no puede crear el entorno
   de Python de la sesión 1:

   ```bash
   sudo apt update && sudo apt install -y make python3-venv
   ```

### Linux y macOS

No hacen falta WSL2 ni la integración anterior. Basta con Docker (Docker
Engine en Linux, Docker Desktop en macOS) instalado y en ejecución, Visual
Studio Code con las extensiones **Python** y **Jupyter**, `make` y Python 3.
En Debian y Ubuntu, `make` y el soporte de entornos virtuales se instalan
con `sudo apt install -y make python3-venv`; en macOS, `make` viene con las
herramientas de línea de órdenes de Xcode (`xcode-select --install`).

### Comprobar la instalación

En una terminal del equipo (en Windows, la de Ubuntu de WSL2):

```bash
docker --version
docker compose version
docker info
make --version
python3 --version
```

Si alguna orden falla, revisa el paso correspondiente antes de seguir: las
sesiones dan por hecho que todas funcionan desde esa terminal. En Windows,
un fallo de `docker` suele deberse a los pasos 2–4. La última orden muestra
la versión de Python con la que Visual Studio Code creará el entorno de la
sesión 1; anótala si tienes que consultar un problema con el kernel.

## Obtener el material

En una terminal del equipo (en Windows, la de Ubuntu de WSL2):

<p align="center" style="text-align: center;"><img src="https://dsevilla.github.io/tcdm-public/figs/anim-host-git-clone.gif" alt="Animación: en una terminal de tu equipo (host) se teclean git clone, cd tcdm-public y code . &amp;" width="832" style="display: block; margin: 0 auto; max-width: 100%; height: auto;"></p>

```bash
git clone --depth 1 --branch 26-27 https://github.com/dsevilla/tcdm-public.git ~/tcdm-public
cd ~/tcdm-public
```

La animación abrevia la orden de clonado: la completa es la del bloque
anterior, que fija la rama `26-27` y el directorio de destino. Su última
orden, `code . &`, abre la carpeta en Visual Studio Code y devuelve el
control a la terminal.

En Windows conviene clonar dentro del sistema de ficheros de WSL2
(`~/tcdm-public`) y no en `/mnt/c/...`: evita problemas de integración y la
entrada/salida es mucho más rápida.

Antes de empezar cada sesión nueva, actualiza la copia desde la raíz:

```bash
git pull
```

## Abrir la sesión 1

Abre la carpeta `~/tcdm-public` en Visual Studio Code y, en ella,
`s1/s1.ipynb`. Si Visual Studio Code ofrece instalar las extensiones
recomendadas, acepta.

El kernel de la sesión 1 es un Python de tu equipo y lo prepara Visual
Studio Code: pulsa **Select Kernel → Python Environments → Create Python
Environment → Venv**. Crea un entorno virtual `.venv` en la carpeta abierta,
instala en él `ipykernel` (acepta si lo pide al ejecutar la primera celda) y
lo deja elegido como kernel.

Desde la sesión 2 los notebooks se ejecutan dentro del clúster, y
`s2/s2.ipynb` explica al principio cómo conectarse.

## Qué contiene

| Ruta | Contenido |
| --- | --- |
| `s1/`, `s2/`, … | Un directorio por sesión, con su notebook (`sN/sN.ipynb`) y sus ficheros auxiliares. Se publican a medida que avanza el curso |
| `entorno/` | Los ficheros Docker Compose y el `Makefile` del laboratorio. Su `README.md` explica cómo arrancar y parar el clúster y qué hacer si algo falla |
| `docs/` | Las páginas web del curso, generadas automáticamente: no se editan a mano |

Las órdenes de terminal de las sesiones se escriben siempre desde la raíz
de esta copia (`~/tcdm-public`), por ejemplo `make -C entorno hadoop-up`.
