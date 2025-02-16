#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 Confluent Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional, Literal

from kafka_mocha.schema_registry.exceptions import SchemaRegistryError
from kafka_mocha.schema_registry.schema_registry_client import RegisteredSchema, Schema, _BaseRestClient
from kafka_mocha.schema_registry.srlogger import get_custom_logger


class _SchemaStore(object):

    def __init__(self):
        self.lock = Lock()
        self.max_id = 0
        self.schema_id_index = {}
        self.schema_index = {}
        self.subject_schemas = defaultdict(set)

    def set(self, registered_schema: RegisteredSchema) -> RegisteredSchema:
        with self.lock:
            self.max_id += 1
            rs = RegisteredSchema(
                schema_id=self.max_id,
                schema=registered_schema.schema,
                subject=registered_schema.subject,
                version=registered_schema.version,
            )
            self.schema_id_index[rs.schema_id] = rs
            self.schema_index[rs.schema] = rs.schema_id
            self.subject_schemas[rs.subject].add(rs)
            return rs

    def get_schema(self, schema_id: int) -> Optional[Schema]:
        with self.lock:
            rs = self.schema_id_index.get(schema_id, None)
            return rs.schema if rs else None

    def get_registered_schema_by_schema(self, subject_name: str, schema: Schema) -> Optional[RegisteredSchema]:
        with self.lock:
            if subject_name in self.subject_schemas:
                for rs in self.subject_schemas[subject_name]:
                    # if rs.schema == schema:  # For some reason, this comparison is not working
                    #     return rs
                    if (
                        rs.schema.schema_str == schema.schema_str
                        and rs.schema.schema_type == schema.schema_type
                        and rs.schema.references == schema.references
                        and rs.schema.metadata == schema.metadata
                        and rs.schema.rule_set == schema.rule_set
                    ):
                        return rs
            return None

    def get_latest_registered_schema_by_subject(self, subject_name: str) -> Optional[RegisteredSchema]:
        with self.lock:
            if subject_name in self.subject_schemas:
                return list(self.subject_schemas[subject_name])[-1]
            return None

    def get_version(self, subject_name: str, version: int) -> Optional[RegisteredSchema]:
        with self.lock:
            if subject_name in self.subject_schemas:
                for rs in self.subject_schemas[subject_name]:
                    if rs.version == version:
                        return rs
            return None

    def get_latest_version(self, subject_name: str) -> Optional[RegisteredSchema]:
        with self.lock:
            if subject_name in self.subject_schemas:
                latest_version = 0
                latest_schema = None
                for rs in self.subject_schemas[subject_name]:
                    if rs.version > latest_version:
                        latest_version = rs.version
                        latest_schema = rs
                return latest_schema
            return None

    def get_latest_with_metadata(self, subject_name: str, metadata: Dict[str, str]) -> Optional[RegisteredSchema]:
        with self.lock:
            if subject_name in self.subject_schemas:
                rs: RegisteredSchema
                for rs in self.subject_schemas[subject_name]:
                    if (
                        rs.schema
                        and rs.schema.metadata
                        and rs.schema.metadata.properties
                        and metadata.items() <= rs.schema.metadata.properties.properties.items()
                    ):
                        return rs
            return None

    def get_subjects(self) -> List[str]:
        with self.lock:
            return list(self.subject_schemas.keys())

    def get_versions(self, subject_name: str) -> List[int]:
        with self.lock:
            if subject_name in self.subject_schemas:
                return [rs.version for rs in self.subject_schemas[subject_name]]
            return []

    def remove_by_schema(self, registered_schema: RegisteredSchema):
        with self.lock:
            subject_name = registered_schema.subject
            if subject_name in self.subject_schemas:
                self.subject_schemas[subject_name].remove(registered_schema)

    def remove_by_subject(self, subject_name: str) -> List[int]:
        with self.lock:
            versions = []
            if subject_name in self.subject_schemas:
                for rs in self.subject_schemas[subject_name]:
                    versions.append(rs.version)
                    schema_id = self.schema_index.pop(rs.schema, None)
                    if schema_id is not None:
                        self.schema_id_index.pop(schema_id, None)

                del self.subject_schemas[subject_name]
            return versions

    def clear(self):
        with self.lock:
            self.schema_id_index.clear()
            self.schema_index.clear()
            self.subject_schemas.clear()


