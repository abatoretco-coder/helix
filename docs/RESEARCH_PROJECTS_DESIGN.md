# Research Projects Design

## Goal

Attach curated streams of articles to long-running research initiatives.

## Config file

- Path: `config/research_projects.yaml`
- Fields:
  - `projects[].name`
  - `projects[].description`
  - `projects[].topics`
  - `projects[].watch_entities`

## Runtime behavior

- Map article category/entities to projects.
- Expose project-oriented slices in API and dashboard operations later.
- Keep v1 as documentation and config scaffolding first.
