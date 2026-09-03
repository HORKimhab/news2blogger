# Use local Codex authentication instead of an API key

This project uses the locally installed Codex CLI by default. Codex can sign in
with ChatGPT and use the access included with an eligible ChatGPT plan, so the
application does not need `OPENAI_API_KEY` or OpenAI API credits in this mode.
Codex plan limits still apply; this is not unlimited usage.

## 1. Install and authenticate Codex

Confirm that the CLI is available:

```bash
codex --version
```

Sign in through the browser:

```bash
codex login
```

Confirm the authentication method:

```bash
codex login status
```

The expected result is:

```text
Logged in using ChatGPT
```

Do not use `codex login --with-api-key`; that selects usage-based API billing
and would have the same API-credit requirement as the original integration.

## 2. Configure `.env`

Use these generator settings:

```dotenv
GENERATOR_PROVIDER=codex
CODEX_COMMAND=codex
CODEX_MODEL=
CODEX_TIMEOUT_SECONDS=300

# Not required for the Codex provider
OPENAI_API_KEY=
```

Leaving `CODEX_MODEL` empty uses the default Codex model available to the signed-in
ChatGPT account. This avoids hard-coding a model that the account may not have.

If you use `.env.encrypted`, regenerate it after changing the plaintext source:

```bash
python scripts/encrypt_env.py --force
```

## 3. Generate a dry run

```bash
news2blogger \
  --env-file .env.encrypted \
  url 'https://thehackernews.com/2026/09/google-anthropic-and-openai-unveil.html' \
  --dry-run
```

The application starts `codex exec` in non-interactive, ephemeral, read-only
mode. It requests schema-constrained JSON and removes `OPENAI_API_KEY`,
`CODEX_API_KEY`, and `NEWS2BLOGGER_ENV_PASSPHRASE` from the Codex child process.
The source article is still sent to the Codex model for summarization.

## Troubleshooting

### `Codex CLI was not found`

Run `codex --version`. If Codex is installed somewhere outside `PATH`, set an
absolute executable path:

```dotenv
CODEX_COMMAND=/absolute/path/to/codex
```

### Codex asks you to sign in

Run:

```bash
codex login
codex login status
```

### Codex reports a usage or plan limit

ChatGPT/Codex subscription limits still apply. Wait for the limit to reset or
use `GENERATOR_PROVIDER=openai` with a funded API key.

## Official documentation

- [Codex authentication](https://learn.chatgpt.com/en/docs/auth)
- [Codex non-interactive mode](https://learn.chatgpt.com/en/docs/non-interactive-mode)
