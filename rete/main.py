import argparse

from rete.nodes import Fact
from rete.parser import (
    build_network, 
    load_actions, 
    load_facts, 
    load_rules,
    load_schemas,
)


def main():
    parser = argparse.ArgumentParser(description="Rete algorithm rule engine")
    parser.add_argument("--rules", default="data/rules.json", help="Path to rules file")
    parser.add_argument("--schemas", default="data/schemas.json", help="Path to schemas file")
    parser.add_argument("--actions", default="data/actions.json", help="Path to actions file")
    parser.add_argument("--facts", default="data/test-facts.json", help="Path to facts file")
    args = parser.parse_args()

    schema_validator = load_schemas(args.schemas)
    rules_data = load_rules(args.rules)
    actions_data = load_actions(args.actions)
    net = build_network(rules_data, actions_data, schema_validator)

    raw_facts = load_facts(args.facts)
    for raw in raw_facts:
        fact = Fact(raw["fact_type"], raw["fact_data"])
        try:
            net.assert_fact(fact)
        except Exception as e:
            print(f"Rejected fact ({raw['fact_type']}): {e}")


if __name__ == "__main__":
    main()
