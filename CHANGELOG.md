# Changelog

## [1.1.1] - 2026-05-22

### Fixed
- Image references broken in 21 chapters (43–53, 69–80) due to bold-wrapped `**![][imageN]**` tags resolving to bare paths without `![]()` syntax

## [1.1.0] - 2026-05-22

### Changed
- Re-extracted all chapters from updated source file (`anjaneya-2-print.md`)
- Chapter content expanded significantly (e.g. chapter 41: 145 → 413 lines) with new sub-sections
- Chapters now start directly with the chapter title — book title header removed
- Heading formatting cleaned: removed anchor IDs, bold markers, and escaped characters
- Images extracted from source and referenced as `../images/chapter-XX.png`
- Page break (`<div style="page-break-after: always;">`) added after chapter cover page (image + sub-topic list)

## [1.0.0] - 2026-05-20

### Added
- Foreword and chapters 41–80 of ఆంజనేయముపాస్మహే ద్వితీయ భాగము as individual markdown files
- README with book description, attribution, and chapter index
