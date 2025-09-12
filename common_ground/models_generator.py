from dataclasses import field, make_dataclass
from typing import Any, Dict, List, Tuple, Type
import re

import d42
from niltype import Nil
from d42.declaration.types import (
    DictSchema,
    ListSchema,
    StrSchema,
    IntSchema,
    FloatSchema,
    BoolSchema,
    NoneSchema,
    AnySchema,
    BytesSchema,
)
from common_ground.common.base import BaseSchemaModel


pascal_pattern = r"[^0-9a-zA-Z_]"


def _is_dict_schema(sch: Any) -> bool:
    return isinstance(sch, DictSchema)


def _is_list_schema(sch: Any) -> bool:
    return isinstance(sch, ListSchema)


def _primitive_py_type(sch: Any) -> Type[Any]:
    if isinstance(sch, StrSchema):
        return str
    if isinstance(sch, IntSchema):
        return int
    if isinstance(sch, FloatSchema):
        return float
    if isinstance(sch, BoolSchema):
        return bool
    if isinstance(sch, BytesSchema):
        return bytes
    if isinstance(sch, NoneSchema):
        return type(None)
    if isinstance(sch, AnySchema):
        return Any
    return Any


def _extract_dict_props(dict_schema: DictSchema) -> Dict[str, Tuple[Any, bool]]:
    try:
        keys = dict_schema.props.keys
    except Exception:
        return {}
    if keys is Nil or not isinstance(keys, dict):
        return {}
    return keys  # type: ignore[return-value]


def _safe_identifier(name: str, default: str = 'field') -> str:
    if name is None:
        return default
    ident = re.sub(pascal_pattern, "_", str(name))
    if not ident:
        ident = default
    if ident[0].isdigit():
        ident = "_" + ident
    return ident


def _safe_class_name(name: str, default: str = 'Generated') -> str:
    if name is None:
        return default
    s = re.sub(pascal_pattern, "_", str(name))
    parts = [p for p in s.split("_") if p]
    if not parts:
        return default
    parts = [p.capitalize() for p in parts]
    cname = "".join(parts)
    if cname and cname[0].isdigit():
        cname = "C" + cname
    return cname


def generate_schema_builders_from_map(schema_map: Dict[str, Any]) -> Dict[str, Type[BaseSchemaModel]]:
    """
    Accepts a map class_name -> d42_schema and generates corresponding builder classes.
    Returns dict class_name -> class.

    Changed: nested DictSchema objects are now created as separate classes and
    added into the parent's namespace (as nested attributes) to support
    deeply nested schema structures.
    """
    generated: Dict[str, Type[BaseSchemaModel]] = {}

    def gen_for_schema(name: str, schema: Any) -> Type[BaseSchemaModel]:
        if name in generated:
            return generated[name]

        # Collect nested classes that should be placed into the parent's namespace
        nested_namespace: Dict[str, Type[BaseSchemaModel]] = {}

        if not _is_dict_schema(schema):
            cls = type(name, (BaseSchemaModel,), {"schema": schema})
            generated[name] = cls
            return cls

        fields: List[Tuple[str, Any, Any]] = []
        props = _extract_dict_props(schema)

        orig_map: Dict[str, str] = {}
        used_names: Dict[str, int] = {}

        for key, (prop_schema, required_flag) in props.items():
            orig_field_name = str(key)
            safe_field = _safe_identifier(orig_field_name)

            if safe_field in used_names:
                used_names[safe_field] += 1
                safe_field = f"{safe_field}_{used_names[safe_field]}"
            else:
                used_names[safe_field] = 0

            if _is_dict_schema(prop_schema):
                nested_name = f"{name}{_safe_class_name(orig_field_name)}"
                # generate nested class
                nested_cls = gen_for_schema(nested_name, prop_schema)
                # store it in the parent's namespace so it becomes a nested attribute
                nested_namespace[nested_name] = nested_cls
                anno = nested_cls
            elif _is_list_schema(prop_schema):
                elem_type = Any
                try:
                    elem_info = prop_schema.props.type
                    if elem_info is not Nil and elem_info is not None:
                        if _is_dict_schema(elem_info):
                            nested_name = f"{name}{_safe_class_name(orig_field_name)}Item"
                            nested_cls = gen_for_schema(nested_name, elem_info)
                            nested_namespace[nested_name] = nested_cls
                            elem_type = List[nested_cls]  # type: ignore[name-defined]
                        else:
                            elem_type = List[_primitive_py_type(elem_info)]  # type: ignore[index]
                    else:
                        elem_type = List[Any]
                except Exception:
                    elem_type = List[Any]
                anno = elem_type
            else:
                anno = _primitive_py_type(prop_schema)

            fields.append((safe_field, anno, field(default=None, metadata={"orig_name": orig_field_name})))
            orig_map[safe_field] = orig_field_name

        def fake(self, **kwargs: Any) -> Any:
            values = self._collect_values()
            orig_map_local = getattr(self, "__orig_field_map__", None)
            if orig_map_local:
                mapped: Dict[str, Any] = {}
                for k, v in values.items():
                    orig_k = orig_map_local.get(k, k)
                    mapped[orig_k] = v
                values = mapped

            options = dict(kwargs)

            substitute = getattr(d42, "substitute", None)
            if values and callable(substitute):
                try:
                    substituted = substitute(self.schema, values)
                except Exception:
                    substituted = None

                if substituted is not None:
                    return d42.fake(substituted, **options)

            if values:
                try:
                    return d42.fake(self.schema, values=values, **options)
                except Exception as exc:
                    raise RuntimeError(f"Failed to fake schema with values parameter: {exc}") from exc
            try:
                return d42.fake(self.schema, **options)
            except Exception as exc:
                raise RuntimeError(f"Failed to call fake function: {exc}") from exc

        try:
            fake.__isabstractmethod__ = False  # type: ignore[attr-defined]
        except Exception as exc:
            raise RuntimeError("Failed to set __isabstractmethod__ attribute on fake function") from exc

        # Prepare namespace: schema, orig_map, fake and nested classes
        namespace: Dict[str, Any] = {"schema": schema, "__orig_field_map__": orig_map, "fake": fake}
        # add nested classes to namespace (they will become parent's attributes)
        namespace.update(nested_namespace)

        cls = make_dataclass(
            cls_name=name,
            fields=fields,
            bases=(BaseSchemaModel,),
            namespace=namespace,
            frozen=False
        )

        if getattr(cls, "__abstractmethods__", None):
            cls.__abstractmethods__ = set()

        # Save the generated class globally
        generated[name] = cls
        return cls

    # Iterate over the provided map and generate classes.
    # Ensure deterministic order (insertion order of dict is preserved).
    for cname, sch in schema_map.items():
        if sch is None:
            continue
        gen_for_schema(cname, sch)

    return generated
