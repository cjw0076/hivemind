# Hive Mind Public Alpha Notes

Hive Mind is a local provider-CLI harness. It coordinates existing provider
CLIs and local workers through a shared blackboard run directory; it does not
replace provider CLIs, MemoryOS, CapabilityOS, or the MyWorld AIOS control
plane.

## First Five Minutes

Start with the provider-free quickstart:

```bash
python -m hivemind.hive demo quickstart
```

This demo requires no provider API keys. It creates a run, routing artifacts,
verification output, a memory draft, and an inspectable summary.

Optional MemoryOS feedback-loop proof:

```bash
python -m hivemind.hive demo memory-loop
```

## Maturity Boundary

Public alpha means:

- local-first run artifacts and receipts are available;
- provider execution is explicit and inspectable;
- demos work without provider credentials;
- MemoryOS and CapabilityOS integrations stay optional and sibling-owned;
- large internal modules are acknowledged as staged refactor targets, not
  hidden as finished architecture.

Public alpha does not mean:

- autonomous execution without operator gates;
- cloud service, hosted product, or credential manager;
- MemoryOS graph ownership;
- CapabilityOS tool execution authority.

## Module Split Strategy

Largest files as of ASC-0079:

- `hivemind/hivemind/harness.py`
- `hivemind/hivemind/plan_dag.py`
- `hivemind/hivemind/hive.py`

Do not split these files by size alone. Safe extraction order:

1. Extract pure report/projection helpers that already have tests.
2. Extract CLI subcommand groups only after command smoke tests cover them.
3. Extract scheduler internals only with plan DAG regression coverage.

Stop condition: any extraction that changes run artifact schema, provider
execution semantics, or inspect output without a focused test is not public
alpha hardening; it is an unsafe refactor.
