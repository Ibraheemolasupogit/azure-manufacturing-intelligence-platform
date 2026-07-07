# Inventory Policy Assumptions

Milestone 5 distinguishes rules-based inventory policy from solver-heavy mathematical optimisation.

Rules-based calculations include:

- projected coverage days from available quantity and demand;
- recommended safety stock from service level, lead time, and deterministic demand uncertainty;
- recommended reorder point from lead-time demand plus safety stock;
- recommended reorder quantity from reorder gap, review period, minimum order quantity, order multiple, and maximum order quantity;
- stockout-risk score from upper-bound lead-time demand, safety stock, current availability, and supplier risk;
- excess-stock, expiry-risk, working-capital, holding-cost, and stockout-cost indicators.

Scenario comparison is deterministic. The constrained working-capital scenario allocates recommended reorder value by descending priority score until the configured capital limit is exhausted. It is a local priority-allocation policy, not an external optimisation solver.
