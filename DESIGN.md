# Design

## Register

product

## Theme

Operational desktop control surface. The user is managing local browser state while reading logs and configuration fields, usually in a developer workstation or server admin context. Use a restrained light theme with sharp hierarchy and a moss-green primary accent.

## Tokens

```css
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(0.975 0.004 160);
  --surface-strong: oklch(0.94 0.008 160);
  --ink: oklch(0.19 0.018 160);
  --muted: oklch(0.43 0.018 160);
  --subtle: oklch(0.69 0.012 160);
  --line: oklch(0.88 0.01 160);
  --primary: oklch(0.47 0.13 160);
  --primary-hover: oklch(0.41 0.13 160);
  --accent: oklch(0.56 0.16 35);
  --danger: oklch(0.55 0.17 28);
  --warning: oklch(0.72 0.16 75);
  --success: oklch(0.54 0.13 150);
  --focus: oklch(0.7 0.14 160);
}
```

## Typography

Use system UI fonts. Keep scale compact: 12px labels, 14px body, 16px emphasized body, 20-24px page headings. Do not use display fonts for controls.

## Components

Use a fixed top bar, left navigation rail, compact panels, data rows, native form controls, icon buttons with labels where action risk is high, and log panes with monospace text. Buttons have default, hover, focus, disabled, loading, and destructive states.

## Motion

Keep transitions to 150-200ms for hover/focus/state changes. Respect `prefers-reduced-motion`.
