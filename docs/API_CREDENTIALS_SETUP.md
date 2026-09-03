# OpenAI and Blogger credentials setup

This project can use local Codex authentication or an OpenAI API key for text
generation. Blogger always uses Google OAuth:

| Service | What the project needs | Local setting/file |
| --- | --- | --- |
| Codex (default) | Local ChatGPT sign-in | `codex login` |
| OpenAI API (optional) | An OpenAI Platform API key | `OPENAI_API_KEY` in `.env` |
| Blogger | A Google **Desktop app OAuth client** | `credentials.json` |
| Blogger | An OAuth token created after you approve access | `token.json` (created automatically) |
| Blogger | Optional numeric destination blog ID | `BLOGGER_BLOG_ID` in `.env` |

The Blogger integration does **not** use a plain Google API key. Creating posts
and listing the current user's blogs access private account data, so Google
requires OAuth 2.0 authorization. A plain Blogger API key is only sufficient for
some public-data requests and will not work for this application's publishing
flow.

## 1. Install the application and create `.env`

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Keep all remaining commands in this guide in the project root—the directory
that contains `pyproject.toml`, `.env`, and (later) `credentials.json`.

## 2. Choose Codex login or an OpenAI API key

For local Codex authentication without API credits, follow
[Use local Codex authentication](CODEX_LOCAL_AUTH.md). Leave
`OPENAI_API_KEY` empty and set `GENERATOR_PROVIDER=codex`.

The remaining section is only for `GENERATOR_PROVIDER=openai`.

### Create and configure the optional OpenAI API key

An OpenAI API key belongs to the OpenAI API Platform. A ChatGPT subscription
does not automatically provide API credits; API billing and usage are managed
separately on the Platform.

