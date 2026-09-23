# Security Policy

## Dependency changes

Dependency upgrades should be evaluated for known vulnerabilities, transitive impact, and compatibility. A change that addresses a security advisory should document the reason for the upgrade and include appropriate regression testing.

## Sensitive changes

Security-sensitive changes require evidence that the affected component was reviewed. Do not claim that a vulnerability is fixed unless the supplied evidence supports that conclusion.

## Secrets

Pull requests must not introduce credentials, access tokens, private keys, or hard-coded secrets.
