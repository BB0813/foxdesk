# Product

## Register

product

## Users

Operators and developers who need to run multiple Camoufox browser profiles locally for controlled browsing, testing, automation, or account/session isolation. They work in a task-heavy environment and need quick visibility into profile settings, proxies, running sessions, and Camoufox installation state.

## Product Purpose

**FoxDesk** (local Camoufox fingerprint browser manager) provides a local GUI for creating fingerprint profiles, launching and stopping sessions, checking installation status, managing proxy pools, encrypted local backups, and in-app updates. Success means a user can manage browser profiles without hand-editing launch scripts or remembering CLI flags — and without a cloud control plane.

## Brand Personality

Precise, quiet, operational. The interface should feel like a reliable control panel, not a marketing site or decorative dashboard.

## Anti-references

Avoid oversized landing-page hero layouts, decorative glass panels, generic SaaS gradients, and low-density card grids. Avoid hiding launch-critical settings behind vague labels.

## Design Principles

1. Make the current operational state obvious: installed, missing, running, failed, or stopped.
2. Keep launch parameters explicit and editable without requiring code changes.
3. Prefer compact panels, predictable forms, and clear action states over visual novelty.
4. Treat logs as first-class output because launch failures are common during browser setup.
5. Keep the GUI usable even before Camoufox is installed.
6. Keep secrets local: DPAPI / encrypted backups; never ship cloud credentials in the package.

## Accessibility & Inclusion

Target WCAG AA contrast, keyboard-accessible controls, visible focus states, reduced-motion support, and non-color-only status indicators.

## Out of scope

- Multi-tenant cloud control
- Guaranteed anti-detect outcomes
- Embedding third-party API tokens in the repository or installer
