from typing import Any, Callable
from dataclasses import dataclass

type Rule = Callable[[Fact], bool]
type JoinFunction = Callable[[Token, Fact], bool]
type BetaChildren = BetaLeftAdapter | TerminalNode
type DummyChildren = BetaLeftAdapter | TerminalNode
type AlphaChildren = DummyTopNode | BetaRightAdapter

@dataclass(frozen=True)
class Fact:
    fact_type: str
    fact_data: Any


@dataclass(frozen=True)
class Token:
    facts: tuple[Fact, ...]

    def extend(self, fact: Fact) -> "Token":
        return Token(self.facts + (fact,))


class RootNode:
    def __init__(self):
        self.children: list["SelectorNode"] = []

    def connect(self, node: "SelectorNode"):
        self.children.append(node)

    def activate(self, fact: Fact):
        for child in self.children:
            child.activate(fact)


class SelectorNode:
    def __init__(self, fact_type: str):
        self.fact_type = fact_type
        self.children: list["AlphaNode"] = []

    def connect(self, node: "AlphaNode"):
        self.children.append(node)

    def activate(self, fact: Fact):
        if fact.fact_type == self.fact_type:
            for child in self.children:
                child.activate(fact)


class AlphaNode:
    def __init__(self, func: Rule):
        self.func = func
        self.memory: list[Fact] = []
        self.children: list["AlphaChildren"] = []

    def connect(self, node: "AlphaChildren"):
        self.children.append(node)

    def activate(self, fact: Fact):

        if self.func(fact):
            self.memory.append(fact)
            for child in self.children:
                child.activate(fact)


class DummyTopNode:
    """Specialized Node for connecting an Alpha node directly to a Beta node."""
        
    def connect(self, node: DummyChildren) -> None:

        self.child = node

    def activate(self, fact: Fact):
        """Convert fact to token and propagate to Beta node via left activation."""

        if not self.child:
            raise RuntimeError("Dummy top node not connected.")

        token = Token(facts=())
        token = token.extend(fact)
        self.child.activate(token)


class BetaNode:
    def __init__(self, join_func: JoinFunction):
        self.children: list["BetaChildren"] = []
        self.left_memory: list[Token] = []
        self.right_memory: list[Fact] = []
        self.join_func: JoinFunction = join_func

    def connect(self, node: "BetaChildren") -> None:
        self.children.append(node)

    def left_activate(self, token: Token) -> None:
        self.left_memory.append(token)
        for fact in self.right_memory:
            if self.join_func(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)

    def right_activate(self, fact: Fact) -> None:
        self.right_memory.append(fact)
        for token in self.left_memory:
            if self.join_func(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)


class BetaRightAdapter:
    def __init__(self, beta: BetaNode):
        self.beta = beta

    def activate(self, fact: Fact) -> None:
        self.beta.right_activate(fact)


class BetaLeftAdapter:
    def __init__(self, beta: BetaNode):
        self.beta = beta

    def activate(self, token: Token) -> None:
        self.beta.left_activate(token)


class TerminalNode:
    def __init__(self, name: str):
        self.name = name

    def activate(self, token: Token) -> None:
        print(f"Terminal node {self.name} activated! Token: {token}")


class ReteNetwork:
    def __init__(self):
        self.root = RootNode()

    def assert_fact(self, fact: Fact) -> None:
        self.root.activate(fact)


def person_account_join(token: Token, fact: Fact) -> bool:
    for f in token.facts:
        if f.fact_type == "Person":
            return f.fact_data["name"] == fact.fact_data["owner"]

    return False


def dummy_beta_function(token: Token, fact: Fact) -> bool:
    return True


def is_it_jerry(fact: Fact) -> bool:

    return fact.fact_data["name"] == "Jerry"


def main():

    # Create network
    net = ReteNetwork()

    # Create selector nodes
    person_sel = SelectorNode("Person")
    account_sel = SelectorNode("Account")

    # Create alpha nodes
    alpha_person = AlphaNode(lambda f: True)
    alpha_person_is_jerry = AlphaNode(is_it_jerry)
    alpha_account = AlphaNode(lambda f: True)

    # Create beta nodes
    beta_node = BetaNode(person_account_join)

    # Create terminal nodes
    terminal = TerminalNode("match")
    terminal_jerry = TerminalNode("YO WE GOT JERRY IN DA HOUSE!!!")

    # Create dummy nodes
    dummy_jerry = DummyTopNode()
    dummy_person = DummyTopNode()

    # Create adapter nodes
    beta_left_adapter = BetaLeftAdapter(beta_node)
    beta_right_adapter = BetaRightAdapter(beta_node)

    # Connect selector nodes to root node
    net.root.connect(person_sel)
    net.root.connect(account_sel)

    # Connect alpha nodes to selector nodes
    person_sel.connect(alpha_person)
    person_sel.connect(alpha_person_is_jerry)
    account_sel.connect(alpha_account)

    # Connect dummy nodes to alpha nodes
    alpha_person_is_jerry.connect(dummy_jerry)
    alpha_person.connect(dummy_person)

    # Connect dummy nodes
    dummy_jerry.connect(terminal_jerry)
    dummy_person.connect(beta_left_adapter)

    # Connect alpha nodes to adapter nodes
    alpha_account.connect(beta_right_adapter)

    # Connect beta nodes to terminal nodes
    beta_node.connect(terminal)

    facts = [
        Fact("Person", {"name": "Alice", "age": 30}),
        Fact("Person", {"name": "Bob", "age": 17}),
        Fact("Person", {"name": "Charlie", "age": 40}),
        Fact("Person", {"name": "Jerry", "age": 37}),
        Fact("Account", {"owner": "Alice", "balance": 5000}),
        Fact("Account", {"owner": "Bob", "balance": 200}),
        Fact("Account", {"owner": "Diana", "balance": 9000}),
    ]

    for f in facts:
        net.assert_fact(f)


if __name__ == "__main__":
    main()
