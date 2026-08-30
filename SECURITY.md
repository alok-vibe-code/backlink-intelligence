# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could enable exploitation, data exposure, server-side request forgery (SSRF), unsafe file access, or abuse of a future hosted service.

Use GitHub's private vulnerability reporting feature when enabled for this repository. If that is not available, contact the repository maintainer privately through the contact method listed on the maintainer's GitHub profile.

## Security model

Backlink Intelligence processes URLs supplied by users. Network-enabled functionality therefore treats URL fetching as security-sensitive.

The v1 fetcher blocks or bounds, at minimum:

- unsupported schemes,
- credentials embedded in URLs,
- localhost and common local hostnames,
- private, loopback, link-local, reserved, multicast, and unspecified IP ranges,
- DNS resolution to non-public addresses,
- redirects to non-public addresses,
- excessive redirect chains,
- oversized responses,
- unexpectedly slow endpoints through request timeouts,
- and non-HTML content.

## Hosted deployment warning

A command-line tool that fetches user-supplied URLs and an internet-facing web service have different risk profiles. Do not expose the crawler as a public web endpoint without additional validation, centralized rate limiting, caching, abuse prevention, request isolation, logging, and SSRF defenses.

## Secrets

Never commit API keys, tokens, passwords, cookies, or client datasets containing confidential information. Use environment variables or local configuration files excluded by `.gitignore` for optional integrations.
