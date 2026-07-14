# Product

## Register

product

## Users

Operators and developers who need **local, multi-profile browser environments** for controlled browsing, isolation, automation, compatibility testing, or higher-risk flows (e.g. multi-account AI platform signup/subscription on **official** flows, checkout sandboxes). They often compare environment quality to **Multilogin** / **GoLogin**. They need clear visibility into profile settings, **engine choice** (Firefox/Camoufox vs Chromium stack), proxies, running sessions, install state, and environment consistency—not a cloud control plane.

## Product Purpose

**FoxDesk** is a **local dual-engine fingerprint environment workstation**:

1. **Control plane** — GUI/API to create profiles, launch/stop sessions, manage proxy pools, encrypted local backups, diagnostics, and in-app updates.
2. **Firefox engine line** — Camoufox-based profiles (existing strength: isolation / automation-friendly Firefox stack).
3. **Chromium engine line** — First-class long-term track aimed at **environment quality** comparable to mainstream commercial Chromium fingerprint browsers, measured by **internal benchmarks** (not marketing guarantees).

Success means:

- Users manage multi-engine profiles without hand-editing launch scripts.
- Secrets and data stay on-device (no cloud control plane).
- Chromium-track quality is **measurable** (static fingerprint, WebRTC, AI signup/subscribe scripts vs **Multilogin** primary / **GoLogin** secondary) and improved through the published roadmap (R1→R2→R3→**R4 / Phase D** when patch stacks are not enough).
- **No marketing SLA** for registration success, subscription success, or “undetectable” claims.

## Positioning code

- **P-B** — Dual-engine workstation (not “Camoufox manager only”).
- **Commercial reference (internal)** — Multilogin (primary), GoLogin (secondary); see `docs/research/l3-kpi.md`.
- **Phase D (R4)** — On the roadmap: deep Chromium alignment (patched/maintained Chromium or equivalent) when Phase C benchmarks still lag the commercial reference.
- Decision log: `docs/research/engine-decision.md`
- Feasibility: `docs/dual-engine-feasibility.md`

## Brand Personality

Precise, quiet, operational. The interface should feel like a reliable control panel, not a marketing site or decorative dashboard. Never promise “undetectable”, “signup guaranteed”, or “payment/subscription guaranteed” in UI copy.

## Anti-references

Avoid oversized landing-page hero layouts, decorative glass panels, generic SaaS gradients, and low-density card grids. Avoid hiding launch-critical settings behind vague labels. Avoid dark-pattern “guaranteed pass” claims.

## Design Principles

1. Make the current operational state obvious: installed, missing, running, failed, stopped, **engine**, risk hints.
2. Keep launch parameters explicit and editable without requiring code changes.
3. Prefer compact panels, predictable forms, and clear action states over visual novelty.
4. Treat logs as first-class output because launch failures are common during browser setup.
5. Keep the GUI usable even before a given engine runtime is installed.
6. Keep secrets local: DPAPI / encrypted backups; never ship cloud credentials in the package.
7. Separate **engine** (camoufox vs chromium) from **mode** (browser vs server); isolate user-data dirs per engine.
8. Surface environment consistency (proxy ↔ geo/timezone/locale, WebRTC) before high-risk launches.

## Accessibility & Inclusion

Target WCAG AA contrast, keyboard-accessible controls, visible focus states, reduced-motion support, and non-color-only status indicators.

## Out of scope

- Multi-tenant **cloud control** / remote fleet orchestration
- **Guaranteed** anti-detect, AI signup/subscribe, or payment pass rates (no SLA in the open product)
- Bulk account abuse, credential stuffing, or payment/card bypass tooling
- Embedding third-party API tokens or commercial license keys in the repository or default installer
- Default **OEM of closed-source commercial fingerprint browsers** (R5) unless a separate licensed product line is created
- Attack tooling aimed at bypassing specific banks/card networks

## In scope (roadmap)

- Dual-engine profiles and workers (Camoufox + Chromium stack)
- Professional fingerprint/consistency configuration (L2)
- Anti-automation patch stack evaluation and integration (L3 entry / Phase C)
- **Deep Chromium alignment (Phase D / R4)** when benchmarks require it
- Local benchmark hooks and honest risk reporting
