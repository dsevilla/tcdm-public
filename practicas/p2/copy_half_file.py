#! /usr/bin/env python3
from pyarrow.fs import FileSystem, FileInfo
import sys

fs1, path = FileSystem.from_uri(sys.argv[1])
fs2, path2 = FileSystem.from_uri(sys.argv[2])

f_info: FileInfo = ... # Obtener información del archivo en fs1

with fs1.open_input_file(path) as instream, \
        fs2.open_output_stream(path2) as outstream:
     # Mover el puntero de instream a la mitad del archivo
     # y copiar el resto del archivo en outstream
     # (se puede usar shutil o cualquier otra forma de copiar)
     ...