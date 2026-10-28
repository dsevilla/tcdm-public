#!/usr/bin/env bash
#
# Comprueba que tu copia del material y tu equipo están listos para una sesión.
#
# Se ejecuta en una terminal de tu equipo (en Windows, la de Ubuntu de WSL2),
# sin instalar nada y sin descargarlo antes:
#
#   curl -fsSL https://raw.githubusercontent.com/dsevilla/tcdm-public/26-27/entorno/comprobar-entorno.sh | bash -s s3
#
# o, una vez actualizada tu copia del material, desde su raíz:
#
#   bash entorno/comprobar-entorno.sh s3
#
# Hace tres cosas:
#
#   1. comprueba que están instaladas las herramientas del curso (Docker,
#      Docker Compose v2, make, Python 3 con venv, git y curl);
#   2. descarga el manifiesto de la última versión publicada en
#      https://github.com/dsevilla/tcdm-public (rama 26-27) y compara con él,
#      fichero a fichero, todo lo que necesita la sesión indicada: s1, s2, ...
#      hasta ella, y las partes de entorno/ que esas sesiones usan;
#   3. si tu copia es un clon de git, indica en qué versión está y cómo
#      actualizarla.
#
# El manifiesto (entorno/MANIFIESTO.txt) lo genera la publicación del material:
# una línea por fichero, "<primera sesión> <huella sha256> <ruta>". En los
# notebooks la huella ignora las salidas guardadas al ejecutarlos y cuenta sólo
# el tipo y el texto de cada celda, así que ejecutar un notebook no lo hace
# parecer desactualizado.
#
# Con --huella FICHERO muestra la huella de un fichero con ese mismo criterio.
# Lo usa la publicación para generar el manifiesto.

set -u

# Las variables TCDM_REPOSITORIO_* sólo sirven para probar el script contra
# una copia local.
GITHUB_GIT="https://github.com/dsevilla/tcdm-public.git"
GITHUB_RAW="https://raw.githubusercontent.com/dsevilla/tcdm-public"
REPOSITORIO_GIT="${TCDM_REPOSITORIO_GIT:-$GITHUB_GIT}"
REPOSITORIO_RAW="${TCDM_REPOSITORIO_RAW:-$GITHUB_RAW}"
RAMA="26-27"
MANIFIESTO="entorno/MANIFIESTO.txt"
COMPROBADOR="entorno/comprobar-entorno.sh"

# Huella de un fichero. Un notebook se resume por el tipo y el texto de sus
# celdas; cualquier otro fichero, por su contenido.
huella() {
    case "$1" in
    *.ipynb)
        python3 -I - "$1" <<'PY'
import hashlib
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fichero:
    cuaderno = json.load(fichero)
resumen = hashlib.sha256()
for celda in cuaderno["cells"]:
    texto = celda["source"]
    if isinstance(texto, list):
        texto = "".join(texto)
    entrada = json.dumps([celda["cell_type"], texto], ensure_ascii=False)
    resumen.update(entrada.encode("utf-8"))
print(resumen.hexdigest())
PY
        ;;
    *)
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum -- "$1" | cut -d ' ' -f 1
        else
            shasum -a 256 -- "$1" | cut -d ' ' -f 1
        fi
        ;;
    esac
}

uso() {
    echo "Uso: bash entorno/comprobar-entorno.sh sX    (X de 1 a 8)"
    echo "Comprueba que tu equipo y tu copia del material están listos"
    echo "para la sesión sX."
}

