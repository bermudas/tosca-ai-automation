# Developing tosca_cli.py

Notes for changing the CLI itself (carried over from the original toscacloud_cli repo's CLAUDE.md / copilot-instructions). Commands run from the repo root.

## Setup and smoke test

```bash
python3 -m venv tools/toscacloud-cli/.venv && source tools/toscacloud-cli/.venv/bin/activate
pip install -r tools/toscacloud-cli/requirements.txt
cp tools/toscacloud-cli/.env.example tools/toscacloud-cli/.env   # then fill in your credentials
python tools/toscacloud-cli/tosca_cli.py config test
```
Config and token cache live next to the script (`tools/toscacloud-cli/.env`, `token.json`) — never in `~/.tosca_cli`.

```bash
python tools/toscacloud-cli/tosca_cli.py config test
python tools/toscacloud-cli/tosca_cli.py inventory search "login" --type TestCase
python tools/toscacloud-cli/tosca_cli.py playlists list
```

## CLI architecture

A Python CLI (`tosca_cli.py`) for Tricentis TOSCA Cloud REST APIs. Single-file, no hidden packages.
Covers: Identity, MBT/Builder v2 (test cases, modules, reuseable blocks), Playlists v2, Inventory v3 + v1 (undocumented folder ops), Simulations v1.

Single file, no sub-packages:
- `ToscaClient` class — all HTTP calls, one method per API endpoint. URL builders: `identity()`, `mbt()`, `playlist()`, `inventory_url()`, `inventory_v1_url()`, `simulations_url()`, `e2g_url()`.
- Typer sub-apps: `config_app`, `identity_app`, `cases_app`, `modules_app`, `blocks_app`, `playlists_app`, `inventory_app`, `simulations_app`.
- `_get_access_token()` — OAuth2 client_credentials, token cached in `token.json` (0600), auto-refreshed 60 s before expiry.
- `_output_json()` — Rich syntax-highlighted JSON when stdout is a tty, plain `print(raw)` otherwise (for piping). Place `--json` **before** positional args.
- `_generate_ulid()` — Crockford base32 ULID generator, used for fresh IDs in block parameters and test case step references.

`httpx`, `typer[all]`, `rich`, `python-dotenv` — no ORM, no frameworks.

## Code style and URL builders

- Python 3.10+, type hints throughout, `|` union syntax (not `Optional` where avoidable).
- `ToscaClient` methods: one method per API endpoint, docstring with `VERB /path → ReturnType`.
- Every Typer command: `--json` flag for raw output, Rich table/panel for human output.
- Use `_output_json(data)` for JSON output — it auto-detects tty vs pipe.
- Use `_exit_err(msg)` for user-facing errors (prints red, raises `typer.Exit(1)`).
- Use `_generate_ulid()` whenever a fresh ULID is needed (block params, parameterLayerIds).
```python
client.identity(path)          # /_identity/api/v1/{path}
client.mbt(path)               # /{spaceId}/_mbt/api/v2/builder/{path}
client.playlist(path)          # /{spaceId}/_playlists/api/v2/{path}
client.inventory_url(path)     # /{spaceId}/_inventory/api/v3/{path}
client.inventory_v1_url(path)  # /{spaceId}/_inventory/api/v1/{path}  (undocumented)
client.simulations_url(path)   # /{spaceId}/_simulations/api/v1/{path}
client.e2g_url(path)           # /{spaceId}/_e2g/api/{path}            (execution units, attachments, agent logs)
```
> The "(block params, parameterLayerIds)" wording in the `_generate_ulid()` line conflicts with the skill's parameterLayerId rule. Change it to "(block params, reference ids, parameter entry ids)".

## Adding a new CLI command

1. Add a `ToscaClient` method with a docstring: HTTP verb, endpoint path, return type.
2. Add a Typer command on the relevant `*_app` with `--json` flag and Rich output.
3. Update `README.md` Command Reference section.
4. If it exposes a new API quirk, add a row to the Known API Limitations table in `README.md`.
> copilot-instructions L106-116 has the same checklist printed **twice** (a copy-paste duplicate). AGENTS.md L58 says to add quirks to "the caveats table in `.github/copilot-instructions.md` and the Skill caveats table". After the consolidation, point all three at the skill.
