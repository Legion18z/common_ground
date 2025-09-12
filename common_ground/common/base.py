from typing import Any, Dict
import d42


class BaseSchemaModel:
    """
    Base class for all generated builder classes.
    Child classes should have a class attribute `schema` (a d42 schema).
    Instances may have attributes corresponding to schema fields.
    """

    schema: Any = None

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def fake(self, **kwargs: Any) -> Any:
        """
        Standard implementation: collects values via _collect_values()
        and calls d42.fake, taking into account possible substitute.
        """
        values = self._collect_values()
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
                raise RuntimeError("Failed to fake schema with values parameter") from exc
        return d42.fake(self.schema, **options)

    def _collect_values(self) -> Dict[str, Any]:
        def convert(value: Any):
            if isinstance(value, BaseSchemaModel):
                return value._collect_values()
            if isinstance(value, (list, tuple)):
                return [convert(v) for v in value if v is not None]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items() if v is not None}
            return value

        result: Dict[str, Any] = {}
        for name, val in vars(self).items():
            if name.startswith("_"):
                continue
            if val is None:
                continue
            result[name] = convert(val)
        return result