# Todo el programa está en una función que se invoca en la última línea. Así,
# con "curl ... | bash", bash lee el script entero antes de ejecutar nada y
# ninguna orden puede consumir por error el resto del script de la entrada.
principal() {
    if [ "${1:-}" = "--huella" ]; then
        huella "${2:?Falta el fichero}"
        exit 0
    fi

    case "${1:-}" in
    -h | --help)
        uso
        exit 0
        ;;
    s[1-8]) ;;
    *)
        uso >&2
        exit 2
        ;;
    esac
    sesion="$1"
    numero_sesion="${sesion#s}"

    if [ -t 1 ]; then
        verde=$'\033[32m'
        rojo=$'\033[31m'
        amarillo=$'\033[33m'
        negrita=$'\033[1m'
        normal=$'\033[0m'
    else
        verde="" rojo="" amarillo="" negrita="" normal=""
    fi

    errores=0
    avisos=0
    ok() { echo "  ${verde}✔${normal} $1"; }
    fallo() {
        echo "  ${rojo}✘${normal} $1"
        errores=$((errores + 1))
    }
    aviso() {
        echo "  ${amarillo}!${normal} $1"
        avisos=$((avisos + 1))
    }
    pista() { echo "      $1"; }
    titulo() { echo "${negrita}$1${normal}"; }

    # Raíz del material: el directorio actual si contiene s1/ o entorno/ (también
    # cuando el script llega por "curl | bash") y, si no, la carpeta que contiene
    # a entorno/, o ~/tcdm-public, donde el README manda clonar el material.
    raiz=""
    directorio_script="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    for candidato in "${TCDM_RAIZ:-}" "$PWD" "$directorio_script/.." \
        "$HOME/tcdm-public"; do
        if [ -z "$candidato" ]; then
            continue
        fi
        if [ -d "$candidato/s1" ] || [ -d "$candidato/entorno" ]; then
            raiz="$(cd "$candidato" && pwd)"
            break
        fi
    done
    if [ -z "$raiz" ]; then
        echo "No encuentro el material (las carpetas s1/, s2/... y" \
            "entorno/)." >&2
        echo "Ejecuta el script desde la raíz de tu copia, por ejemplo:" >&2
        echo "  cd ~/tcdm-public" >&2
        echo "  bash entorno/comprobar-entorno.sh $sesion" >&2
        exit 2
    fi

    echo "Comprobando el entorno para la sesión $sesion"
    echo "Material en: $raiz"
    if grep -qi microsoft /proc/version 2>/dev/null; then
        en_wsl=1
        echo "Sistema: WSL2"
    else
        en_wsl=0
    fi
    echo

    # ---------------------------------------------------------------------------
    titulo "Herramientas del equipo"

    if command -v git >/dev/null 2>&1; then
        ok "git"
        hay_git=1
    else
        hay_git=0
        fallo "git no está instalado"
        pista "Instálalo con: sudo apt update && sudo apt install -y git"
    fi

    if command -v curl >/dev/null 2>&1; then
        ok "curl"
    elif command -v wget >/dev/null 2>&1; then
        ok "wget (curl no está instalado, pero basta para la descarga)"
    else
        fallo "ni curl ni wget están instalados"
        pista "Instálalo con: sudo apt update && sudo apt install -y curl"
    fi

    if command -v make >/dev/null 2>&1; then
        ok "make"
    elif [ "$numero_sesion" -ge 2 ]; then
        fallo "make no está instalado (se usa desde la sesión 2)"
        pista "Instálalo con: sudo apt update && sudo apt install -y make"
    else
        aviso "make no está instalado (lo necesitarás a partir de la sesión 2)"
        pista "Instálalo con: sudo apt update && sudo apt install -y make"
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        fallo "python3 no está instalado"
        pista "Instálalo con:"
        pista "  sudo apt update && sudo apt install -y python3 python3-venv"
    elif python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
        ok "python3 con venv ($(python3 --version 2>&1))"
    else
        fallo "python3 no puede crear entornos virtuales (falta python3-venv)"
        pista "Visual Studio Code lo necesita para el kernel de la sesión 1."
        pista "Instálalo con:"
        pista "  sudo apt update && sudo apt install -y python3-venv"
    fi

    hay_docker=0
    if ! command -v docker >/dev/null 2>&1; then
        fallo "docker no se encuentra"
        if [ "$en_wsl" = 1 ]; then
            pista "En WSL2 hace falta Docker Desktop, arrancado y con la"
            pista "integración WSL activada para tu distribución (Settings →"
            pista "Resources → WSL Integration)."
        else
            pista "Instala Docker Engine con el plugin de Compose v2:"
            pista "  https://docs.docker.com/engine/install/"
        fi
    elif ! docker info >/dev/null 2>&1; then
        fallo "docker está instalado, pero el motor no responde"
        if [ "$en_wsl" = 1 ]; then
            pista "Arranca Docker Desktop y espera a que esté en marcha."
        else
            pista "Arráncalo con: sudo systemctl start docker"
            pista "Si el error es de permisos, ejecuta"
            pista "  sudo usermod -aG docker \"\$USER\""
            pista "y vuelve a abrir la terminal."
        fi
    else
        ok "docker en marcha"
        hay_docker=1
        if docker compose version >/dev/null 2>&1; then
            ok "docker compose ($(docker compose version --short 2>/dev/null))"
        else
            fallo "falta Docker Compose v2 (la orden docker compose)"
            pista "Instala el plugin:"
            pista "  sudo apt install -y docker-compose-plugin"
        fi
    fi
    echo

    # ---------------------------------------------------------------------------
    titulo "Última versión publicada"

    if [ "$hay_git" = 1 ]; then
        ultimo_commit="$(GIT_TERMINAL_PROMPT=0 git ls-remote \
            "$REPOSITORIO_GIT" "refs/heads/$RAMA" 2>/dev/null | cut -f 1)"
    else
        ultimo_commit=""
    fi
    # Con el commit exacto se evita la caché de raw.githubusercontent.com, que
    # puede tardar unos minutos en ver una publicación recién hecha.
    referencia="${ultimo_commit:-$RAMA}"

    descargar() {
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL --max-time 30 "$1"
        else
            wget -qO- --timeout=30 "$1"
        fi
    }

    url_manifiesto="$REPOSITORIO_RAW/$referencia/$MANIFIESTO"
    manifiesto="$(descargar "$url_manifiesto" 2>/dev/null)"
    if [ -z "$manifiesto" ]; then
        fallo "no puedo descargar el manifiesto de $url_manifiesto"
        pista "Comprueba la conexión a Internet. Si funciona, el material"
        pista "aún no se ha publicado con este comprobador."
        echo
        echo "${rojo}Resultado: no se puede comprobar el material.${normal}"
        exit 1
    fi
    if [ -n "$ultimo_commit" ]; then
        ok "rama $RAMA de tcdm-public en el commit ${ultimo_commit:0:7}"
    else
        ok "rama $RAMA de tcdm-public"
    fi

    ultima_publicada="$(sed -n 's/^# ultima-sesion: s\([1-8]\)$/\1/p' \
        <<<"$manifiesto")"
    if [ -z "$ultima_publicada" ]; then
        fallo "el manifiesto descargado no tiene el formato esperado"
        exit 1
    fi
    if [ "$numero_sesion" -gt "$ultima_publicada" ]; then
        echo
        echo "${rojo}La sesión $sesion todavía no está publicada" \
            "(la última es s$ultima_publicada).${normal}"
        exit 1
    fi
    echo

    # ---------------------------------------------------------------------------
    if [ "$numero_sesion" = 1 ]; then
        titulo "Ficheros de s1 y de entorno/"
    else
        titulo "Ficheros de s1 a $sesion y de entorno/"
    fi

    errores_antes="$errores"
    if ! command -v python3 >/dev/null 2>&1; then
        fallo "sin python3 no se pueden comparar los notebooks"
    else
        comprobados=0
        faltan=()
        distintos=()
        while read -r primera_sesion esperada ruta; do
            case "$primera_sesion" in
            "" | \#*) continue ;;
            esac
            if [ "${primera_sesion#s}" -gt "$numero_sesion" ]; then
                continue
            fi
            comprobados=$((comprobados + 1))
            if [ ! -f "$raiz/$ruta" ]; then
                faltan+=("$ruta")
            elif [ "$(huella "$raiz/$ruta")" != "$esperada" ]; then
                distintos+=("$ruta")
            fi
        done <<<"$manifiesto"

        if [ "${#faltan[@]}" -eq 0 ] && [ "${#distintos[@]}" -eq 0 ]; then
            ok "los $comprobados ficheros coinciden con la versión publicada"
        else
            for ruta in ${faltan[@]+"${faltan[@]}"}; do
                fallo "falta $ruta"
            done
            for ruta in ${distintos[@]+"${distintos[@]}"}; do
                case "$ruta" in
                *.ipynb)
                    fallo "$ruta es distinto del publicado"
                    pista "(versión antigua, o celdas que has cambiado tú)"
                    ;;
                *) fallo "$ruta es distinto del publicado" ;;
                esac
            done
            coinciden=$((comprobados - ${#faltan[@]} - ${#distintos[@]}))
            ok "$coinciden de $comprobados ficheros coinciden"
        fi
    fi
    problemas_ficheros=$((errores - errores_antes))
    echo

    # ---------------------------------------------------------------------------
    titulo "Copia local (git)"

    if [ "$hay_git" = 0 ]; then
        aviso "sin git no se puede revisar de qué versión es tu copia"
    elif ! git -C "$raiz" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        aviso "esta carpeta no es un clon de git: no se puede actualizar"
        pista "Descarga el material de nuevo con:"
        pista "  git clone --depth 1 --branch $RAMA \\"
        pista "    $REPOSITORIO_GIT ~/tcdm-public"
    else
        rama_local="$(git -C "$raiz" symbolic-ref --short -q HEAD \
            || echo "(sin rama)")"
        commit_local="$(git -C "$raiz" rev-parse HEAD)"
        if [ "$rama_local" = "$RAMA" ]; then
            ok "rama $rama_local"
        else
            fallo "estás en la rama $rama_local y el curso usa la $RAMA"
            pista "Vuelve a clonar:"
            pista "  git clone --depth 1 --branch $RAMA \\"
            pista "    $REPOSITORIO_GIT ~/tcdm-public"
        fi
        if [ -z "$ultimo_commit" ]; then
            aviso "no he podido consultar el último commit de $REPOSITORIO_GIT"
        elif [ "$commit_local" = "$ultimo_commit" ]; then
            ok "tu copia está en el último commit (${commit_local:0:7})"
        elif [ "$problemas_ficheros" -gt 0 ]; then
            aviso "tu copia está en el commit ${commit_local:0:7} y la" \
                "última publicada es la ${ultimo_commit:0:7}"
        else
            ok "tu copia está en el commit ${commit_local:0:7}; hay uno más" \
                "reciente (${ultimo_commit:0:7}), pero no cambia nada de lo" \
                "que necesita $sesion"
        fi
    fi
    echo

    # ---------------------------------------------------------------------------
    if [ "$hay_docker" = 1 ] && [ "$numero_sesion" -ge 3 ]; then
        titulo "Contenedores de versiones anteriores"
        if docker ps -a --format '{{.Names}}' 2>/dev/null \
            | grep -qx 'tcdm-s3-client'; then
            aviso "queda el contenedor tcdm-s3-client de una versión anterior"
            pista "Ya no se usa; elimínalo con: docker rm -f tcdm-s3-client"
        else
            ok "ninguno"
        fi
        echo
    fi

    # ---------------------------------------------------------------------------
    if [ "$errores" -eq 0 ]; then
        if [ "$avisos" -eq 0 ]; then
            echo "${verde}${negrita}Todo listo para la sesión $sesion.$normal"
        else
            echo "${verde}${negrita}Todo lo necesario para la sesión $sesion" \
                "está en orden${normal} (con $avisos aviso(s) arriba)."
        fi
        exit 0
    fi

    echo "${rojo}${negrita}Hay $errores problema(s) que resolver antes de" \
        "la sesión $sesion.${normal}"
    if [ "$problemas_ficheros" -gt 0 ]; then
        echo
        echo "Para actualizar el material, desde la raíz de tu copia:"
        echo "  make -C entorno actualizar"
        echo "Si ni siquiera tienes este comprobador, ejecuta el último sin"
        echo "descargarlo:"
        echo "  curl -fsSL $GITHUB_RAW/$RAMA/$COMPROBADOR | bash -s $sesion"
    fi
    echo
    echo "Si el problema persiste, copia toda esta salida y envíamela."
    exit 1
}

principal "$@" </dev/null
