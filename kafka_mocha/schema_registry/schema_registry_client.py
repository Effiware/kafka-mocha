#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Confluent Inc.
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
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast
from urllib.parse import unquote, urlparse

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T")
VALID_AUTH_PROVIDERS = ["URL", "USER_INFO"]


class RuleKind(str, Enum):
    CONDITION = "CONDITION"
    TRANSFORM = "TRANSFORM"

    def __str__(self) -> str:
        return str(self.value)


class RuleMode(str, Enum):
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"
    UPDOWN = "UPDOWN"
    READ = "READ"
    WRITE = "WRITE"
    WRITEREAD = "WRITEREAD"

    def __str__(self) -> str:
        return str(self.value)


class ConfigCompatibilityLevel(str, Enum):
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"
    NONE = "NONE"

    def __str__(self) -> str:
        return str(self.value)


class _BaseRestClient(object):

    def __init__(self, conf: dict):
        # copy dict to avoid mutating the original
        conf_copy = conf.copy()

        base_url = conf_copy.pop("url", None)
        if base_url is None:
            raise ValueError("Missing required configuration property url")
        if not isinstance(base_url, str):
            raise TypeError("url must be a str, not " + str(type(base_url)))
        base_urls = []
        for url in base_url.split(","):
            url = url.strip().rstrip("/")
            if not url.startswith("http") and not url.startswith("mock"):
                raise ValueError("Invalid url {}".format(url))
            base_urls.append(url)
        if not base_urls:
            raise ValueError("Missing required configuration property url")
        self.base_urls = base_urls

        self.verify = True
        ca = conf_copy.pop("ssl.ca.location", None)
        if ca is not None:
            self.verify = ca

        key: Optional[str] = conf_copy.pop("ssl.key.location", None)
        client_cert: Optional[str] = conf_copy.pop("ssl.certificate.location", None)
        self.cert: Union[str, Tuple[str, str], None] = None

        if client_cert is not None and key is not None:
            self.cert = (client_cert, key)

        if client_cert is not None and key is None:
            self.cert = client_cert

        if key is not None and client_cert is None:
            raise ValueError("ssl.certificate.location required when" " configuring ssl.key.location")

        parsed = urlparse(self.base_urls[0])
        try:
            userinfo = (unquote(parsed.username), unquote(parsed.password))
        except (AttributeError, TypeError):
            userinfo = ("", "")
        if "basic.auth.user.info" in conf_copy:
            if userinfo != ("", ""):
                raise ValueError(
                    "basic.auth.user.info configured with"
                    " userinfo credentials in the URL."
                    " Remove userinfo credentials from the url or"
                    " remove basic.auth.user.info from the"
                    " configuration"
                )

            userinfo = tuple(conf_copy.pop("basic.auth.user.info", "").split(":", 1))

            if len(userinfo) != 2:
                raise ValueError("basic.auth.user.info must be in the form" " of {username}:{password}")

        self.auth = userinfo if userinfo != ("", "") else None

        # The following adds support for proxy config
        # If specified: it uses the specified proxy details when making requests
        self.proxy = None
        proxy = conf_copy.pop("proxy", None)
        if proxy is not None:
            self.proxy = proxy

        self.timeout = None
        timeout = conf_copy.pop("timeout", None)
        if timeout is not None:
            self.timeout = timeout

        self.cache_capacity = 1000
        cache_capacity = conf_copy.pop("cache.capacity", None)
        if cache_capacity is not None:
            if not isinstance(cache_capacity, (int, float)):
                raise TypeError("cache.capacity must be a number, not " + str(type(cache_capacity)))
            self.cache_capacity = cache_capacity

        self.cache_latest_ttl_sec = None
        cache_latest_ttl_sec = conf_copy.pop("cache.latest.ttl.sec", None)
        if cache_latest_ttl_sec is not None:
            if not isinstance(cache_latest_ttl_sec, (int, float)):
                raise TypeError("cache.latest.ttl.sec must be a number, not " + str(type(cache_latest_ttl_sec)))
            self.cache_latest_ttl_sec = cache_latest_ttl_sec

        self.max_retries = 3
        max_retries = conf_copy.pop("max.retries", None)
        if max_retries is not None:
            if not isinstance(timeout, (int, float)):
                raise TypeError("max.retries must be a number, not " + str(type(max_retries)))
            self.max_retries = max_retries

        self.retries_wait_ms = 1000
        retries_wait_ms = conf_copy.pop("retries.wait.ms", None)
        if retries_wait_ms is not None:
            if not isinstance(retries_wait_ms, (int, float)):
                raise TypeError("retries.wait.ms must be a number, not " + str(type(retries_wait_ms)))
            self.retries_wait_ms = retries_wait_ms

        self.retries_max_wait_ms = 20000
        retries_max_wait_ms = conf_copy.pop("retries.max.wait.ms", None)
        if retries_max_wait_ms is not None:
            if not isinstance(retries_max_wait_ms, (int, float)):
                raise TypeError("retries.max.wait.ms must be a number, not " + str(type(retries_max_wait_ms)))
            self.retries_max_wait_ms = retries_max_wait_ms

        # Any leftover keys are unknown to _RestClient
        if len(conf_copy) > 0:
            raise ValueError("Unrecognized properties: {}".format(", ".join(conf_copy.keys())))

    def get(self, url: str, query: dict = None) -> Any:
        raise NotImplementedError()

    def post(self, url: str, body: dict, **kwargs) -> Any:
        raise NotImplementedError()

    def delete(self, url: str) -> Any:
        raise NotImplementedError()

    def put(self, url: str, body: dict = None) -> Any:
        raise NotImplementedError()


