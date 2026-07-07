from rete.nodes import Fact, RootNode
from rete.validator import SchemaValidator


class ReteNetwork:
    def __init__(self, validator: SchemaValidator):
        self.root = RootNode()
        self.validator = validator

    def assert_fact(self, fact: Fact) -> None:
        self.validator.validate(fact)
        self.root.activate(fact)
