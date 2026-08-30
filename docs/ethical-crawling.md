# Ethical Crawling

Backlink Intelligence should collect only the information required for the requested analysis and should avoid unnecessary load on third-party websites.

## Principles

- Use a transparent, configurable user agent.
- Apply conservative per-host rate limits.
- Use timeouts and bounded retries.
- Avoid repeatedly fetching identical resources when cached evidence is sufficient.
- Bound response sizes and redirect chains.
- Do not attempt to bypass authentication, paywalls, CAPTCHAs, or access controls.
- Do not use the project as a generic proxy or content-copying service.
- Treat bulk analysis as a queue, not as unbounded concurrency.

## Robots and site policies

Crawling behavior should be documented and configurable. Users remain responsible for complying with applicable laws, contractual terms, and website policies in their jurisdiction and use case.

## Data minimization

Reports should store only the evidence required for analysis. A future public web service should avoid permanently storing user-submitted URLs and extracted content unless storage is clearly disclosed and necessary.