@_attrs_define
class RuleParams:
    params: Dict[str, str] = _attrs_field(factory=dict, hash=False)

    def to_dict(self) -> Dict[str, Any]:
        field_dict: Dict[str, Any] = {}
        field_dict.update(self.params)

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        rule_params = cls(params=d)

        return rule_params

    def __hash__(self):
        return hash(frozenset(self.params.items()))


@_attrs_define(frozen=True)
class Rule:
    name: Optional[str]
    doc: Optional[str]
    kind: Optional[RuleKind]
    mode: Optional[RuleMode]
    type: Optional[str]
    tags: Optional[List[str]] = _attrs_field(hash=False)
    params: Optional[RuleParams]
    expr: Optional[str]
    on_success: Optional[str]
    on_failure: Optional[str]
    disabled: Optional[bool]

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        doc = self.doc

        kind_str: Optional[str] = None
        if self.kind is not None:
            kind_str = self.kind.value

        mode_str: Optional[str] = None
        if self.mode is not None:
            mode_str = self.mode.value

        rule_type = self.type

        tags = self.tags

        _params: Optional[Dict[str, Any]] = None
        if self.params is not None:
            _params = self.params.to_dict()

        expr = self.expr

        on_success = self.on_success

        on_failure = self.on_failure

        disabled = self.disabled

        field_dict: Dict[str, Any] = {}
        field_dict.update({})
        if name is not None:
            field_dict["name"] = name
        if doc is not None:
            field_dict["doc"] = doc
        if kind_str is not None:
            field_dict["kind"] = kind_str
        if mode_str is not None:
            field_dict["mode"] = mode_str
        if type is not None:
            field_dict["type"] = rule_type
        if tags is not None:
            field_dict["tags"] = tags
        if _params is not None:
            field_dict["params"] = _params
        if expr is not None:
            field_dict["expr"] = expr
        if on_success is not None:
            field_dict["onSuccess"] = on_success
        if on_failure is not None:
            field_dict["onFailure"] = on_failure
        if disabled is not None:
            field_dict["disabled"] = disabled

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name", None)

        doc = d.pop("doc", None)

        _kind = d.pop("kind", None)
        kind: Optional[RuleKind] = None
        if _kind is not None:
            kind = RuleKind(_kind)

        _mode = d.pop("mode", None)
        mode: Optional[RuleMode] = None
        if _mode is not None:
            mode = RuleMode(_mode)

        rule_type = d.pop("type", None)

        tags = cast(List[str], d.pop("tags", None))

        _params: Optional[Dict[str, Any]] = d.pop("params", None)
        params: Optional[RuleParams] = None
        if _params is not None:
            params = RuleParams.from_dict(_params)

        expr = d.pop("expr", None)

        on_success = d.pop("onSuccess", None)

        on_failure = d.pop("onFailure", None)

        disabled = d.pop("disabled", None)

        rule = cls(
            name=name,
            doc=doc,
            kind=kind,
            mode=mode,
            type=rule_type,
            tags=tags,
            params=params,
            expr=expr,
            on_success=on_success,
            on_failure=on_failure,
            disabled=disabled,
        )

        return rule


