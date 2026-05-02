Codex CLI

If no subcommand is specified, options will be forwarded to the interactive CLI.

Usage: codex [OPTIONS] [PROMPT]
       codex [OPTIONS] <COMMAND> [ARGS]

Commands:
  exec         Run Codex non-interactively [aliases: e]
  review       Run a code review non-interactively
  login        Manage login
  logout       Remove stored authentication credentials
  mcp          Manage external MCP servers for Codex
  plugin       Manage Codex plugins
  mcp-server   Start Codex as an MCP server (stdio)
  app-server   [experimental] Run the app server or related tooling
  completion   Generate shell completion scripts
  update       Update Codex to the latest version
  sandbox      Run commands within a Codex-provided sandbox
  debug        Debugging tools
  apply        Apply the latest diff produced by Codex agent as a `git apply` to
               your local working tree [aliases: a]
  resume       Resume a previous interactive session (picker by default; use
               --last to continue the most recent)
  fork         Fork a previous interactive session (picker by default; use --last
               to fork the most recent)
  cloud        [EXPERIMENTAL] Browse tasks from Codex Cloud and apply changes
               locally
  exec-server  [EXPERIMENTAL] Run the standalone exec-server service
  features     Inspect feature flags
  help         Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Optional user prompt to start the session

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from
          `~/.codex/config.toml`. Use a dotted path (`foo.bar.baz`) to override
          nested values. The `value` portion is parsed as TOML. If it fails to
          parse as TOML, the raw string is used as a literal.
          
          Examples: - `-c model="o3"` - `-c
          'sandbox_permissions=["disk-full-read-access"]'` - `-c
          shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c
          features.<name>=false`

      --remote <ADDR>
          Connect the TUI to a remote app server websocket endpoint.
          
          Accepted forms: `ws://host:port` or `wss://host:port`.

      --remote-auth-token-env <ENV_VAR>
          Name of the environment variable containing the bearer token to send to
          a remote app server websocket

  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt

  -m, --model <MODEL>
          Model the agent should use

      --oss
          Use open-source provider

      --local-provider <OSS_PROVIDER>
          Specify which local provider to use (lmstudio or ollama). If not
          specified with --oss, will use config default or show selection

  -p, --profile <CONFIG_PROFILE>
          Configuration profile from config.toml to specify default options

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell
          commands
          
          [possible values: read-only, workspace-write, danger-full-access]

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing.
          EXTREMELY DANGEROUS. Intended solely for running in environments that
          are externally sandboxed

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --add-dir <DIR>
          Additional directories that should be writable alongside the primary
          workspace

  -a, --ask-for-approval <APPROVAL_POLICY>
          Configure when the model requires human approval before executing a
          command

          Possible values:
          - untrusted:  Only run "trusted" commands (e.g. ls, cat, sed) without
            asking for user approval. Will escalate to the user if the model
            proposes a command that is not in the "trusted" set
          - on-failure: DEPRECATED: Run all commands without asking for user
            approval. Only asks for approval if a command fails to execute, in
            which case it will escalate to the user to ask for un-sandboxed
            execution. Prefer `on-request` for interactive runs or `never` for
            non-interactive runs
          - on-request: The model decides when to ask the user for approval
          - never:      Never ask for user approval Execution failures are
            immediately returned to the model

      --search
          Enable live web search. When enabled, the native Responses `web_search`
          tool is available to the model (no per‑call approval)

      --no-alt-screen
          Disable alternate screen mode
          
          Runs the TUI in inline mode, preserving terminal scrollback history.
          This is useful in terminal multiplexers like Zellij that follow the
          xterm spec strictly and disable scrollback in alternate screen buffers.

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version


Claude Code - starts an interactive session by default, use -p/--print for
non-interactive output

Arguments:
  prompt                                            Your prompt

