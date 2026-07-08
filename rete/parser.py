import json

from cel import compile as cel_compile

from rete.network import ReteNetwork
from rete.nodes import (
    AlphaMemoryNode,
    BetaMemoryNode,
    JoinNode,
    JoinRightAdapterNode,
    SelectNode,
    TerminalAdapterNode,
    TerminalNode,
    Token,
    TypeNode,
)
from rete.validator import SchemaValidator


def load_rules(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def load_actions(path: str) -> dict[str, dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {data["id"]: data}
    return {entry["id"]: entry for entry in data}


def load_schemas(path: str) -> SchemaValidator:
    return SchemaValidator(path)


def load_facts(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def _first_seen_index(rule: dict) -> list[str]:
    """Given a rule, return a list of all unique variables across all CEL's."""

    cels = [e["cel"] for e in rule["expression"]["all"]]
    seen: list[str] = []
    for cel_str in cels:
        for var in cel_compile(cel_str).variables():
            if var not in seen:
                seen.append(var)
    return seen


def build_network(
    rules: list[dict],
    actions: dict[str, dict],
    schema_validator: SchemaValidator,
) -> ReteNetwork:
    """Construct a Rete network from rule definitions.

    Each rule in rules has an id, an expression.all list of CEL conditions,
    and an action string that keys into actions.

    The Rete network has two subsystems:

    Alpha network (data-driven fact filtering)
        Shared across rules. For each fact type encountered (e.g. beneficiary,
        doctor, claim):

        RootNode -> TypeNode -> SelectNode -> AlphaMemoryNode

        TypeNode filters facts by their fact_type field.  SelectNode applies
        single-variable CEL conditions (e.g. beneficiary.age >= 65).
        Multiple rules with the same (type, conditions) pair share one alpha
        chain.  AlphaMemoryNode stores every fact that passes the select.

    Beta network (join tree, built per rule)
        Combines facts from multiple alpha memories into tuples (Tokens) that
        satisfy cross-variable conditions:

        DummyBeta(seed) -> JoinNode -> BetaMemoryNode -> ... -> TerminalNode

        DummyBeta is seeded with Token(()) so every fact entering the first
        join right away produces a single-fact token.  Each JoinNode reads
        its left memory (beta) and right memory (alpha) and evaluates a CEL
        join expression -- any condition that involves variables from both
        sides.  Matching pairs produce an extended token sent to the next
        beta memory or directly to the terminal.

    CEL partitioning (per-rule, left-to-right over ordered variables)

        Variables are ordered by first appearance in the rule's CEL list
        (_first_seen_index).  As each new variable var_i is processed:

        - Ready CELs = those whose variable set is a subset of
          {var_0, ..., var_i} and includes var_i.
        - If a ready CEL references only var_i -> SelectNode.
        - If it references var_i plus earlier variables -> JoinNode expression
          for this step.
        - CELs involving as-yet-unseen variables are deferred to later steps.
    """

    net = ReteNetwork(schema_validator)

    type_cache: dict[str, TypeNode] = {}
    alpha_cache: dict[tuple[str, frozenset[str]], AlphaMemoryNode] = {}

    def get_or_create_type(fact_type: str) -> TypeNode:
        if fact_type not in type_cache:
            node = TypeNode(fact_type)
            net.root.connect(node)
            type_cache[fact_type] = node
        return type_cache[fact_type]

    def get_or_create_alpha(type_node: TypeNode, cels: list[str]) -> AlphaMemoryNode:
        key = (type_node.fact_type, frozenset(cels))
        if key not in alpha_cache:
            select = SelectNode(cels)
            alpha = AlphaMemoryNode()
            select.connect(alpha)
            type_node.connect(select)
            alpha_cache[key] = alpha
        return alpha_cache[key]

    for rule in rules:
        rule_id = rule["id"]
        action_id = rule["action"]
        cels = [e["cel"] for e in rule["expression"]["all"]]
        variables = _first_seen_index(rule)

        if len(variables) == 1:
            var = variables[0]
            select_cels = []
            for cel_str in cels:
                cel_vars = set(cel_compile(cel_str).variables())
                if cel_vars == {var}:
                    select_cels.append(cel_str)

            type_node = get_or_create_type(var)
            alpha_mem = get_or_create_alpha(type_node, select_cels)

            adapter = TerminalAdapterNode()
            adapter.connect(TerminalNode(rule_id, action_id))
            alpha_mem.connect(adapter)

        else:
            seen: set[str] = set()
            prev_beta: BetaMemoryNode | None = None

            for i, var in enumerate(variables):
                seen.add(var)

                select_cels: list[str] = []
                join_cels: list[str] = []
                for cel_str in cels:
                    cel_vars = set(cel_compile(cel_str).variables())
                    if cel_vars.issubset(seen) and var in cel_vars:
                        if cel_vars == {var}:
                            select_cels.append(cel_str)
                        else:
                            join_cels.append(cel_str)

                type_node = get_or_create_type(var)
                alpha_mem = get_or_create_alpha(type_node, select_cels)

                if i == 0:
                    dummy_beta = BetaMemoryNode()
                    dummy_beta.memory.append(Token(facts=()))
                    prev_beta = dummy_beta

                join_expr = " && ".join(join_cels) if join_cels else "true"
                join = JoinNode(
                    join_expr, left_memory=prev_beta, right_memory=alpha_mem
                )
                prev_beta.connect(join)

                right_adapter = JoinRightAdapterNode()
                right_adapter.connect(join)
                alpha_mem.connect(right_adapter)

                if i == len(variables) - 1:
                    join.connect(TerminalNode(rule_id, action_id))
                else:
                    new_beta = BetaMemoryNode()
                    join.connect(new_beta)
                    prev_beta = new_beta

    return net
