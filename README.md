# Rete Algorithm Python Implementation

To Implement:

- [ ] Root Node: Entrypoint for all facts into the algorithm
- [ ] Type / Select Nodes: Only parent is root node. All children are alpha nodes corresponding to a single predicate for that variable. For example, one type node for age, one type node for birthday, one type node for income, etc. Not strictly by data type (integer, date, currency), but by variable.
- [ ] Alpha Memory: Each alpha node should parent a single alpha memory node.

Notes:

- need to rework base node / protocol thing. activation function signatures are different for each node type, so a base class / protocol is problematic.