class MockSchemaRegistryClient(_BaseRestClient):
    _instance = None
    _lock = Lock()

    def __new__(
        cls,
        conf: dict,
        register_schemas: Optional[list[str]] = None,
        loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING",
    ):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        conf: dict,
        register_schemas: Optional[list[str]] = None,
        loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING",
    ):
        super().__init__(conf)
        self._store = _SchemaStore()
        self.logger = get_custom_logger(loglevel)  # noqa F821
        if register_schemas:
            self._register_schemas(register_schemas)

        self.logger.debug("Mock Schema Registry Client initialized.")

    def _register_schemas(self, register_schemas: list[str]) -> None:
        if isinstance(register_schemas, list):
            for schema in register_schemas:
                file_name = schema.split("/")[-1]
                extension = file_name.split(".")[-1]
                if extension == "avsc":
                    schema_type = "AVRO"
                elif extension == "json":
                    schema_type = "JSON"
                else:
                    raise SchemaRegistryError(
                        400, 40002, "Unsupported schema file format, only AVRO and JSON are supported."
                    )
                with open(schema, "r") as f:
                    avro_schema = json.loads(f.read())
                    avro_schema_str = json.dumps(avro_schema)
                    self.register_schema(
                        file_name + "-value", Schema(schema_str=avro_schema_str, schema_type=schema_type)
                    )
        else:
            raise SchemaRegistryError(400, 40001, "Invalid schema file list format.")

    def register_schema(self, subject_name: str, schema: "Schema", normalize_schemas: bool = False) -> int:
        self.logger.debug("Registering schema for subject: %s and schema: %s", subject_name, schema)
        registered_schema = self.register_schema_full_response(subject_name, schema, normalize_schemas)
        return registered_schema.schema_id

    def register_schema_full_response(
        self, subject_name: str, schema: "Schema", normalize_schemas: bool = False
    ) -> "RegisteredSchema":
        self.logger.debug("Registering schema (full response) for subject: %s and schema: %s", subject_name, schema)
        registered_schema = self._store.get_registered_schema_by_schema(subject_name, schema)
        if registered_schema is not None:
            return registered_schema

        latest_schema = self._store.get_latest_version(subject_name)
        latest_version = 1 if latest_schema is None else latest_schema.version + 1

        registered_schema = RegisteredSchema(schema_id=0, schema=schema, subject=subject_name, version=latest_version)

        registered_schema = self._store.set(registered_schema)

        return registered_schema

    def get_schema(self, schema_id: int, subject_name: str = None, fmt: str = None) -> "Schema":
        self.logger.debug("Getting schema for schema_id: %d", schema_id)
        schema = self._store.get_schema(schema_id)
        if schema is not None:
            return schema

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def lookup_schema(
        self, subject_name: str, schema: "Schema", normalize_schemas: bool = False, deleted: bool = False
    ) -> "RegisteredSchema":
        self.logger.debug("Looking up schema for subject: %s and schema: %s", subject_name, schema)
        registered_schema = self._store.get_registered_schema_by_schema(subject_name, schema)
        if registered_schema is not None:
            return registered_schema

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def get_subjects(self) -> List[str]:
        self.logger.info("Retrieving all registered subjects")
        return self._store.get_subjects()

    def delete_subject(self, subject_name: str, permanent: bool = False) -> List[int]:
        self.logger.info("Deleting for subject: %s", subject_name)
        return self._store.remove_by_subject(subject_name)

    def get_latest_version(self, subject_name: str, fmt: str = None) -> "RegisteredSchema":
        self.logger.debug("Getting latest schema version for subject: %s", subject_name)
        registered_schema = self._store.get_latest_version(subject_name)
        if registered_schema is not None:
            return registered_schema

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def get_latest_with_metadata(
        self, subject_name: str, metadata: Dict[str, str], deleted: bool = False, fmt: str = None
    ) -> "RegisteredSchema":
        self.logger.debug("Getting latest schema metadata for subject: %s and version: %s", subject_name, metadata)
        registered_schema = self._store.get_latest_with_metadata(subject_name, metadata)
        if registered_schema is not None:
            return registered_schema

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def get_version(
        self, subject_name: str, version: int, deleted: bool = False, fmt: str = None
    ) -> "RegisteredSchema":
        registered_schema = self._store.get_version(subject_name, version)
        self.logger.debug("Getting schema version for subject: %s and version: %d", subject_name, version)
        if registered_schema is not None:
            return registered_schema

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def get_versions(self, subject_name: str) -> List[int]:
        self.logger.debug("Getting versions for subject: %s", subject_name)
        return self._store.get_versions(subject_name)

    def delete_version(self, subject_name: str, version: int, permanent: bool = False) -> int:
        registered_schema = self._store.get_version(subject_name, version)
        if registered_schema is not None:
            self.logger.info("Deleting version: %d for subject: %s", version, subject_name)
            self._store.remove_by_schema(registered_schema)
            return registered_schema.schema_id

        raise SchemaRegistryError(404, 40400, "Schema Not Found")

    def set_config(
        self, subject_name: Optional[str] = None, config: "ServerConfig" = None  # noqa F821
    ) -> "ServerConfig":  # noqa F821
        self.logger.warning("Mock Schema Registry Client does not support configuration.")
        return None

    def get_config(self, subject_name: Optional[str] = None) -> "ServerConfig":  # noqa F821
        self.logger.warning("Mock Schema Registry Client does not support configuration.")
        return None

    def __del__(self):
        self.logger.debug("Mock Schema Registry Client has been terminated.")
