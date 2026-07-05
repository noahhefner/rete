from typing import Protocol, Any, Callable
from dataclasses import dataclass
from abc import abstractmethod

type Predicate = Callable[[Fact], bool]

@dataclass(frozen=True)
class Fact:

    token: str
    value: Any  # WARNING: May cause runtime errors if value is not hashable

class Node(Protocol):

    children: list[Node]

    def connect(self, node: Node):

        self.children.append(node)

    @abstractmethod
    def activate(self, facts: list[Fact]) -> None:
        raise NotImplementedError

class AlphaNode(Node):

    def __init__(self, predicate: Predicate):

        self.predicate = predicate
        self.memory: list[Fact] = []
        self.children: list[Node] = []

    def activate(self, facts: list[Fact]) -> None:

        if not self.predicate(facts[0]):
            return

        self.memory.append(facts[0])

        for child in self.children:
            child.activate(facts)

class BetaNode(Node):

    def __init__(self):

        self.children: list[Node] = []
        self.left_memory: list[Fact] = []
        self.right_memory: list[Fact] = []

    def activate(self, facts: list[Fact]) -> None:
        raise RuntimeError("Use left_activate or right_activate for Beta nodes.")

    def left_activate(self, facts: list[Fact]):

        # Add incoming facts to left memory
        self.left_memory = list(set(self.left_memory + facts))

        # Do not activate children if the right side has not
        # been activated yet
        if not self.right_memory:
            return

        # Propagate all facts to children
        all_facts = list(set(self.left_memory + self.right_memory))
        for child in self.children:
            child.activate(all_facts)

    def right_activate(self, facts: list[Fact]):

        # Add incoming facts to right memory
        self.right_memory = list(set(self.right_memory + facts))

        # Do not activate children if the left side has not
        # been activated yet
        if not self.left_memory:
            return

        # Propagate all facts to children
        all_facts = list(set(self.left_memory + self.right_memory))
        for child in self.children:
            child.activate(all_facts)

class BetaRightAdapter(Node):

    def connect(self, node: Node):

        if not isinstance(node, BetaNode):
            raise TypeError("BetaRightAdapter can only connect to a BetaNode")

        self.children = [node]

    def activate(self, facts: list[Fact]) -> None:

        if not self.children:
            raise RuntimeError("BetaRightAdapter not connected.")

        if not isinstance(self.children[0], BetaNode):
            raise RuntimeError("BetaLeftAdapter connected to wrong Node type.")

        self.children[0].right_activate(facts)

class BetaLeftAdapter(Node):

    def connect(self, node: Node):

        if not isinstance(node, BetaNode):
            raise TypeError("BetaLeftAdapter can only connect to a BetaNode")

        self.children = [node]

    def activate(self, facts: list[Fact]) -> None:

        if not self.children:
            raise RuntimeError("BetaLeftAdapter not connected.")

        if not isinstance(self.children[0], BetaNode):
            raise RuntimeError("BetaLeftAdapter connected to wrong Node type.")

        self.children[0].left_activate(facts)

class TerminalNode(Node):

    def __init__ (self, name: str):

        self.name = name

    def activate(self, facts: list[Fact]):

        print(f"Terminal node {self.name} activated! Facts: {facts}")

class ReteNetwork:

    def __init__(self, network: list[AlphaNode]):

        self.root_nodes: list[AlphaNode] = network

    def assert_fact(self, fact: Fact) -> None:

        for node in self.root_nodes:

            node.activate([fact])

def main():

    # ------------------------
    # Setup Alpha Nodes
    # ------------------------

    def age_check(fact: Fact) -> bool:

        if not fact.token == "age":
            return False

        if not isinstance(fact.value, int):
            return False

        return fact.value >= 18

    def country_check(fact: Fact) -> bool:

        if not fact.token == "country":
            return False

        if not isinstance(fact.value, str):
            return False

        return fact.value == "USA"

    def job_check(fact: Fact) -> bool:

        if not fact.token == "job":
            return False

        if not isinstance(fact.value, str):
            return False

        return fact.value == "engineer"

    alpha_age_check = AlphaNode(age_check)
    alpha_job_check = AlphaNode(job_check)
    alpha_country_check = AlphaNode(country_check)

    # ------------------------
    # Setup Beta Nodes
    # ------------------------

    beta_adult_engineer = BetaNode()
    beta_adult_engineer_left_adapter = BetaLeftAdapter()
    beta_adult_engineer_right_adapter = BetaRightAdapter()
    beta_adult_engineer_left_adapter.connect(beta_adult_engineer)
    beta_adult_engineer_right_adapter.connect(beta_adult_engineer)

    alpha_age_check.connect(beta_adult_engineer_left_adapter)
    alpha_job_check.connect(beta_adult_engineer_right_adapter)

    all_three = BetaNode()
    all_three_left_adapter = BetaLeftAdapter()
    all_three_right_adapter = BetaRightAdapter()
    all_three_left_adapter.connect(all_three)
    all_three_right_adapter.connect(all_three)

    beta_adult_engineer.connect(all_three_left_adapter)
    alpha_country_check.connect(all_three_right_adapter)
    
    # ------------------------
    # Setup Terminal Nodes
    # ------------------------

    terminal_adult_engineer = TerminalNode("Adult Engineer")
    beta_adult_engineer.connect(terminal_adult_engineer)

    terminal_all_three = TerminalNode("All Three")
    all_three.connect(terminal_all_three)

    # ------------------------
    # Setup Rete Network
    # ------------------------

    network = ReteNetwork([
        alpha_age_check,
        alpha_job_check,
        alpha_country_check
    ])

    # ------------------------
    # Send in Facts
    # ------------------------

    fact_one = Fact("age", 26)
    fact_two = Fact("country", "USA")
    fact_three = Fact("job", "engineer")

    network.assert_fact(fact_one)
    network.assert_fact(fact_two)
    network.assert_fact(fact_three)

if __name__ == "__main__":

    main()