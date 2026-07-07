import json
from cel import compile as cel_compile

from rete.nodes import (
    SelectorNode, AlphaNode, BetaNode,
    DummyTopNode, TerminalNode, BetaLeftAdapter, BetaRightAdapter,
)
from rete.network import ReteNetwork
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
    cels = [e["cel"] for e in rule["expression"]["all"]]
    seen: list[str] = []
    for cel_str in cels:
        for var in cel_compile(cel_str).variables():
            if var not in seen:
                seen.append(var)
    return seen


def build_network(rules: list[dict], actions: dict[str, dict],
                  schemas: SchemaValidator) -> ReteNetwork:
    net = ReteNetwork(schemas)

    for rule in rules:
        raw_cels = [e["cel"] for e in rule["expression"]["all"]]
        if not raw_cels:
            continue

        intra: dict[str, list[str]] = {}
        cross: list[str] = []

        for cel in raw_cels:
            prog = cel_compile(cel)
            unique = set(prog.variables())
            if len(unique) <= 1:
                ft = next(iter(unique), None)
                if ft is not None:
                    intra.setdefault(ft, []).append(cel)
            else:
                cross.append(cel)

        all_types = _first_seen_index(rule)

        alphas: dict[str, AlphaNode] = {}
        for ft in all_types:
            sel = SelectorNode(ft)
            alpha = AlphaNode(intra.get(ft))
            net.root.connect(sel)
            sel.connect(alpha)
            alphas[ft] = alpha

        if not all_types:
            continue

        if len(all_types) == 1:
            betas = [BetaNode(has_right_input=False)]
        else:
            betas = [BetaNode(has_right_input=True) for _ in range(len(all_types) - 1)]

        type_pos = {ft: i for i, ft in enumerate(all_types)}

        for cel in cross:
            prog = cel_compile(cel)
            unique = set(prog.variables())
            last_pos = max(type_pos[t] for t in unique)
            beta_idx = 0 if last_pos == 0 else last_pos - 1
            if betas[beta_idx].program is not None:
                raise ValueError(
                    f"BetaNode {beta_idx} already has a join CEL"
                )
            betas[beta_idx].set_join(cel)

        terminal = TerminalNode(rule["id"], rule["action"])
        betas[-1].connect(terminal)

        dummy = DummyTopNode()
        alphas[all_types[0]].connect(dummy)
        dummy.connect(BetaLeftAdapter(betas[0]))

        for i in range(len(betas) - 1):
            betas[i].connect(BetaLeftAdapter(betas[i + 1]))

        for ft in all_types[1:]:
            beta_idx = type_pos[ft] - 1
            alphas[ft].connect(BetaRightAdapter(betas[beta_idx]))

    return net
