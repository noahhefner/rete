from typing import Protocol, Any, Callable
from dataclasses import dataclass
from abc import abstractmethod

type Rule = Callable[[Fact], bool]
type NetworkNode = BetaNode | TerminalNode
type JoinFunction = Callable[[Token, Fact], bool]

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
        self.children: list["BetaNode"] = []

    def connect(self, node: "BetaNode"):
        # NOTE: What if I want to connect an Alpha node directly to a Terminal node?
        self.children.append(node)

    def activate(self, fact: Fact):
        if self.func(fact):
            self.memory.append(fact)

            for child in self.children:
                child.right_activate(fact)


class BetaNode:
    def __init__(self, join_func: JoinFunction):
        self.children: list["NetworkNode"] = []
        self.left_memory: list[Token] = []
        self.right_memory: list[Fact] = []
        self.join_func = join_func

    def connect(self, node: "NetworkNode"):
        self.children.append(node)

    def left_activate(self, token: Token):
        self.left_memory.append(token)

        for fact in self.right_memory:
            if self.join_func(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.left_activate(new_token)

    def right_activate(self, fact: Fact):
        self.right_memory.append(fact)

        for token in self.left_memory:
            if self.join_func(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.left_activate(new_token)


class TerminalNode:

    def __init__ (self, name: str):

        self.name = name

    def activate(self, token: Token):

        print(f"Terminal node {self.name} activated! Token: {token}")


class ReteNetwork:
    def __init__(self):
        self.root = RootNode()

    def assert_fact(self, fact: Fact):
        self.root.activate(fact)


def person_account_join(token: Token, fact: Fact) -> bool:
    for f in token.facts:
        if f.fact_type == "Person":
            return f.fact_data["name"] == fact.fact_data["owner"]

    return False

def main():

    net = ReteNetwork()

    person_sel = SelectorNode("Person")
    account_sel = SelectorNode("Account")

    alpha_person = AlphaNode(lambda f: True)
    alpha_account = AlphaNode(lambda f: True)

    beta = BetaNode(person_account_join)

    terminal = TerminalNode("match")

    net.root.connect(person_sel)
    net.root.connect(account_sel)

    person_sel.connect(alpha_person)
    account_sel.connect(alpha_account)

    alpha_person.connect(beta)
    alpha_account.connect(beta)

    beta.connect(terminal)

    beta.left_activate(Token(tuple()))  # bootstrap

    facts = [
        Fact("Person", {"name": "Alice", "age": 30}),
        Fact("Person", {"name": "Bob", "age": 17}),
        Fact("Person", {"name": "Charlie", "age": 40}),

        Fact("Account", {"owner": "Alice", "balance": 5000}),
        Fact("Account", {"owner": "Bob", "balance": 200}),
        Fact("Account", {"owner": "Diana", "balance": 9000}),
    ]

    for f in facts:
        net.assert_fact(f)


if __name__ == "__main__":

    main()