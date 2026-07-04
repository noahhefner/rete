from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


# -------------------------------------------------
# Base Node
# -------------------------------------------------

class Node(ABC):
    def __init__(self):
        self.children: list[Node] = []

    def connect(self, node: "Node") -> None:
        self.children.append(node)


# -------------------------------------------------
# Connectors
# -------------------------------------------------

class LeftConnector(Node):
    """Propagates tokens down the left side."""

    def activate(self, token: tuple):
        for child in self.children:
            child.left_activate(token)


class RightConnector(Node):
    """Propagates facts down the right side."""

    def activate(self, fact: Any):
        for child in self.children:
            child.right_activate(fact)


# -------------------------------------------------
# Alpha Node
# -------------------------------------------------

class AlphaNode(Node):

    def __init__(self, predicate: Callable[[Any], bool]):
        super().__init__()
        self.predicate = predicate
        self.memory: list[Any] = []

    def activate(self, fact: Any):

        if not self.predicate(fact):
            return

        self.memory.append(fact)

        for child in self.children:
            child.right_activate(fact)


# -------------------------------------------------
# Beta Memory
# -------------------------------------------------

class BetaMemory(Node):

    def __init__(self):
        super().__init__()
        self.memory: list[tuple] = []

    def left_activate(self, token: tuple):

        self.memory.append(token)

        for child in self.children:
            child.left_activate(token)


# -------------------------------------------------
# Join Node
# -------------------------------------------------

class JoinNode(Node):

    def __init__(self, test: Callable[[tuple, Any], bool]):
        super().__init__()

        self.test = test
        self.left_memory: list[tuple] = []
        self.right_memory: list[Any] = []

    def left_activate(self, token: tuple):

        self.left_memory.append(token)

        for fact in self.right_memory:

            if self.test(token, fact):

                new_token = token + (fact,)

                for child in self.children:
                    child.left_activate(new_token)

    def right_activate(self, fact: Any):

        self.right_memory.append(fact)

        for token in self.left_memory:

            if self.test(token, fact):

                new_token = token + (fact,)

                for child in self.children:
                    child.left_activate(new_token)


# -------------------------------------------------
# Production Node
# -------------------------------------------------

class ProductionNode(Node):

    def __init__(self, action: Callable[[tuple], None]):
        super().__init__()
        self.action = action

    def left_activate(self, token: tuple):
        self.action(token)


# -------------------------------------------------
# Root
# -------------------------------------------------

class RootNode(Node):

    def start(self):

        empty = ()

        for child in self.children:
            child.left_activate(empty)


# -------------------------------------------------
# Working Memory
# -------------------------------------------------

class WorkingMemory:

    def __init__(self):
        self.facts: list[Any] = []
        self.alpha_nodes: list[AlphaNode] = []

    def add_alpha(self, node: AlphaNode):
        self.alpha_nodes.append(node)

    def assert_fact(self, fact: Any):

        self.facts.append(fact)

        for alpha in self.alpha_nodes:
            alpha.activate(fact)


# -------------------------------------------------
# Top-Level Network
# -------------------------------------------------

class ReteNetwork:

    def __init__(self):

        self.root = RootNode()
        self.working_memory = WorkingMemory()

    def add_alpha(self, node: AlphaNode):

        self.working_memory.add_alpha(node)

    def add_rule(
        self,
        alpha: AlphaNode,
        join: JoinNode,
        production: ProductionNode,
    ):

        self.root.connect(join)
        alpha.connect(join)
        join.connect(production)

        self.add_alpha(alpha)

    def assert_fact(self, fact):

        self.working_memory.assert_fact(fact)

    def initialize(self):

        self.root.start()