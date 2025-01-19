import os
import subprocess
from pathlib import Path

# compile proto file and create python stubs
proto_path = Path(__file__).parent / 'service.proto'
os.chdir(proto_path.parent)

res = subprocess.call(
    (
        rf'python -m grpc_tools.protoc -I . --python_out=. '
        rf'--grpc_python_out=. --mypy_out=. --mypy_grpc_out=. {proto_path.name}'
    ),
    shell=True,
)
print(f'Exit code: {res}')

# make imports relative
source_files = ['{0}_pb2_grpc.py', '{0}_pb2_grpc.pyi']
for filename in source_files:
    source_file = proto_path.parent / filename.format(proto_path.stem)
    source = source_file.read_text()

    # replace import
    source = source.replace(
        f'import {proto_path.stem}_pb2', f'from . import {proto_path.stem}_pb2'
    )
    source_file.write_text(source)
