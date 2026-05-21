# template/

Directory-scoped guide for the Copier template that renders shared Python modules
into the google-* skills under `skills/`. Use the top-level `AGENTS.md` for general
repo workflow; load this file only when editing `template/**` or rendered modules
that come from this template.

## Scope

- `template/copier.yml` owns the current variables, exclusions, and Copier
  behavior. Check it directly instead of duplicating a variable index here.
- `src/{{ pkg }}/` contains the Jinja templates rendered into consuming skills.
- `bootstraps/` contains substitution data for first-time renders of new
  templated skills.
- Each consuming skill records its substitutions in `.copier-answers.yml`.

## Constraint: no skill-name branching

Templates contain only Python plus `{{ variable }}` substitutions. Never write
`{% if pkg == 'ga4' %}` or any other branch that knows a consuming skill by name.

Skill-specific variation should be expressed through substitution variables. If a
variation does not fit a common rendered shape, leave that file out of the
template and let each skill carry its own copy.

## Authoring workflow

1. Edit the relevant `.jinja` template under `src/{{ pkg }}/`.
2. From each affected consuming skill's directory, re-render using its recorded
   answers:
   ```bash
   copier copy --data-file .copier-answers.yml --defaults --trust --overwrite ../../template .
   ```
3. Review `git diff` and commit the template change with the regenerated outputs.

Use `copier copy --overwrite`, not `copier update`: `copier update` expects the
template to be a standalone Git repo, but this template lives inside the parent
repository.

## Adding a templated module

1. Add the new `.jinja` file under `src/{{ pkg }}/`.
2. If the module should be skipped for some skills, render the disabled filename
   to a hidden `.copier-skip-*` destination and rely on the static `_exclude`
   entry in `copier.yml`. Copier does not render `_exclude` patterns.
3. From each skill that should consume the module, run:
   ```bash
   copier copy --data-file .copier-answers.yml --defaults --trust --overwrite ../../template .
   ```

## Adding a new templated skill

1. Add `bootstraps/<name>.yml` with the substitutions for the new skill.
2. From the skill's destination directory, run:
   ```bash
   copier copy --data-file ../../template/bootstraps/<name>.yml --trust --defaults --overwrite ../../template .
   ```
   The relative `../../template` source path keeps the recorded `_src_path`
   portable across machines.
3. Register the skill in `.claude-plugin/marketplace.json` and `README.md` per the
   top-level `AGENTS.md`.

## Validation

- Re-render every affected skill that has a `.copier-answers.yml` file.
- If rendered Python changed, run:
  ```bash
  uv run --project skills/<skill> ruff check .
  uv run --project skills/<skill> ty check
  ```
- Run `git diff --check` before finishing.
