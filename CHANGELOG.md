# Obsidian to typst changelog

## 0.2.5

### Fixes

1. Embed every page of a PDF, instead of only the first page

## 0.2.4

### Features

1. Support linking to a heading by name with `[[#Heading Name]]`

### Fixes

1. Support hyphens in embedded file names
2. Fix wikilinks being mangled when followed by a markdown link on the same line
3. Fix embedded files' labels attaching to the wrong (preceding) heading, causing duplicate-label warnings when the preceding heading is also labelled

## 0.2.3

### Features

1. Support embedding PDFs in obsidian documents

## 0.1.3

### Fixes

1. Fix issue with building mermaid docs when run as root (as in a Docker container)

## 0.1.2

### Features

1. Allow embedding images within a line

### Fixes

1. Code lines starting with `#` are not modified

## 0.1.0

### New Features

1. Can convert some simple markdown files to typst and pdfs

### Fixes

1. None, no bugs in previous release (based on https://github.com/kelseyhightower/nocode)