Options:
  --add-dir <directories...>                        Additional directories to allow tool access to
  --agent <agent>                                   Agent for the current session. Overrides the 'agent' setting.
  --agents <json>                                   JSON object defining custom agents (e.g. '{"reviewer": {"description": "Reviews code", "prompt": "You are a code reviewer"}}')
  --allow-dangerously-skip-permissions              Enable bypassing all permission checks as an option, without it being enabled by default. Recommended only for sandboxes with no internet access.
  --allowedTools, --allowed-tools <tools...>        Comma or space-separated list of tool names to allow (e.g. "Bash(git *) Edit")
  --append-system-prompt <prompt>                   Append a system prompt to the default system prompt
  --bare                                            Minimal mode: skip hooks, LSP, plugin sync, attribution, auto-memory, background prefetches, keychain reads, and CLAUDE.md auto-discovery. Sets CLAUDE_CODE_SIMPLE=1. Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings (OAuth and keychain are never read). 3P providers (Bedrock/Vertex/Foundry) use their own credentials. Skills still resolve via /skill-name. Explicitly provide context via: --system-prompt[-file], --append-system-prompt[-file], --add-dir (CLAUDE.md dirs), --mcp-config, --settings, --agents, --plugin-dir.
  --betas <betas...>                                Beta headers to include in API requests (API key users only)
  --brief                                           Enable SendUserMessage tool for agent-to-user communication
  --chrome                                          Enable Claude in Chrome integration
  -c, --continue                                    Continue the most recent conversation in the current directory
  --dangerously-skip-permissions                    Bypass all permission checks. Recommended only for sandboxes with no internet access.
  -d, --debug [filter]                              Enable debug mode with optional category filtering (e.g., "api,hooks" or "!1p,!file")
  --debug-file <path>                               Write debug logs to a specific file path (implicitly enables debug mode)
  --disable-slash-commands                          Disable all skills
  --disallowedTools, --disallowed-tools <tools...>  Comma or space-separated list of tool names to deny (e.g. "Bash(git *) Edit")
  --effort <level>                                  Effort level for the current session (low, medium, high, xhigh, max)
  --exclude-dynamic-system-prompt-sections          Move per-machine sections (cwd, env info, memory paths, git status) from the system prompt into the first user message. Improves cross-user prompt-cache reuse. Only applies with the default system prompt (ignored with --system-prompt). (default: false)
  --fallback-model <model>                          Enable automatic fallback to specified model when default model is overloaded (only works with --print)
  --file <specs...>                                 File resources to download at startup. Format: file_id:relative_path (e.g., --file file_abc:doc.txt file_def:img.png)
  --fork-session                                    When resuming, create a new session ID instead of reusing the original (use with --resume or --continue)
  --from-pr [value]                                 Resume a session linked to a PR by PR number/URL, or open interactive picker with optional search term
  -h, --help                                        Display help for command
  --ide                                             Automatically connect to IDE on startup if exactly one valid IDE is available
  --include-hook-events                             Include all hook lifecycle events in the output stream (only works with --output-format=stream-json)
  --include-partial-messages                        Include partial message chunks as they arrive (only works with --print and --output-format=stream-json)
  --input-format <format>                           Input format (only works with --print): "text" (default), or "stream-json" (realtime streaming input) (choices: "text", "stream-json")
  --json-schema <schema>                            JSON Schema for structured output validation. Example: {"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}
  --max-budget-usd <amount>                         Maximum dollar amount to spend on API calls (only works with --print)
  --mcp-config <configs...>                         Load MCP servers from JSON files or strings (space-separated)
  --mcp-debug                                       [DEPRECATED. Use --debug instead] Enable MCP debug mode (shows MCP server errors)
  --model <model>                                   Model for the current session. Provide an alias for the latest model (e.g. 'sonnet' or 'opus') or a model's full name (e.g. 'claude-sonnet-4-6').
  -n, --name <name>                                 Set a display name for this session (shown in the prompt box, /resume picker, and terminal title)
  --no-chrome                                       Disable Claude in Chrome integration
  --no-session-persistence                          Disable session persistence - sessions will not be saved to disk and cannot be resumed (only works with --print)
  --output-format <format>                          Output format (only works with --print): "text" (default), "json" (single result), or "stream-json" (realtime streaming) (choices: "text", "json", "stream-json")
  --permission-mode <mode>                          Permission mode to use for the session (choices: "acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan")
  --plugin-dir <path>                               Load plugins from a directory for this session only (repeatable: --plugin-dir A --plugin-dir B) (default: [])
  -p, --print                                       Print response and exit (useful for pipes). Note: The workspace trust dialog is skipped when Claude is run in non-interactive mode (via -p, or when stdout is not a TTY, e.g. piped or redirected output). Only use this in directories you trust.
  --remote-control-session-name-prefix <prefix>     Prefix for auto-generated Remote Control session names (default: hostname)
  --replay-user-messages                            Re-emit user messages from stdin back on stdout for acknowledgment (only works with --input-format=stream-json and --output-format=stream-json)
  -r, --resume [value]                              Resume a conversation by session ID, or open interactive picker with optional search term
  --session-id <uuid>                               Use a specific session ID for the conversation (must be a valid UUID)
  --setting-sources <sources>                       Comma-separated list of setting sources to load (user, project, local).
  --settings <file-or-json>                         Path to a settings JSON file or a JSON string to load additional settings from
  --strict-mcp-config                               Only use MCP servers from --mcp-config, ignoring all other MCP configurations
  --system-prompt <prompt>                          System prompt to use for the session
  --tmux                                            Create a tmux session for the worktree (requires --worktree). Uses iTerm2 native panes when available; use --tmux=classic for traditional tmux.
  --tools <tools...>                                Specify the list of available tools from the built-in set. Use "" to disable all tools, "default" to use all tools, or specify tool names (e.g. "Bash,Edit,Read").
  --verbose                                         Override verbose mode setting from config
  -v, --version                                     Output the version number
  -w, --worktree [name]                             Create a new git worktree for this session (optionally specify a name)

Commands:
  agents [options]                                  Manage background and configured agents
  auth                                              Manage authentication
  auto-mode                                         Inspect auto mode classifier configuration
  doctor                                            Check the health of your Claude Code auto-updater. Note: The workspace trust dialog is skipped and stdio servers from .mcp.json are spawned for health checks. Only use this command in directories you trust.
  install [options] [target]                        Install Claude Code native build. Use [target] to specify version (stable, latest, or specific version)
  mcp                                               Configure and manage MCP servers
  plugin|plugins                                    Manage Claude Code plugins
  project                                           Manage Claude Code project state
  setup-token                                       Set up a long-lived authentication token (requires Claude subscription)
  ultrareview [options] [target]                    Run a cloud-hosted multi-agent code review of the current branch (or a PR number / base branch) and print the findings
  update|upgrade                                    Check for updates and install if available


Usage: gemini [options] [command]

Gemini CLI - Defaults to interactive mode. Use
 -p/--prompt for non-interactive (headless) mode.

Commands:
  gemini mcp                   Manage MCP servers
  gemini extensions <command>  Manage Gemini CLI extensions. [aliases: extension]
  gemini skills <command>      Manage agent skills.              [aliases: skill]
  gemini hooks <command>       Manage Gemini CLI hooks.           [aliases: hook]
  gemini gemma                 Manage local Gemma model routing
  gemini [query..]             Launch Gemini CLI                        [default]

Positionals:
  query  Initial prompt. Runs in interactive mode by default; use -p/--prompt for
          non-interactive.

Options:
  -d, --debug                     Run in debug mode (open debug console with F12)
                                                       [boolean] [default: false]
  -m, --model                     Model                                  [string]
  -p, --prompt                    Run in non-interactive (headless) mode with the
                                   given prompt. Appended to input on stdin (if a
                                  ny).                                   [string]
  -i, --prompt-interactive        Execute the provided prompt and continue in int
                                  eractive mode                          [string]
      --skip-trust                Trust the current workspace for this session.
                                                       [boolean] [default: false]
  -w, --worktree                  Start Gemini in a new git worktree. If no name
                                  is provided, one is generated automatically.
                                                                         [string]
  -s, --sandbox                   Run in sandbox?                       [boolean]
  -y, --yolo                      Automatically accept all actions (aka YOLO mode
                                  , see https://www.youtube.com/watch?v=xvFZjo5Pg
                                  G0 for more details)?[boolean] [default: false]
      --approval-mode             Set the approval mode: default (prompt for appr
                                  oval), auto_edit (auto-approve edit tools), yol
                                  o (auto-approve all tools), plan (read-only mod
                                  e)
                       [string] [choices: "default", "auto_edit", "yolo", "plan"]
      --policy                    Additional policy files or directories to load
                                  (comma-separated or multiple --policy)  [array]
      --admin-policy              Additional admin policy files or directories to
                                   load (comma-separated or multiple --admin-poli
                                  cy)                                     [array]
      --acp                       Starts the agent in ACP mode          [boolean]
      --experimental-acp          Starts the agent in ACP mode (deprecated, use -
                                  -acp instead)                         [boolean]
      --allowed-mcp-server-names  Allowed MCP server names                [array]
      --allowed-tools             [DEPRECATED: Use Policy Engine instead See http
                                  s://geminicli.com/docs/core/policy-engine] Tool
                                  s that are allowed to run without confirmation
                                                                          [array]
  -e, --extensions                A list of extensions to use. If not provided, a
                                  ll extensions are used.                 [array]
  -l, --list-extensions           List all available extensions and exit.
                                                                        [boolean]
  -r, --resume                    Resume a previous session. Use "latest" for mos
                                  t recent or index number (e.g. --resume 5)
                                                                         [string]
      --list-sessions             List available sessions for the current project
                                   and exit.                            [boolean]
      --delete-session            Delete a session by index number (use --list-se
                                  ssions to see available sessions).     [string]
      --include-directories       Additional directories to include in the worksp
                                  ace (comma-separated or multiple --include-dire
                                  ctories)                                [array]
      --screen-reader             Enable screen reader mode for accessibility.
                                                                        [boolean]
  -o, --output-format             The format of the CLI output.
                                [string] [choices: "text", "json", "stream-json"]
      --raw-output                Disable sanitization of model output (e.g. allo
                                  w ANSI escape sequences). WARNING: This can be
                                  a security risk if the model output is untruste
                                  d.                                    [boolean]
      --accept-raw-output-risk    Suppress the security warning when using --raw-
                                  output.                               [boolean]
  -v, --version                   Show version number                   [boolean]
  -h, --help                      Show help                             [boolean]
