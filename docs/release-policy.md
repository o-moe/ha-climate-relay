# Release Policy

## Purpose

This document defines how ClimateRelayCore versions are published for HACS and
how early test builds are exposed without turning every feature branch into a
user-facing release channel.

## Distribution Channels

- Stable releases are published as normal GitHub releases.
- Early access builds are published as GitHub pre-releases.
- Short-lived public test branches may be used for focused HACS validation when
  a pre-release would be too broad.

## Versioning Scheme

Use semantic versions for published tags and releases.

Examples:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

Use semantic pre-release suffixes for non-stable HACS releases.

Examples:

- `v0.1.0-alpha.1`
- `v0.1.0-alpha.2`
- `v0.1.0-dev.1`

## Iteration Mapping

- The Git tag remains semantic and release-oriented.
- The GitHub release title and release notes must name the related iteration
  explicitly when an iteration boundary is being tested or delivered.

Examples:

- Tag: `v0.1.0-alpha.1`
- Release title: `Iteration 1.1 Alpha 1`

- Tag: `v0.1.0`
- Release title: `Iteration 1.1`

## GitHub Release Rules

- Stable user-facing installs in HACS should be backed by normal GitHub
  releases.
- Alpha or dev testing in HACS should use GitHub pre-releases rather than
  ordinary releases.
- A plain Git tag without a GitHub release is not the preferred distribution
  mechanism for HACS version selection.
- Release notes must describe scope, known limitations, and any migration or
  upgrade expectations relevant to the published build.

## Branch-Based Test Builds

- Do not publish every feature branch as a HACS-facing channel.
- If branch-based HACS testing is required, use a deliberately named public
  test branch such as `testing/iteration-1.1` or `preview/simulation-mode`.
- Public test branches should exist only as long as they are actively needed.
- Once the test purpose is finished, remove the public test branch or stop
  documenting it as an installation target.

## Recommended Workflow

1. Merge development into the intended release line.
2. For early user testing, create a GitHub pre-release such as
   `v0.1.0-alpha.1`.
3. For narrow technical validation where a pre-release is too broad, expose one
   named public test branch temporarily.
4. When the iteration is complete and accepted, publish the stable GitHub
   release such as `v0.1.0`.

## Documentation Duties

- `README.md` must describe the recommended installation path for ordinary
  users.
- `README.md` may mention that alpha or dev builds exist, but should not become
  a running release log.
- Developer-oriented release procedures belong in `docs/`.
