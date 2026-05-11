# Hive Mind Public Alpha Gate

Status: ready for public-alpha publication.

Production-v0 is technically closed, but public alpha has a higher bar. A user
must understand why Hive exists within five minutes without reading `.runs/`
files or already believing in multi-agent harnesses.

## Public Alpha Criteria

- [x] `hive demo quickstart` shows the core value loop without provider keys.
- [x] The quickstart run creates inspectable receipts, a memory draft, and a
  MemoryOS-compatible read model.
- [x] README starts with the quickstart path, not the full command surface.
- [x] `hive init` tells a new user the next command to run and why.
- [x] MemoryOS feedback loop demo exists: run result -> memory draft/import ->
  accepted context -> next Hive run references the accepted memory.
- [x] Public release gate verifies the feedback loop with `hive demo memory-loop`.
- [x] CLI command surface has a recommended path: `hive demo quickstart`,
  `hive run`, `hive inspect`, `hive goal`; advanced commands are secondary.
- [x] Claude/foreign-context reviewer finds no high/medium public-alpha blockers.

## Current Decision

Production-v0, onboarding, demo loop, MemoryOS feedback, release gate, and
foreign-context review are now green. Public alpha can proceed if the owner
chooses to publish or announce it.
