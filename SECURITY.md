# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could enable exploitation, data exposure, server-side request forgery (SSRF), unsafe file access, or abuse of a future hosted service.

Use GitHub's private vulnerability reporting feature when enabled for this repository. If that is not available, contact the repository maintainer privately through the contact method listed on the maintainer's GitHub profile.

## Security model

Backlink Intelligence is expected to process URLs supplied by users. Network-enabled releases therefore treat URL fetching as security-sensitive functionality.

Future implementations should protect against, at minimum:

- localhost and loopback targets,
- private and link-local IP ranges,
- cloud metadata endpoints,
- DNS rebinding and redirect-to-private-network behavior,
- excessive redirect chains,
- oversized responses,
- decompression bombs,
- unexpectedly slow endpoints,
- unsupported schemes,
- unsafe local file paths,
- use as a generic open proxy,
- and uncontrolled concurrency during bulk analysis.

## Hosted deployment warning

A command-line tool that fetches user-supplied URLs and an internet-facing web service have different risk profiles. Do not expose the crawler as a public web endpoint without additional validation, rate limiting, abuse prevention, request isolation, and SSRF defenses.

## Secrets

Never commit API keys, tokens, passwords, cookies, or client datasets containing confidential information. Use environment variables or local configuration files excluded by `.gitignore` for optional integrations.