@_attrs_define
class RuleSet:
    migration_rules: Optional[List["Rule"]] = _attrs_field(hash=False)
    domain_rules: Optional[List["Rule"]] = _attrs_field(hash=False)

    def to_dict(self) -> Dict[str, Any]:
        _migration_rules: Optional[List[Dict[str, Any]]] = None
        if self.migration_rules is not None:
            _migration_rules = []
            for migration_rules_item_data in self.migration_rules:
                migration_rules_item = migration_rules_item_data.to_dict()
                _migration_rules.append(migration_rules_item)

        _domain_rules: Optional[List[Dict[str, Any]]] = None
        if self.domain_rules is not None:
            _domain_rules = []
            for domain_rules_item_data in self.domain_rules:
                domain_rules_item = domain_rules_item_data.to_dict()
                _domain_rules.append(domain_rules_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update({})
        if _migration_rules is not None:
            field_dict["migrationRules"] = _migration_rules
        if _domain_rules is not None:
            field_dict["domainRules"] = _domain_rules

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        migration_rules = []
        _migration_rules = d.pop("migrationRules", None)
        for migration_rules_item_data in _migration_rules or []:
            migration_rules_item = Rule.from_dict(migration_rules_item_data)
            migration_rules.append(migration_rules_item)

        domain_rules = []
        _domain_rules = d.pop("domainRules", None)
        for domain_rules_item_data in _domain_rules or []:
            domain_rules_item = Rule.from_dict(domain_rules_item_data)
            domain_rules.append(domain_rules_item)

        rule_set = cls(
            migration_rules=migration_rules,
            domain_rules=domain_rules,
        )

        return rule_set

    def __hash__(self):
        return hash(frozenset((self.migration_rules or []) + (self.domain_rules or [])))


@_attrs_define
class MetadataTags:
    tags: Dict[str, List[str]] = _attrs_field(factory=dict, hash=False)

    def to_dict(self) -> Dict[str, Any]:
        field_dict: Dict[str, Any] = {}
        for prop_name, prop in self.tags.items():
            field_dict[prop_name] = prop

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        tags = {}
        for prop_name, prop_dict in d.items():
            tag = cast(List[str], prop_dict)

            tags[prop_name] = tag

        metadata_tags = cls(tags=tags)

        return metadata_tags

    def __hash__(self):
        return hash(frozenset(self.tags.items()))


@_attrs_define
class MetadataProperties:
    properties: Dict[str, str] = _attrs_field(factory=dict, hash=False)

    def to_dict(self) -> Dict[str, Any]:
        field_dict: Dict[str, Any] = {}
        field_dict.update(self.properties)

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        metadata_properties = cls(properties=d)

        return metadata_properties

    def __hash__(self):
        return hash(frozenset(self.properties.items()))


@_attrs_define(frozen=True)
class Metadata:
    tags: Optional[MetadataTags]
    properties: Optional[MetadataProperties]
    sensitive: Optional[List[str]] = _attrs_field(hash=False)

    def to_dict(self) -> Dict[str, Any]:
        _tags: Optional[Dict[str, Any]] = None
        if self.tags is not None:
            _tags = self.tags.to_dict()

        _properties: Optional[Dict[str, Any]] = None
        if self.properties is not None:
            _properties = self.properties.to_dict()

        sensitive: Optional[List[str]] = None
        if self.sensitive is not None:
            sensitive = []
            for sensitive_item in self.sensitive:
                sensitive.append(sensitive_item)

        field_dict: Dict[str, Any] = {}
        if _tags is not None:
            field_dict["tags"] = _tags
        if _properties is not None:
            field_dict["properties"] = _properties
        if sensitive is not None:
            field_dict["sensitive"] = sensitive

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        _tags: Optional[Dict[str, Any]] = d.pop("tags", None)
        tags: Optional[MetadataTags] = None
        if _tags is not None:
            tags = MetadataTags.from_dict(_tags)

        _properties: Optional[Dict[str, Any]] = d.pop("properties", None)
        properties: Optional[MetadataProperties] = None
        if _properties is not None:
            properties = MetadataProperties.from_dict(_properties)

        sensitive = []
        _sensitive = d.pop("sensitive", None)
        for sensitive_item in _sensitive or []:
            sensitive.append(sensitive_item)

        metadata = cls(
            tags=tags,
            properties=properties,
            sensitive=sensitive,
        )

        return metadata


@_attrs_define(frozen=True)
class SchemaReference:
    name: Optional[str]
    subject: Optional[str]
    version: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        subject = self.subject

        version = self.version

        field_dict: Dict[str, Any] = {}
        if name is not None:
            field_dict["name"] = name
        if subject is not None:
            field_dict["subject"] = subject
        if version is not None:
            field_dict["version"] = version

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name", None)

        subject = d.pop("subject", None)

        version = d.pop("version", None)

        schema_reference = cls(
            name=name,
            subject=subject,
            version=version,
        )

        return schema_reference


@_attrs_define(frozen=True, cache_hash=True, eq=True)
class Schema:
    """
    An unregistered schema.
    """

    schema_str: Optional[str]
    schema_type: Optional[str] = "AVRO"
    references: Optional[List[SchemaReference]] = _attrs_field(factory=list, hash=False)
    metadata: Optional[Metadata] = None
    rule_set: Optional[RuleSet] = None

    def to_dict(self) -> Dict[str, Any]:
        schema = self.schema_str

        schema_type = self.schema_type

        _references: Optional[List[Dict[str, Any]]] = []
        if self.references is not None:
            for references_item_data in self.references:
                references_item = references_item_data.to_dict()
                _references.append(references_item)

        _metadata: Optional[Dict[str, Any]] = None
        if isinstance(self.metadata, Metadata):
            _metadata = self.metadata.to_dict()

        _rule_set: Optional[Dict[str, Any]] = None
        if isinstance(self.rule_set, RuleSet):
            _rule_set = self.rule_set.to_dict()

        field_dict: Dict[str, Any] = {}
        if schema is not None:
            field_dict["schema"] = schema
        if schema_type is not None:
            field_dict["schemaType"] = schema_type
        if _references is not None:
            field_dict["references"] = _references
        if _metadata is not None:
            field_dict["metadata"] = _metadata
        if _rule_set is not None:
            field_dict["ruleSet"] = _rule_set

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        schema = d.pop("schema", None)
        schema_str = json.dumps(schema)
        schema_type = d.pop("schemaType", "AVRO")

        references = []
        _references = d.pop("references", None)
        for references_item_data in _references or []:
            references_item = SchemaReference.from_dict(references_item_data)

            references.append(references_item)

        def _parse_metadata(data: object) -> Optional[Metadata]:
            if data is None:
                return data
            if not isinstance(data, dict):
                raise TypeError()
            return Metadata.from_dict(data)

        metadata = _parse_metadata(d.pop("metadata", None))

        def _parse_rule_set(data: object) -> Optional[RuleSet]:
            if data is None:
                return data
            if not isinstance(data, dict):
                raise TypeError()
            return RuleSet.from_dict(data)

        rule_set = _parse_rule_set(d.pop("ruleSet", None))

        return cls(
            schema_str=schema_str,
            schema_type=schema_type,
            references=references,
            metadata=metadata,
            rule_set=rule_set,
        )

    # def __eq__(self, other):
    #     if not isinstance(other, Schema):
    #         return False
    #     return self.to_dict() == other.to_dict()


@_attrs_define(frozen=True, cache_hash=True)
class RegisteredSchema:
    """
    An registered schema.
    """

    schema_id: Optional[int]
    schema: Optional[Schema]
    subject: Optional[str]
    version: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        schema = self.schema

        schema_id = self.schema_id

        subject = self.subject

        version = self.version

        field_dict: Dict[str, Any] = {}
        if schema is not None:
            field_dict = schema.to_dict()
        if schema_id is not None:
            field_dict["id"] = schema_id
        if subject is not None:
            field_dict["subject"] = subject
        if version is not None:
            field_dict["version"] = version

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        schema = Schema.from_dict(d)

        schema_id = d.pop("id", None)

        subject = d.pop("subject", None)

        version = d.pop("version", None)

        schema = cls(
            schema_id=schema_id,
            schema=schema,
            subject=subject,
            version=version,
        )

        return schema
