# Release Policy

## Purpose

This document defines how ClimateRelayCore versions are published for HACS and
how early test builds are exposed without turning every feature branch into a
user-facing release channel.

## Distribution Channels

- Stable releases are published as normal GitHub releases.
- Alpha test builds are published as GitHub pre-releases from an explicitly
  selected branch or commit.
- Beta test builds are published as GitHub pre-releases from `main`.
- Short-lived public test branches may still be used for focused HACS
  validation when a pre-release would be too broad.

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
- `v0.1.0-beta.1`

## Iteration Mapping

- The Git tag remains semantic and release-oriented.
- The GitHub release title and release notes must name the related iteration
  explicitly when an iteration boundary is being tested or delivered.

Examples:

- Tag: `v0.1.0-alpha.1`
- Release title: `Iteration 1.1 Alpha 1`

- Tag: `v0.1.0-beta.1`
- Release title: `Iteration 1.1 Beta 1`

- Tag: `v0.1.0`
- Release title: `Iteration 1.1`

## GitHub Release Rules

- Stable user-facing installs in HACS should be backed by normal GitHub
  releases.
- Alpha and beta testing in HACS should use GitHub pre-releases rather than
  ordinary releases.
- A plain Git tag without a GitHub release is not the preferred distribution
  mechanism for HACS version selection.
- Release notes must describe scope, known limitations, and any migration or
  upgrade expectations relevant to the published build.
- The integration `manifest.json` version is the source of truth for the
  release version.
- The current iteration label used in release titles is stored in
  `.github/release-plan.json`.
- No release or pre-release may be published until the exact target commit has
  green GitHub quality gates.
- Releases shall be cut from explicit, already-verified refs rather than from
  an assumed latest local state.

## Automated Workflow

- Alpha pre-releases are created manually through the GitHub Actions workflow
  `Publish Alpha Pre-Release`.
- The alpha workflow requires an explicit target ref and alpha sequence number.
- Beta pre-releases are created automatically on pushes to `main` when the
  repository still has no stable release for the current manifest version.
- Stable releases remain deliberate manual publication steps after formal
  acceptance.

## Branch-Based Test Builds

- Do not publish every pull request automatically as a HACS-facing release.
- If branch-based HACS testing is required, publish a deliberate alpha
  pre-release from the intended feature branch or use a deliberately named
  public test branch such as `testing/iteration-1.1` or
  `preview/simulation-mode`.
- Public test branches should exist only as long as they are actively needed.
- Once the test purpose is finished, remove the public test branch or stop
  documenting it as an installation target.

## Recommended Workflow

1. Set the target version in
   `custom_components/climate_relay_core/manifest.json`.
2. Set the current iteration label in `.github/release-plan.json`.
3. Push the intended release commit and wait for the GitHub quality gates on
   that exact ref to complete successfully.
4. Perform the minimum required manual HA smoke test for newly introduced or
   changed user-visible surfaces.
5. For branch-based HA testing, create the alpha pre-release only after steps
   3 and 4 are satisfied.
6. After merge to `main`, allow the automatic beta pre-release to publish the
   integrated test build.
7. For narrow technical validation where a pre-release is too broad, expose one
   named public test branch temporarily.
8. When the iteration is complete and accepted, publish the stable GitHub
   release such as `v0.1.0`.

## Documentation Duties

- `README.md` must describe the recommended installation path for ordinary
  users.
- `README.md` may mention that alpha or dev builds exist, but should not become
  a running release log.
- Developer-oriented release procedures belong in `docs/`.
