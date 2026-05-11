# Hive Mind Public Alpha Gate

Status: not ready.

Production-v0 is technically closed, but public alpha has a higher bar. A user
must understand why Hive exists within five minutes without reading `.runs/`
files or already believing in multi-agent harnesses.

## Public Alpha Criteria

- [x] `hive demo quickstart` shows the core value loop without provider keys.
- [x] The quickstart run creates inspectable receipts, a memory draft, and a
  MemoryOS-compatible read model.
- [ ] README starts with the quickstart path, not the full command surface.
- [ ] `hive init` tells a new user the next command to run and why.
- [ ] MemoryOS feedback loop demo exists: run result -> memory draft/import ->
  accepted context -> next Hive run references the accepted memory.
- [ ] CLI command surface has a recommended path: `hive demo quickstart`,
  `hive run`, `hive inspect`, `hive goal`; advanced commands are secondary.
- [ ] Claude/foreign-context reviewer finds no high/medium public-alpha blockers.

## Current Decision

Do not make the repository public only because production-v0 passed. Public
alpha starts after the quickstart and MemoryOS feedback loop can produce a
30-second demo with a clear before/after value signal.
