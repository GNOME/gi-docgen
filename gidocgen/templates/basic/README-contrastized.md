<!--
SPDX-FileCopyrightText: 2024 FeRD (Frank Dana) <ferdnyc@gmail.com>
SPDX-License-Identifier: MIT
-->

# Contrastized Light and Contrastized Dark

The "Contrastized" themes
(`contrastized-light.css` and `contrastized-dark.css`)
are contrast-enhanced remixes of the corresponding Solarized themes.
Solarized is a relatively low-contrast theme,
falling well below modern accessibility standards for readability.

## WCAG AAA contrast fixes

All theme colors have been adjusted
to meet the W3C Web Content Accessibility Group (WCAG)
AAA standard for color contrast,
with a minimum 7.0 contrast ratio between the foreground and background.

## Modernization

All static color values have been replaced
with CSS custom property references (using the `var(...)` syntax).
Properties named with the prefix `--pyg-`
are set on the `:root` element
to define color values referenced in the style rules.

As a result, both variations have identical style rules;
they differ only in the color values assigned to the custom properties.

(The theme variations could even be made auto-selecting
via media queries on `prefers-color-scheme`.)

## License

### Solarized

Copyright 2014 John Louis Del Rosario, Hank Gay, John Mastro, Brandon Bennett.
Used under the terms of the MIT license.

### Contrastized

Copyright 2024 FeRD (Frank Dana).
Released under the same terms as the source themes (MIT license).
