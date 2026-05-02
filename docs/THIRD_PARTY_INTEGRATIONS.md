# Third-Party Integrations

Hive Mind should prefer optional adapters for third-party tools unless their
license clearly allows bundling, redistribution, hosted service use, and future
commercial packaging.

## `llm-checker`

Source:

- GitHub: `https://github.com/Pavelevich/llm-checker`
- NPM package: `llm-checker`

Use in Hive Mind:

- Treat as optional external CLI/MCP capability.
- Do not vendor source code into this repository.
- Do not list it as a required runtime dependency.
- Keep `hive local checker` as an adapter that detects a user-installed
  `llm-checker` binary or, when explicitly requested, can run through `npx`.
- Attribute the upstream project when showing adapter output or generated
  reports.

License note:

The upstream project currently uses `LLM Checker No Paid Distribution License
(NPDL-1.0)`. That license allows free use/copy/modify/redistribution with
notice, but forbids paid distribution, monetized delivery, and hosted/managed/API
service delivery without a separate commercial license from the copyright
holder.

Product rule:

For a public free GitHub release, an optional adapter plus attribution is enough.
For any paid Hive Mind distribution, hosted service, bundled installer, or
commercial package that includes or depends on `llm-checker`, contact the
maintainer first and get explicit permission or a commercial license.

Hive Mind still owns its built-in `hive local benchmark` command. The optional
`llm-checker` adapter can enrich or cross-check recommendations, but it is not
required for the local JSON-validity and latency smoke benchmark.
