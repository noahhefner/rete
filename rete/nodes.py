from dataclasses import dataclass
from typing import Any

from cel import compile as cel_compile


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

    def connect(self, node: "SelectorNode") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        for child in self.children:
            child.activate(fact)


class SelectorNode:
    def __init__(self, fact_type: str):
        self.fact_type = fact_type
        self.children: list["AlphaNode"] = []

    def connect(self, node: "AlphaNode") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        if fact.fact_type == self.fact_type:
            for child in self.children:
                child.activate(fact)


class AlphaNode:
    def __init__(self, expression: str):
        self.program = cel_compile(expression)
        self.memory: list[Fact] = []
        self.children: list["DummyTopNode | BetaRightAdapter"] = []

    def connect(self, node: "DummyTopNode | BetaRightAdapter") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        if self._matches(fact):
            self.memory.append(fact)
            for child in self.children:
                child.activate(fact)

    def _matches(self, fact: Fact) -> bool:
        ctx = {fact.fact_type: fact.fact_data}
        needed = set(self.program.variables())
        if not needed.issubset(ctx.keys()):
            return False
        return self.program.execute(ctx)


class DummyTopNode:
    def __init__(self):
        self.children: list["BetaLeftAdapter"] = []

    def connect(self, node: "BetaLeftAdapter") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        if not self.children:
            raise RuntimeError("DummyTopNode has no children.")
        token = Token(facts=()).extend(fact)
        for child in self.children:
            child.activate(token)


class BetaNode:

    # TODO: This class should accept a list of join tests to run. The join tests
    # should be inferred in build_network()

    def __init__(self):
        self.left_memory: list[Token] = []
        self.right_memory: list[Fact] = []
        self.children: list["TerminalNode | BetaLeftAdapter"] = []

    def connect(self, node: "TerminalNode | BetaLeftAdapter") -> None:
        self.children.append(node)

    def left_activate(self, token: Token) -> None:
        """Join an incoming Token with Facts stored in right memory.
        
        Extend and propagate partial matches to child nodes.
        """

        self.left_memory.append(token)
        for fact in self.right_memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)

    def right_activate(self, fact: Fact) -> None:
        """Join an incoming Fact with Tokens stored in left memory.

        Extend and propagate partial matches to child nodes.
        """

        self.right_memory.append(fact)
        for token in self.left_memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)

    def _check_join(self, token: Token, fact: Fact) -> bool:
        """Perform a JOIN on a Token and a Fact.
        
        """


        ctx: dict[str, Any] = {}
        for f in (*token.facts, fact):
            ctx[f.fact_type] = f.fact_data

        needed = set(self.program.variables())
        
        if not needed.issubset(ctx.keys()):
            return False
        
        return self.program.execute(ctx)

    def _check_token(self, token: Token) -> bool:
        ctx: dict[str, Any] = {f.fact_type: f.fact_data for f in token.facts}
        needed = set(self.program.variables())
        if not needed.issubset(ctx.keys()):
            return False
        return self.program.execute(ctx)


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
    def __init__(self, rule_id: str, action_id: str):
        self.rule_id = rule_id
        self.action_id = action_id

    def activate(self, token: Token) -> None:
        print(f"Rule '{self.rule_id}' fired \u2192 action: {self.action_id} | Token: {token}")
