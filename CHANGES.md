# Changes

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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
