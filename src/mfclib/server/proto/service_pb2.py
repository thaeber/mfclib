# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: service.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'service.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rservice.proto\x1a\x1fgoogle/protobuf/timestamp.proto\"\x07\n\x05\x45mpty\"\r\n\x0bStopRequest2\\\n\rMFCController\x12$\n\nStopServer\x12\x0c.StopRequest\x1a\x06.Empty\"\x00\x12%\n\x11ServerHealthCheck\x12\x06.Empty\x1a\x06.Empty\"\x00\x42\x03\x90\x01\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'service_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\220\001\001'
  _globals['_EMPTY']._serialized_start=50
  _globals['_EMPTY']._serialized_end=57
  _globals['_STOPREQUEST']._serialized_start=59
  _globals['_STOPREQUEST']._serialized_end=72
  _globals['_MFCCONTROLLER']._serialized_start=74
  _globals['_MFCCONTROLLER']._serialized_end=166
_builder.BuildServices(DESCRIPTOR, 'service_pb2', _globals)
# @@protoc_insertion_point(module_scope)
