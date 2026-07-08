import json
import sys

from cel import compile as cel_compile

from rete.network import ReteNetwork
from rete.nodes import (
    AlphaNode, 
    BetaLeftAdapter, 
    BetaNode, 
    BetaRightAdapter,
    DummyTopNode, 
    SelectorNode, 
    TerminalNode,
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

def _create_beta_lookup_key(cels: list[str]) -> str:
    """Create a key for Beta node lookup table using a list of CEL's as input."""
    copy = list(cels)
    copy.sort()
    return " ".join(copy)

def build_network(
    rules: list[dict], 
    actions: dict[str, dict],
    schema_validator: SchemaValidator,
) -> ReteNetwork:
    
    net = ReteNetwork(schema_validator)
    
    # Create a set of all unique CEL's and fact types across all rules
    unique_cels: list[str] = []
    unique_fact_types: list[str] = []
    for rule in rules:
        cels = rule["expression"]["all"]
        unique_cels = list(set(unique_cels + cels))
        for cel in cels:
            variables = cel_compile(cel).variables()
            unique_fact_types = list(set(unique_fact_types + variables))

    # Create Selector nodes for all fact types
    for fact_type in unique_fact_types:
        selector_node = SelectorNode(fact_type)
        net.root.connect(selector_node)

    # Create an Alpha node for each unique CEL
    alpha_lookup_table: dict[str, AlphaNode] = {}
    for cel in unique_cels:
        alpha_node = AlphaNode(cel)
        alpha_lookup_table[cel] = alpha_node

    # Create Beta and Dummy nodes
    beta_lookup_table: dict[str, BetaNode] = {}
    previous_beta: BetaNode | None = None
    for rule in rules:
        expression = rule["expression"]["all"]

        for cel_index in range(len(expression) - 1):

            left_activation_cels = expression[0:cel_index + 1]
            right_activation_cel = expression[cel_index + 1]

            beta_key = _create_beta_lookup_key(
                list(set(left_activation_cels + right_activation_cel))
            )

            beta_node = beta_lookup_table[beta_key]
            
            # If there's already a Beta node that joins these CEL's, continue to 
            # next loop iteration
            if beta_node is not None:
                previous_beta = beta_node
                continue
            
            # Create a Beta node and add it to the lookup table
            beta_node = BetaNode()
            beta_lookup_table[beta_key] = beta_node

            # Lookup the right activation Alpha node and link it to the Beta node
            # via BetaRightAdapter
            alpha_node = alpha_lookup_table[right_activation_cel]
            if alpha_node is None:
                raise RuntimeError(f"Failed to locate alpha node in lookup table for CEL: {right_activation_cel}")
                sys.exit(1)
            beta_right_adapter = BetaRightAdapter(beta_node)
            alpha_node.connect(beta_right_adapter)
            beta_right_adapter.connect(beta_node)

            # Connect output of previous Beta node to left side of this Beta node
            beta_left_adapter = BetaLeftAdapter(beta_node)
            if previous_beta is not None:
                # Connect output of previous Beta to this Beta
                previous_beta.connect(beta_left_adapter)
            else:
                # Left side is a single CEL (single Alpha node). Create Dummy node and 
                # connect it to left side of this Beta node.
                dummy_node = DummyTopNode()
                alpha_node = alpha_lookup_table[left_activation_cels[0]]
                if alpha_node is None:
                    raise RuntimeError(f"Failed to locate alpha node in lookup table for CEL: {left_activation_cels[0]}")
                    sys.exit(1)
                alpha_node.connect(dummy_node)
                dummy_node.connect(beta_left_adapter)

            # Create Terminal node and connect it to the last Beta node in the chain
            if cel_index == len(expression) - 1:
                terminal_node = TerminalNode(rule["id"], rule["action"])
                beta_node.connect(terminal_node)

            previous_beta = beta_node

    return net
