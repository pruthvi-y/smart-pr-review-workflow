# Dependency Policy

## Supported dependencies

Production dependencies should remain on supported versions where practical. Upgrades should identify the old and new versions and call out breaking-change risk.

## Testing

Dependency upgrades should include relevant unit or integration tests. For security-related dependency changes, regression testing of the affected service is expected.

## Major versions

Major-version upgrades require explicit compatibility review because APIs and runtime behavior may change.
