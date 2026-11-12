# v0.1 technical architecture

The engine is single-threaded and synchronous at period granularity. The internal state is a mutable `State` object with NumPy arrays for agent-household membership, participation, heterogeneous sector skills, cash balances, inventory, employment, prices, resource stock, and cumulative goods/resource quantities. `Simulation` consumes a fully validated `Scenario` dataclass. A local `numpy.random.Generator(PCG64)` provides all stochastic draws; the complete generator state is serialized along with state arrays.

Canonical execution order at each abstract period `t`:

1. Regenerate shared physical resource using its logistic rule.
2. Calculate automation intensity from the configured shock schedule.
3. Rotate the firm hiring priority; identify unemployed participants; each firm targets inventory based on fixed baseline household demand, recent sales and recent unfilled stock demand. Hire the most productive currently available participants for that sector subject to the wage budget, paying wages from firms to households.
4. Compute potential production using hired productivity. When requested physical input exceeds the remaining resource, make a proportional initial allocation and distribute feasible residual units in rotating firm order. Increase inventories and consume physical input.
5. Charge taxes from households on current wage receipts.
6. Spend the configured share of current tax receipts equally among the bottom households by current wage income (ties by stable ID).
7. Draw each sector's household demand and preferred-firm decisions; shuffle purchasing order. Purchase affordable stocked bundles with cash transfer to seller and one inventory unit removed. Count distinct stock and budget unmet demand. Lower priced firms are preferred probabilistically.
8. Distribute a fraction of positive current operating surplus (sales less wages) to the registered owners of each firm.
9. Update posted prices from stock-out/surplus rules.
10. Check monetary, physical resource, and finished-goods stock identities. Return recorded metrics and summarized transfer journal.

All firm and household cash use exact signed 64-bit cents; state transitions reject negative balances. Monetary issuance and debt are disabled. Household purchases are atomic. `State.transfer` is the single monetary transaction primitive. Integer bounds are adequate for the delivered configuration but are not proved for arbitrary enormous configured populations or balances; production deployments should add overflow guards.

## Files

- `model.py`: typed scenario and validation
- `state.py`: arrays and conserved ledger
- `engine.py`: deterministic period scheduler
- `metrics.py`: Gini calculation
- `persistence.py`: exact state checkpoints, CSV/JSONL and SQLite experiment metadata
- `cli.py`: scenario runner, resume and replication suite
- `tests/test_simulation.py`: regression and analytical sanity cases

## Scaling contract

The state has `O(N × sectors + households + firms)` storage. Each period sorts candidate skills for each hiring firm and loops over household demands; this is a transparent CPU reference implementation, **not yet optimized for 1,000,000 agents**. All scheduling is sequential, so there is no claim of multithread reproducibility. Efficient vectorization or Numba must preserve accounting and deterministic event semantics or document any difference.