1. Sign in to the [OpenAI API Platform](https://platform.openai.com/).
2. Select or create the project that should own this application's usage.
3. Open [API keys](https://platform.openai.com/api-keys).
4. Select **Create new secret key**.
5. Give it a recognizable name, such as `news2blogger-local`.
6. Choose the project and permissions. For the simplest local setup, use the
   default/all permissions. If you use restricted permissions, allow the model
   and Responses API operations needed to generate text.
7. Create the key and copy it immediately. The full secret may only be displayed
   once.
8. If the project has no API billing configured, add a payment method or credits
   and set an appropriate project usage limit. See the
   [OpenAI billing overview](https://platform.openai.com/settings/organization/billing/overview).

Open `.env` and set the key:

```dotenv
OPENAI_API_KEY=sk-your-secret-key-here
OPENAI_MODEL=gpt-5-mini
```

Do not add spaces around `=`. Quotes are normally unnecessary. Keep the default
model unless you intentionally want to use another model available to your
OpenAI project.

Confirm that the application loads the value without printing the secret:

```bash
python -c 'from news2blogger.config import Settings; s = Settings.from_env(); print("OpenAI key loaded:", bool(s.openai_api_key)); print("Model:", s.openai_model)'
```

Expected output starts with `OpenAI key loaded: True`. This checks local
configuration only; the first `--dry-run` in step 5 makes a real API request.
OpenAI's official quickstart also recommends loading the key from the
`OPENAI_API_KEY` environment variable rather than embedding it in source code.

## 3. Create the Google OAuth credentials for Blogger

Before starting, make sure the Google account you will authorize can access the
target blog in [Blogger](https://www.blogger.com/). For safer testing, consider
using a test blog first.

### 3.1 Create a Google Cloud project and enable Blogger API v3

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Use the project selector at the top of the page to select an existing project
   or create a new one, for example `news2blogger`.
3. Open the [API Library](https://console.cloud.google.com/apis/library).
4. Search for **Blogger API** (the service may be displayed as **Blogger API**).
5. Open it and select **Enable**.

### 3.2 Configure the OAuth consent screen

Google currently groups OAuth setup under **Google Auth Platform**. The precise
menu labels can change, but the required values are the same.

1. Open [Google Auth Platform](https://console.cloud.google.com/auth/overview)
   for the same Cloud project and start its configuration if prompted.
2. Under **Branding**, enter an app name such as `news2blogger`, choose a user
   support email, and add your developer contact email.
3. Under **Audience**:
   - Choose **Internal** only if the app and authorizing account belong to the
     same Google Workspace organization and your administrator permits it.
   - Otherwise choose **External** and leave the app in **Testing** for personal
     setup.
4. For an External app in Testing, add the Google account that owns or manages
   the Blogger blog as a **test user**. If this step is missed, Google may reject
   sign-in with `access_denied` or an "app is being tested" message.
5. Under **Data Access**, add the Blogger scope used by this project:

   ```text
   https://www.googleapis.com/auth/blogger
   ```

For personal use or a small known group, keeping the app in Testing is usually
enough and Google verification is not normally required. Google notes that a
Testing authorization can expire after seven days, so you may occasionally
need to authorize again. Public production use can require Google app/brand or
scope verification.

### 3.3 Create and download a Desktop OAuth client

1. In Google Auth Platform, open **Clients**.
2. Select **Create client**.
3. Set **Application type** to **Desktop app**.
4. Name it, for example `news2blogger desktop`, and create it.
5. Download the client JSON file.
6. Move the downloaded file into this project's root and rename it exactly:

   ```text
   credentials.json
   ```

The downloaded filename often resembles
`client_secret_123....apps.googleusercontent.com.json`; renaming it does not
change its contents. Do not paste the JSON values into `.env`.

Confirm the expected files exist:

```bash
ls -l .env credentials.json
```

If you prefer another filename or directory, set its path in `.env`:

```dotenv
BLOGGER_CLIENT_SECRETS=/absolute/path/to/blogger-client.json
```

## 4. Authorize Blogger and find the blog ID

With the virtual environment active, run:

```bash
news2blogger list-blogs
```

What happens:

1. The CLI opens the system browser using Google's installed-app OAuth flow.
2. Sign in with the Google account listed as a test user and which can manage
   the destination blog.
3. Review the permission request and approve Blogger access.
4. Google redirects the browser to a temporary local address. The CLI receives
   the authorization result; no redirect URL needs to be configured manually
   for a Desktop client.
5. The CLI creates `token.json` and restricts its permissions on macOS/Linux.
6. The command prints one line per accessible blog in this order:

   ```text
   BLOG_ID    BLOG_NAME    BLOG_URL
   ```

If the account has exactly one accessible blog, leave `BLOGGER_BLOG_ID` empty.
The application asks Google Blogger for the blog list and selects that sole blog
automatically:

```dotenv
BLOGGER_BLOG_ID=
```

If the account has multiple blogs, automatic selection stops to prevent posting
to the wrong destination. Copy the intended blog's numeric ID from the first
column and add it to `.env`:

```dotenv
BLOGGER_BLOG_ID=1234567890123456789
BLOGGER_CLIENT_SECRETS=credentials.json
BLOGGER_TOKEN_FILE=token.json
BLOGGER_PUBLISH=false
```

Keep `BLOGGER_PUBLISH=false` while testing. This makes normal Blogger operations
create drafts rather than immediately publishing them.

## 5. Verify the complete configuration safely

First, test article retrieval and OpenAI generation without contacting Blogger:

```bash
news2blogger url 'https://example.com/a-real-article' --dry-run
```

Replace the example URL with a publicly accessible article you are allowed to
process. A successful run prints a generated title and HTML. It consumes OpenAI
API usage but does not create a Blogger post.

Then create a Blogger **draft**:

```bash
news2blogger url 'https://example.com/a-real-article'
```

If you use the same URL as the dry run, it is still eligible because dry runs
are not recorded as published. Confirm the result in Blogger's **Posts** list.
Only use `--publish` after the draft output and target blog have been verified.

## Complete `.env` example

```dotenv
# OpenAI
OPENAI_API_KEY=sk-your-secret-key-here
OPENAI_MODEL=gpt-5-mini

# Output
TARGET_LANGUAGE=Khmer
SUMMARY_MAX_WORDS=350

# Blogger OAuth and destination
# Optional when the authorized account has exactly one accessible blog
BLOGGER_BLOG_ID=
BLOGGER_CLIENT_SECRETS=credentials.json
BLOGGER_TOKEN_FILE=token.json

# Keep drafts as the default
BLOGGER_PUBLISH=false

# Local state
DATABASE_PATH=data/news2blogger.db
LOG_LEVEL=INFO
HTTP_USER_AGENT=news2blogger/0.1 (+https://www.blogger.com/)
```

## Credential security

- Never commit or share `.env`, `credentials.json`, or `token.json`. This
  repository's `.gitignore` excludes all three.
- Never put `OPENAI_API_KEY` in Python source, screenshots, issue reports, or
  client-side/browser code.
- Treat `token.json` as a password: it contains credentials that can act with
  the Blogger permission you approved.
- If an OpenAI key is exposed, delete it in the OpenAI API keys page and create
  a replacement.
- If Blogger OAuth files are exposed, revoke the app's access in your Google
  Account, delete the affected OAuth client in Google Cloud, and create a new
  one.
- Use separate credentials and Google Cloud projects for local testing and a
  production deployment.

## Troubleshooting

### `OPENAI_API_KEY is required`

Make sure `.env` is in the directory where you run the command, the variable is
spelled exactly `OPENAI_API_KEY`, and its value is not empty. If the file is
elsewhere, pass it explicitly:

```bash
news2blogger --env-file /absolute/path/to/.env url 'https://example.com/article' --dry-run
```

### OpenAI reports an invalid key, permission error, quota error, or unavailable model

- Verify that the key has not been deleted and belongs to the expected OpenAI
  project.
- Check API billing, project limits, and available credit.
- If the key uses restricted permissions, allow the required Responses/model
  operations or create a key with the default permissions.
- Make sure `OPENAI_MODEL` names a model available to that project.

### `Blogger OAuth credentials not found: credentials.json`

Run the command from the project root, verify that the downloaded file was
renamed correctly, or set `BLOGGER_CLIENT_SECRETS` to the correct path. The file
must be the JSON for a **Desktop app** OAuth client—not an API key download or a
Web application client.

### Google says the app is blocked, is being tested, or returns `access_denied`

Open Google Auth Platform's **Audience** page and add the exact Google account
you are using as a test user. Also confirm that the account can manage the blog.

### `redirect_uri_mismatch`

Delete or replace `credentials.json` with credentials created using the
**Desktop app** client type. Do not use a Web application client. The CLI starts
a temporary loopback server automatically.

### Blogger API has not been used, is disabled, or returns a 403

Enable **Blogger API v3** in the same Google Cloud project that owns the OAuth
client. After enabling it, wait briefly and retry.

### The browser authorization succeeded but no blogs are listed

The authorized Google account has no accessible Blogger blogs. Sign into
Blogger with that account and create a blog or grant it access to the intended
blog. To change accounts, remove the local `token.json` and run
`news2blogger list-blogs` again.

### OAuth worked before but now returns `invalid_grant` or repeatedly asks for access

This commonly happens after a token is revoked/expired or while an External app
remains in Testing. Remove `token.json`, verify the account is still a test user,
and run `news2blogger list-blogs` to authorize again. Removing `token.json` only
removes the local authorization token; it does not delete Blogger posts or the
downloaded `credentials.json`.

## References

- [OpenAI developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI API authentication](https://developers.openai.com/api/reference/overview)
- [Blogger API authorization](https://developers.google.com/blogger/docs/3.0/using)
- [Google OAuth 2.0 for desktop apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google OAuth testing and verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)
