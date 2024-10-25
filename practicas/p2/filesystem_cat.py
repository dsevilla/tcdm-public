#! /usr/bin/env python3
from pyarrow.fs import FileSystem
import sys
import shutil

def fs_cat(uri: str) -> None:
    fs, path = FileSystem.from_uri(uri)

    with fs.open_input_stream(path) as stream:
        shutil.copyfileobj(stream, sys.stdout.buffer)

if __name__ == "__main__":
    # Si no se proporciona un argumento, se muestra un mensaje de error
    if len(sys.argv) != 2:
        print("Uso: {} <uri>".format(sys.argv[0]))
        sys.exit(1)

    fs_cat(sys.argv[1])
