from typing import Protocol, Any, Callable
from dataclasses import dataclass

type Predicate = Callable[[Fact], bool]

@dataclass(frozen=True)
class Fact:

    token: str
    value: Any  # WARNING: May cause runtime errors if value is not hashable

class Node(Protocol):
    
    children: list[Node]

    def connect(self, node: Node) -> None:

        self.children.append(node)

class AlphaNode(Node):

    def __init__(self, predicate: Predicate):

        self.token = token
        self.predicate = predicate
        self.memory: list[Fact] = []

    def activate(self, fact: Fact):

        if not self.predicate(fact):
            return

        self.memory.append(fact)

        for child in children:
            child.activate(fact)

class BetaNode(Node):

    def __init__(self):

        self.left_memory: list[Fact] = []
        self.right_memory: list[Fact] = []

    def left_activate(self, facts: list[Fact]):

        # Add incoming facts to left memory
        self.left_memory = list(set(self.left_memory + facts))

        if not self.right_memory:
            return

        # Join all facts
        all_facts = list(set(self.left_memory + self.right_memory))

        # Propagate facts to children
        for child in children:

            child.activate



    def right_activate(self, fact: Fact):




"""
Example alphas:

age >= 18
country == "US"
favorite_color != pink




"""