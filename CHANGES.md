# Changes

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [2025.5] - 2025-10-11

### Fixed

- Make sure to escape query strings [#228]

## [2025.4] - 2025-07-02

### Added

- Add online attribute for devhelp index [#204]
- Include type data in the field template [!250]

### Fixed

- Use normal font size for enumeration values description [#218]

## [2025.1] - 2025-02-28

### Added

- Add layout for tablet portrait mode [#95]
- Support static virtual methods [#211]

### Changed

- Don't generate classes hierarchy if not needed [!220]
- Improve copy buttons on narrow layouts [#91]

### Fixed

- Only consider dot data processing fail if dot returns non-zero [#188]
- Show non-standard instance parameters [#202]
- Fix C declaration of structure fields [#210]

## [2024.1] - 2024-05-20

### Added

- Add unit testing for link syntax
- Support link to enumeration members [!214, !215]
- Add favicon support [#152]
- Add proper anchor for enum members [#183]
- Parse optional anchors in links [#191]
- Generate a link to finish functions [#189]
- Add 'inline' to C declarations for inline callables [#173]
- Make the logo a link to the index [#195]
- Clear search when pressing Escape [#194]

### Changed

- Update the wording for transfer modes [!205]
- Turn deprecation notices into admonitions [#155]
- Improve filesystem string type docs [#193]

### Fixed

- Fix doubled paragraph tags around descriptions [!206]
- Append period after last line in more cases [#181]
- Documentation fixes [!223, #198]
- Use the basename of the urlmap file [#197]

### Removed

- Revert "generate: Add fallback for missing "since"" [#179]

## [2023.3] - 2023-11-25

### Fixed

- Add missing dependency [#175]
- Add missing test data to the source archive [#174]

## [2023.2] - 2023-11-24

### Added

- Use packaging module to properly compare versions
- Add "implements" in class definition pseudocode
- Ignore the first class instance struct field
- Parse default-value attribute [#103]
- Test the gtk-doc sigil parsing
- Support admonitions in docblocks [#170]
- Add link to the extra content files location in the source repository [#118]
- Search for GIR XML in `$GI_GIR_PATH` and `/usr/share/gir-1.0` [!196]
- Add fallback for missing "since" [!198]

### Changed

- Redesign the search results
- Redesign the index for enumeration types

### Fixed

- Match dependencies list in the index and sidebar [!177]
- Use KeyboardEvent.key to focus search input [#151]
- Build fixes for subproject use [!185]
- Remove display:flex from headings [#147]
- Split transfer notes based on direction [#141]
- Clarify signal flags [!189]
- Hide build section if empty [#160]
- Always explicitely use utf-8 when reading/writing files [!193]
- use `color-scheme: dark` when in dark mode [!188]

## [2023.1] - 2023-01-06

### Added

- Use tomlib for Python >= 3.11 and tomli/toml for Python < 3.11 [!168, !172]

### Fixed

- Use the proper link fragment for interface prerequisite [#148]
