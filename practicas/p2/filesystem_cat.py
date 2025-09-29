#! /usr/bin/env python3
import shutil
import sys

from pyarrow.fs import FileSystem


def fs_cat(uri: str) -> None:
    """
    Lee el contenido de un archivo en el sistema de archivos
    y lo muestra en la salida estándar.

    Args:
        uri (str): URI del archivo a mostrar.
    """
    fs, path = FileSystem.from_uri(uri)

    with fs.open_input_stream(path) as stream:
        shutil.copyfileobj(stream, sys.stdout.buffer)


if __name__ == "__main__":
    # Si no se proporciona un argumento, se muestra un mensaje de error
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <uri>")
        sys.exit(1)

    fs_cat(sys.argv[1])
