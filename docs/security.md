# Security and limitations

## Security

- **No authentication is built in.** Anyone who can reach the server can use it, including the hosted demo. Run it on a trusted network or behind an authenticating proxy, and do not upload confidential data to the public demo.
- **Secrets stay on the server.** AI keys, webhook URLs and signing secrets are read from the backend environment, excluded from logs and settings output, and never returned by the API (covered by a test). `.env` files are ignored by Git.
- **Uploads are untrusted data.** Files are size-limited while streaming, checked for type, binary content, encoding and structure, and parsed only as text. Nothing in a file is executed.
- **Filenames are not trusted.** Stored files use server-generated ids; the uploaded name is cleaned and used only as a label. Ids in URLs are validated before use.
- **Spreadsheet formula injection** is neutralised in CSV exports by prefixing cells that start with `=`, `+`, `-`, `@`, tab or carriage return.
- **Reports are static.** HTML reports escape all data and are served with a Content Security Policy that blocks scripts and external requests.
- **External calls need intent.** AI and webhook calls happen only on an explicit user action or the explicitly enabled report rule, with timeouts and error handling. Webhooks must use HTTPS and redirects are not followed.
- **Signed links.** Report PDF and confirmation links sent to Make.com are HMAC-signed, bound to one event and purpose, and expire. Signatures are removed before links are stored.
- **Data minimisation.** Only aggregated figures go to the AI provider; webhook payloads contain metrics, not rows.
- **HTTP hardening.** CORS is restricted to configured origins, and responses carry `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` headers.

## Storage

Everything is stored under `DATA_DIR`: the original upload and a working copy of each dataset, metadata and cleaning history in SQLite, generated report files, and automation and activity history. It survives restarts only when that directory is on a persistent disk, which is not the case on Render's free plan.

Deleting a dataset removes its files and cleaning history; reports generated from it are kept, because each report stores its own rendered files. The display currency setting is stored in the browser only.

## Known limitations

- CSV only; Excel files must be exported to CSV first. Files are processed in memory, so the size limit should stay modest.
- Single-user, single-server design with no per-user data separation.
- Business columns are detected from English column names; other names need manual mapping.
- Ambiguous dates are interpreted day-first (for example `03/04/2025` is 3 April), and the chosen format is shown.
- Revenue is treated as a single currency; the currency symbol is only a display label.
- Trends are straight-line fits over past periods, not forecasts.
- One AI provider is implemented, and AI output is labelled but not automatically fact-checked.
- Reports are generated on request; there is no scheduling.
