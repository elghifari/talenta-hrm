---
name: Talenta HRIS
description: Persistent-sidebar employee administration, selected direction A
colors:
  navigation: "#163049"
  navigation-active: "#2b435a"
  navigation-text: "#d1dce6"
  primary: "#315a85"
  primary-hover: "#25476a"
  ground: "#f7f9fb"
  surface: "#ffffff"
  text: "#202630"
  secondary-text: "#526171"
  record-border: "#cbd4dd"
  control-border: "#77818c"
  focus: "#93601e"
  error: "#94332a"
  success-text: "#235637"
  success-ground: "#eef6f0"
typography:
  body:
    fontFamily: '"Segoe UI", Arial, sans-serif'
    lineHeight: 1.55
  heading:
    fontSize: "1.65rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.035em"
  label:
    fontSize: "0.85rem"
    fontWeight: 600
rounded:
  control: "5px"
  input: "4px"
spacing:
  compact: "12px"
  standard: "18px"
  record: "26px"
  desktop: "36px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.surface}"
---

# Talenta HRIS design system

## Overview

Direction A was selected through the HRIS shell study. The implemented interface uses a persistent navy sidebar, a compact account header and light employee-record surfaces. It serves repetitive HR record administration and scoped manager reads. ENERGY 1 / RHYTHM 1 / MOTION 1.

This records the implemented application, not an existing corporate brand identity. Product name is text; there are no generated brand assets.

## Colors

Navy anchors module navigation. Blue marks the primary record action. Light neutral surfaces keep names and text identifiers dominant. Error/success feedback includes explicit language and never relies on color alone. Color values above come from `frontend/src/styles.css`.

## Typography

Use the implemented system sans stack for office-record readability without a font download. Employee codes remain text and use tabular numerals. Long names and codes wrap; headings do not become decorative display type. Table text is 0.875rem; secondary text is at least 0.75rem.

## Layout

Desktop uses a 224px sidebar, 76px minimum account header and 36px content padding. Below 1000px, sidebar narrows to 190px and padding reduces. Below 680px, a labeled Menu replaces persistent navigation, records stack and forms remain single-column. Account identity and logout stay available. The content maximum is 1320px.

Personnel is the only working module in this slice. Approved future labels are Attendance, Payroll, Recruitment and Settings, with Applicants inside Recruitment. Do not ship dead links to anticipated modules.

## Elevation & Depth

Records sit flat on the working ground. Borders and tonal surfaces separate navigation, header, rows and forms. No card shadows, glow or glass effects are used.

## Shapes

Controls and record surfaces use modest corners. Inputs are not pills. Interactive controls meet a 44px minimum target; focus uses a visible 3px outline with a 3px offset. The asynchronously loaded record title receives programmatic focus.

## Components

Dedicated list/detail/create/edit routes preserve orientation and reload behavior. Primary actions use explicit labels; employee names are links. The form associates errors with fields, announces outcomes and confirms dirty navigation. Managers have read-only presentation; the server remains authoritative. Login stands alone without authenticated chrome.

## Do's and Don'ts

- Keep code/name as the current employee fields and preserve leading zeros.
- Keep English module names and the selected Indonesian task language.
- Retain loading, empty, error, denied, expiry and uncertain-save states.
- Do not invent metrics, salaries, units, profile photos or future actions to fill the page.
- Do not add a second sidebar, modal-led editing or a new visual world without a concrete approved requirement.
