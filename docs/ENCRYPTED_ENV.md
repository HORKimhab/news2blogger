# Encrypting `.env` values

`news2blogger-env` encrypts selected dotenv values with AES-256-GCM. It derives
the encryption key from a passphrase using scrypt and uses a fresh random salt
and nonce for every value. The variable name is authenticated too, so an
encrypted value cannot silently be moved to a different setting.

This protects secrets while the encrypted file is at rest. It does not protect
them after the application decrypts them in memory, and it cannot help if an
attacker obtains both the encrypted file and the passphrase.

## Recommended local workflow

Create and activate the project environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Set the master passphrase without echoing it, then export it for the current
terminal session:

```bash
read -r -s "NEWS2BLOGGER_ENV_PASSPHRASE?Enter encryption passphrase: "
printf '\n'
export NEWS2BLOGGER_ENV_PASSPHRASE
```

Run the zero-argument Python script:

```bash
python scripts/encrypt_env.py
```

The script prompts for `Confirm encryption passphrase:`. Enter the same value
again. It stops without creating the output if confirmation does not match. It
then reads `.env`, encrypts every valid non-empty value, preserves comments and
empty placeholders, and atomically writes `.env.encrypted` with owner-only file
permissions. It refuses to overwrite an existing output; use this when you
intentionally want to regenerate it:

```bash
python scripts/encrypt_env.py --force
```

For trusted non-interactive automation, confirmation can be skipped explicitly:

```bash
python scripts/encrypt_env.py --force --no-confirm
```

The script rejects malformed, duplicate, or multiline dotenv assignments rather
than risk copying an unrecognized secret as plaintext. The Google files
`credentials.json` and `token.json` are not dotenv values and are not processed
by this tool; keep them private and outside version control.

For selective encryption, the lower-level command remains available:

```bash
news2blogger-env .env --key OPENAI_API_KEY
```

After inspecting `.env.encrypted`, remove the plaintext `.env` from normal use
and store any needed recovery copy in a password manager or other protected
location. Both `.env` and `.env.encrypted` are ignored by this repository.

## Supply the passphrase when running the app

Do not put the passphrase in `.env`, `.env.encrypted`, source code, shell
history, or a committed shell profile. Keep the passphrase exported only for
the current terminal session.

Then use the encrypted file:

```bash
news2blogger --env-file .env.encrypted url 'https://example.com/article' --dry-run
```

When finished, remove the passphrase from the shell environment:

```bash
unset NEWS2BLOGGER_ENV_PASSPHRASE
```

If you intentionally exported the passphrase before running the encryption
command, `news2blogger-env` uses it instead of prompting. Prompting is preferable
for interactive encryption because it avoids putting the passphrase in command
history.

## Production recommendation

For production, use the deployment platform's secret manager to inject
`NEWS2BLOGGER_ENV_PASSPHRASE` into the process environment at startup. Examples
include a container-orchestrator secret, a CI/CD protected secret, or a cloud
secret manager. Restrict access so the encrypted file and its passphrase are
controlled through different mechanisms.

An OS keychain is also preferable to permanently placing the passphrase in
`.zshrc`, `.bashrc`, or another plaintext profile. A small launcher can retrieve
the passphrase from the keychain, export it for this process, run the command,
and immediately unset it.

## Token format and behavior

Encrypted entries look like this:

```dotenv
OPENAI_API_KEY=ENC[v1:base64-data-here]
```

Ordinary unencrypted entries continue to work. `Settings.from_env()` detects
the `ENC[v1:...]` wrapper and decrypts it automatically. Decryption fails safely
when the passphrase is missing, incorrect, the ciphertext was modified, or the
encrypted value was moved under another variable name.

There is deliberately no command that writes a fully decrypted dotenv file.
When a value must be changed, update a protected plaintext source and generate
a new `.env.encrypted` file. Use a new strong passphrase and `--force` to rotate
the encryption:

```bash
news2blogger-env /protected/path/news2blogger.env --all \
  --output .env.encrypted --force
```

Use a long, unique passphrase—preferably several randomly generated words—and
keep a recovery copy in a password manager. Losing the passphrase means the
encrypted values cannot be recovered.

## Common errors

`OPENAI_API_KEY is encrypted; export NEWS2BLOGGER_ENV_PASSPHRASE` means the
encrypted file loaded correctly but the application cannot find the master
passphrase.

`wrong passphrase or damaged encrypted value` means authentication failed.
Re-enter the passphrase. If it still fails, restore the value from a protected
backup and encrypt it again; the tool cannot bypass authenticated encryption.

## Cryptographic design references

- [AES-GCM authenticated encryption](https://cryptography.io/en/stable/hazmat/primitives/aead/)
- [scrypt key derivation](https://cryptography.io/en/stable/hazmat/primitives/key-derivation-functions/#scrypt)
