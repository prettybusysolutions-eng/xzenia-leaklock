# Releasing

The repository has a dated proof-packet release. The next code release must use `v0.1.0` after the default-branch regression suite passes.

## Required gate

1. Start from the exact default-branch commit to be released.
2. Reproduce the repository quickstart in a clean environment.
3. Confirm all required GitHub checks pass on that commit.
4. Update the changelog or prepare generated release notes.
5. Create an annotated Semantic Versioning tag: \`vMAJOR.MINOR.PATCH\`.
6. Create a GitHub release from that exact tag.
7. Verify any package registry version and digest match the release.

## Claim boundary

A release proves a versioned artifact exists. It does not prove production
readiness, security certification, third-party validation, adoption, revenue,
or performance. Those claims require separate evidence.
