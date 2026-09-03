# news2blogger

A Python CLI that downloads an article, creates an original translated summary,
adds visible credit and a source link, and sends it to Blogger. Posts are created
as **drafts by default**.

## What it does

- Accepts one article URL or recent entries from an RSS/Atom feed.
- Extracts the main article text and available author/publisher metadata.
- Uses local Codex ChatGPT authentication by default to produce a structured
  translated summary; OpenAI API-key mode remains optional.
- Renders safe HTML with key points, credit, reference link, and disclosure.
- Prevents duplicate processing with a local SQLite database.
- Authenticates to Blogger through Google's installed-app OAuth flow.
- Supports dry runs, drafts, and explicit immediate publishing.

Use sources you are permitted to access and follow their terms. The application
does not bypass paywalls or access controls. Summaries should not substitute for
the source; attribution and the original link are always included.

## Setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env` and set `TARGET_LANGUAGE`. `OPENAI_API_KEY` can remain empty when
using the default local Codex provider. `BLOGGER_BLOG_ID` can remain empty when
the authorized Google account has exactly one blog.

Authenticate the local Codex CLI once:

```bash
codex login
codex login status
```

See [Using local Codex authentication](docs/CODEX_LOCAL_AUTH.md) for the full
configuration and security details.

For click-by-click instructions covering OpenAI API billing/key creation,
Google Auth Platform, OAuth test users, `credentials.json`, `token.json`, blog
ID discovery, security, verification, and common errors, see the
[OpenAI and Blogger credentials setup guide](docs/API_CREDENTIALS_SETUP.md).

To keep sensitive `.env` values encrypted at rest, see
[Encrypting environment values](docs/ENCRYPTED_ENV.md). The application can
decrypt `ENC[v1:...]` values automatically when the master passphrase is
provided separately. The short workflow is:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
read -r -s "NEWS2BLOGGER_ENV_PASSPHRASE?Enter encryption passphrase: "
printf '\n'
export NEWS2BLOGGER_ENV_PASSPHRASE
python scripts/encrypt_env.py
news2blogger --env-file .env.encrypted url 'https://example.com/article' --dry-run
```

The encryption script asks for the passphrase again and stops if confirmation
does not match.

### Configure Blogger OAuth

> Blogger publishing requires a Desktop app OAuth client, not a plain Google
> API key. See the [detailed credentials guide](docs/API_CREDENTIALS_SETUP.md)
> if this is your first setup.

1. Create or select a Google Cloud project.
2. Enable **Blogger API v3**.
3. Configure the OAuth consent screen.
4. Create an OAuth client ID for a **Desktop app**.
5. Download it as `credentials.json` in this directory.
6. Run `news2blogger list-blogs`. A browser opens for authorization and the CLI
   prints each accessible blog ID.
7. If exactly one blog is listed, leave `BLOGGER_BLOG_ID` empty and the app will
   select it automatically. If multiple blogs are listed, put the desired ID in
   `.env` as `BLOGGER_BLOG_ID` so the app cannot post to the wrong blog.

`credentials.json`, `token.json`, `.env`, logs, and the local database are all
ignored by Git.

## Usage

Preview the generated output without connecting to Blogger:

```bash
news2blogger url 'https://example.com/article' --dry-run

news2blogger url \
  'https://thehackernews.com/2026/09/google-anthropic-and-openai-unveil.html' \
  --dry-run \
  --output google-anthropic-and-openai-unveil.md
```

`--output` saves the generated title and structured content in a Markdown preview file.
Saving a preview with `--dry-run` never creates a Blogger post. After reviewing or
editing the file, publish that exact content without fetching or generating it again:

```bash
news2blogger url \
  'https://thehackernews.com/2026/09/google-anthropic-and-openai-unveil.html' \
  --output google-anthropic-and-openai-unveil.md \
  --publish
```

Published posts automatically load and use the Battambang font, with Khmer OS
Battambang and sans-serif as fallbacks.

Create a Blogger draft (the default):

```bash
news2blogger url 'https://example.com/article'
```

Process the five newest feed items as drafts:

```bash
news2blogger feed 'https://example.com/feed.xml' --limit 5
```

Publish immediately only after reviewing your configuration:

```bash
news2blogger url 'https://example.com/article' --publish
```

Set `BLOGGER_PUBLISH=true` only if immediate publishing should become the default.
Use `--force` to intentionally process a URL already recorded as successful.

## Tests and lint

```bash
pytest
ruff check .
```

## Project layout

- `fetcher.py`: URL/RSS retrieval and article extraction
- `generator.py`: summarization and translation prompt
- `formatter.py`: attributed Blogger HTML
- `blogger.py`: OAuth and Blogger API calls
- `state.py`: duplicate detection
- `service.py`: end-to-end orchestration
- `cli.py`: command-line interface
