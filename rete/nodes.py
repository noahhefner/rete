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
    """Starting node where all Facts enter.

    When the Root node is activated by a Fact, the Fact is propagated to all
    child nodes (Type nodes).
    """

    def __init__(self):
        self.children: list["TypeNode"] = []

    def connect(self, node: "TypeNode") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        for child in self.children:
            child.activate(fact)


class TypeNode:
    def __init__(self, fact_type: str):
        self.fact_type = fact_type
        self.children: list["SelectNode"] = []

    def connect(self, node: "SelectNode") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        if fact.fact_type == self.fact_type:
            for child in self.children:
                child.activate(fact)


class SelectNode:
    def __init__(self, expressions: list[str] | None = None):
        self.programs = [cel_compile(e) for e in (expressions or [])]
        self.memory_node: "AlphaMemoryNode" | None = None

    def connect(self, node: "AlphaMemoryNode") -> None:
        self.memory_node = node

    def activate(self, fact: Fact) -> None:
        if not self.memory_node:
            raise RuntimeError("SelectNode activated but not connected.")

        if self._matches(fact):
            self.memory_node.activate(fact)

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


class AlphaMemoryNode:
    def __init__(self):
        self.memory: list[Fact] = []
        self.children: list["JoinRightAdapterNode" | "TerminalAdapterNode"] = []

    def connect(self, node: "JoinRightAdapterNode" | "TerminalAdapterNode") -> None:
        self.children.append(node)

    def activate(self, fact: Fact) -> None:
        self.memory.append(fact)
        for child in self.children:
            child.activate(fact)


class BetaMemoryNode:
    def __init__(self):
        self.memory: list[Token] = []
        self.join_node: "JoinNode" | None = None

    def connect(self, node: "JoinNode") -> None:
        self.join_node = node

    def activate(self, token: Token) -> None:
        if not self.join_node:
            raise RuntimeError("BetaMemoryNode activated but not connected.")

        self.memory.append(token)
        self.join_node.left_activate(token)


class JoinRightAdapterNode:
    def __init__(self):
        self.join_node: "JoinNode" | None = None

    def connect(self, join_node: "JoinNode") -> None:
        self.join_node = join_node

    def activate(self, fact: Fact):
        if self.join_node is None:
            raise RuntimeError("JoinRightAdapterNode activated but not connected.")
        self.join_node.right_activate(fact)


class JoinNode:
    def __init__(
        self,
        join_expression: str,
        left_memory: "BetaMemoryNode",
        right_memory: "AlphaMemoryNode",
    ):
        self.program = cel_compile(join_expression)
        self.output_node: "BetaMemoryNode" | "TerminalNode" | None = None

        self.left_memory: "BetaMemoryNode" = left_memory
        self.right_memory: "AlphaMemoryNode" = right_memory

    def connect(self, node: "BetaMemoryNode" | "TerminalNode") -> None:
        self.output_node = node

    def left_activate(self, token: Token) -> None:
        if self.output_node is None:
            raise RuntimeError("JoinNode left activated but not connected.")

        for fact in self.right_memory.memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                self.output_node.activate(new_token)

    def right_activate(self, fact: Fact) -> None:
        if self.output_node is None:
            raise RuntimeError("JoinNode right activated but not connected.")

        for token in self.left_memory.memory:
            if self._check_join(token, fact):
                new_token = token.extend(fact)
                self.output_node.activate(new_token)

    def _check_join(self, token: Token, fact: Fact) -> bool:
        ctx: dict[str, Any] = {}
        for f in (*token.facts, fact):
            ctx[f.fact_type] = f.fact_data
        needed = set(self.program.variables())
        if not needed.issubset(ctx.keys()):
            return False
        return self.program.execute(ctx)


class TerminalAdapterNode:
    def __init__(self):
        self.terminal_node: "TerminalNode" | None = None

    def connect(self, terminal_node: "TerminalNode") -> None:
        self.terminal_node = terminal_node

    def activate(self, fact: Fact):
        if not self.terminal_node:
            raise RuntimeError("TerminalAdapterNode activated but not connected.")
        token = Token(facts=(fact,))
        self.terminal_node.activate(token)


class TerminalNode:
    def __init__(self, rule_id: str, action_id: str):
        self.rule_id = rule_id
        self.action_id = action_id

    def activate(self, token: Token) -> None:
        print(
            f"Rule '{self.rule_id}' fired \u2192 action: {self.action_id} | Token: {token}"
        )
