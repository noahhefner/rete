import json

from jsonschema import validate

from rete.nodes import Fact


class SchemaValidator:
    def __init__(self, schemas_path: str):
        with open(schemas_path) as f:
            raw = json.load(f)
        self.schemas: dict[str, dict] = {}
        for ft_name, ref_obj in raw.get("properties", {}).items():
            ref_path = ref_obj.get("$ref", "")
            def_key = ref_path.split("/")[-1]
            schema = raw.get("$defs", {}).get(def_key)
            if schema is not None:
                self.schemas[ft_name] = schema

    def validate(self, fact: Fact) -> None:
        schema = self.schemas.get(fact.fact_type)
        if schema is None:
            raise ValueError(f"No schema defined for fact type: {fact.fact_type}")
        validate(instance=fact.fact_data, schema=schema)
