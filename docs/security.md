# Security

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
