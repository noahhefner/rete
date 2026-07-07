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
    def __init__(self, expressions: list[str] | None = None):
        self.programs = [cel_compile(e) for e in (expressions or [])]
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
        if not self.programs:
            return True
        ctx = {fact.fact_type: fact.fact_data}
        for prog in self.programs:
            needed = set(prog.variables())
            if not needed.issubset(ctx.keys()):
                return False
            if not prog.execute(ctx):
                return False
        return True


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
    def __init__(self, has_right_input: bool = False):
        self.program = None
        self.has_right_input = has_right_input
        self.left_memory: list[Token] = []
        self.right_memory: list[Fact] = []
        self.children: list["TerminalNode | BetaLeftAdapter"] = []

    def set_join(self, expression: str) -> None:
        self.program = cel_compile(expression)

    def connect(self, node: "TerminalNode | BetaLeftAdapter") -> None:
        self.children.append(node)

    def left_activate(self, token: Token) -> None:
        self.left_memory.append(token)
        for fact in self.right_memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)
        if not self.has_right_input:
            if self._check_token(token):
                for child in self.children:
                    child.activate(token)

    def right_activate(self, fact: Fact) -> None:
        self.right_memory.append(fact)
        for token in self.left_memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                for child in self.children:
                    child.activate(new_token)

    def _check_join(self, token: Token, fact: Fact) -> bool:
        if self.program is None:
            return True
        ctx: dict[str, Any] = {}
        for f in (*token.facts, fact):
            ctx[f.fact_type] = f.fact_data
        needed = set(self.program.variables())
        if not needed.issubset(ctx.keys()):
            return False
        return self.program.execute(ctx)

    def _check_token(self, token: Token) -> bool:
        if self.program is None:
            return True
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
