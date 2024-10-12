#! /usr/bin/env python3
from pyarrow.fs import FileSystem
import sys
import shutil

fs, path = FileSystem.from_uri(sys.argv[1])

with fs.open_input_stream(path) as stream:
    shutil.copyfileobj(stream, sys.stdout.buffer)