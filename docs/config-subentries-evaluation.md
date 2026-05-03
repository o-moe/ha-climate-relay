# Config Subentries Evaluation

## Purpose

This document evaluates whether Climate Relay should use Home Assistant config
subentries for room or regulation-profile configuration.

The decision is deliberately conservative. Config subentries may be technically
useful for repeated administrative configuration, but they are not the target
product UI for daily room-level climate operation.

## Current Home Assistant model

Home Assistant config entries persist integration configuration created through
UI flows. Config entries can be changed through reconfigure steps or options
flows.

Home Assistant config subentries allow one config entry to own repeated pieces
of configuration. They are created by config subentry flows and may support
reconfigure flows. The documented examples include repeated locations under one
parent integration entry.

Official references:

- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/core/integration/config_flow/
- https://developers.home-assistant.io/blog/2025/02/16/config-subentries/

## Candidate mapping

A Climate Relay installation maps naturally to one parent config entry:

- global presence configuration
- global fallback behavior
- global simulation mode
- global diagnostics
- integration-wide service/action registration

A Climate Relay room or regulation profile could map to one config subentry:

- primary climate anchor
- derived Home Assistant area
- optional humidity sensor
- optional window contact
- room targets
- room schedule
- room-level open-window behavior

This is structurally closer to Home Assistant's repeated-subconfiguration model
than storing every profile in one global options-flow list.

## Potential benefits

Using config subentries for rooms could provide:

- clearer separation between global integration configuration and repeated room
  configuration
- a more Home Assistant-native administrative model than one global
  add/edit/remove options-flow list
- built-in identity boundaries for individual room/profile configuration
- more explicit migration targets if the backend later separates parent config
  from room configuration
- possible reduction of custom profile-selection logic inside the options flow

## Risks and limitations

Config subentries do not solve the product UX problem.

They are still administrative Home Assistant configuration flows. They are not a
room overview, room detail UI, schedule editor, quick override surface, or daily
climate-control experience.

Risks include:

- investing effort into a better administrative UI while delaying the custom
  daily-use frontend
- creating a second migration path before the frontend/backend contract is
  stable
- letting Home Assistant flow structure shape the product interaction model
- introducing additional lifecycle and migration complexity too early
- duplicating future frontend room-management behavior in another HA
  administrative surface

## Decision

Status: evaluate later, do not adopt now.

Climate Relay shall not adopt config subentries during the current Epic 2 / UX
correction work.

Config subentries may be reconsidered only after the frontend/backend contract
and the backend-owned room configuration operations are stable enough to judge
whether subentries reduce persistence and migration risk.

The primary target for room-level product interaction remains the custom
frontend room-management UI.

## Adoption criteria

Config subentries may be adopted only if all of the following are true:

- they reduce backend persistence complexity compared with the current `rooms`
  list
- they do not replace or delay the custom frontend room-management UI
- they can coexist with the first frontend slice without duplicating business
  logic
- they preserve stable room/profile identifiers
- they support migration from existing `rooms` options without data loss
- they can be tested with Home Assistant-native flow tests and runtime reload
  tests
- they keep daily-use workflows out of Home Assistant Developer Tools and manual
  service calls

## Rejection criteria

Config subentries shall be rejected if any of the following become true:

- they primarily improve the administrative options/configuration UX while not
  helping the target frontend
- they require duplicating room-management validation in multiple places
- they make schedule editing harder to expose through the custom frontend
- they introduce a competing persistence format for the same room state
- they make the frontend depend on Home Assistant flow internals
- they delay the first frontend slice

## Evaluation questions for a future spike

A future technical spike must answer:

1. Can one room/profile be represented as one subentry without weakening the
   backend-owned room model?
2. Can existing `rooms` options migrate to subentries without changing runtime
   behavior?
3. Can the frontend consume the same backend-owned room state regardless of
   whether storage uses options or subentries?
4. Can the frontend update room configuration through backend-owned operations
   without depending on Home Assistant subentry flow screens?
5. Does subentry adoption reduce code complexity after removing the current
   options-flow profile manager?
6. Does subentry adoption preserve or improve testability?

## Practical guidance

Until this evaluation is revisited, contributors shall:

- keep room-level options-flow configuration marked as temporary bootstrap
  scaffolding
- avoid adding new room-level options-flow UX
- avoid implementing config subentries as a side effect of unrelated work
- design backend room configuration operations independently of the current
  options-flow profile manager
- prioritize the first custom frontend slice for daily room-level use
