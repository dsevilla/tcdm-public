#! /usr/bin/env python3
from pyarrow.fs import FileSystem, FileInfo
import sys

def copy_half_file(uri1: str, uri2: str) -> None:
    fs1, path = FileSystem.from_uri(uri1)
    fs2, path2 = FileSystem.from_uri(uri2)

    f_info: FileInfo = ... # Obtener información del archivo en fs1

    with fs1.open_input_file(path) as instream, \
         fs2.open_output_stream(path2) as outstream:
        # Mover el puntero de instream a la mitad del archivo
        # y copiar el resto del archivo en outstream
        # (se puede usar shutil o cualquier otra forma de copiar)
        ...

if __name__ == "__main__":
    # Si no se proporcionan dos argumentos, se muestra un mensaje de error
    if len(sys.argv) != 3:
        print("Uso: {} <uri1> <uri2>".format(sys.argv[0]))
        sys.exit(1)

    copy_half_file(sys.argv[1], sys.argv[2])
