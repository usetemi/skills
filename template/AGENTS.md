# template/

Copier template that renders shared modules into the google-* skills under `skills/`. The skill template (`SKILL.md`) lives here too as the starting scaffold for new skills, but it's unrelated to Copier.

Currently templated: `__init__.py`, `__main__.py`, `auth.py` (only when `uses_oauth: true`). `config.py` and the planned shared `common.py` / `doctor_helpers.py` are out of scope for now and live hand-written in each skill.

## Layout

```
template/
  copier.yml                            # Copier config + variables
  {{ _copier_conf.answers_file }}.jinja # Renders the per-skill .copier-answers.yml
  src/{{ pkg }}/
    __init__.py.jinja
    __main__.py.jinja
    auth.py.jinja                       # Skipped when uses_oauth is false
  bootstraps/                           # Per-skill substitution data, used at first copy
    ga4.yml
    gsc.yml
    gdrive.yml
```

Each consuming skill keeps a `.copier-answers.yml` at its root recording which template version was used and what variable values were supplied. `copier update` reads it and re-renders.

## Variables

| Variable | Type | Purpose |
| --- | --- | --- |
| `pkg` | str | Python package name (`ga4`). Used in import paths and the `src/<pkg>/` directory name. |
| `cmd` | str | CLI entry command (`ga4`). Almost always equal to `pkg`; exposed as a separate variable in case a skill ever needs them to differ. |
| `config_dir_name` | str | Subdirectory under `~/.config/skills/` for this skill's state. |
| `env_var_config_dir` | str | Env var override for the config dir (e.g. `GA4_CONFIG_DIR`). |
| `description` | str | One-line description used in module docstrings. |
| `uses_oauth` | bool | Skip `auth.py` if false (e.g. gdrive uses rclone, not the Google OAuth Desktop flow). |
| `default_oauth_port` | int | Local port for the OAuth callback. Must differ between skills running concurrently. |
| `scopes_block` | str (multiline) | Verbatim Python block defining `SCOPE_*` constants and `DEFAULT_LOGIN_SCOPES`. Inlined into `auth.py`. |
| `default_credential_scope` | str | Name of the `SCOPE_*` constant used as the read-only default in `get_credentials()` and `whoami` (e.g. `SCOPE_READONLY`). |
| `login_default_help` | str | Help text suffix for the `--scope` flag's default value. |
| `auth_module_extras` | str (multiline) | Optional extra paragraphs appended to `auth.py`'s module docstring. Use for skill-specific notes (e.g. ga4's ADC paragraph). |

## Constraint: no skill-name branching

Templates contain only Python + `{{ variable }}` substitutions. **Never** write `{% if pkg == 'ga4' %}` or any other skill-name-aware branching. Variation that doesn't fit a single rendered shape goes into a substitution variable (e.g. `scopes_block` is verbatim Python that ga4 and gsc each fill in differently).

If new variation can't be expressed via a substitution, the right move is usually to leave that file out of the template and let each skill carry its own copy.

## Authoring workflow

1. Edit a `.jinja` template under `src/{{ pkg }}/`.
2. From each consuming skill's directory, run `copier update --defaults --trust`. Variables come from the skill's `.copier-answers.yml`.
3. `git diff` shows the propagated change. Commit the template change and the regenerated outputs together.

CI runs the same `copier update --defaults --trust` per skill on every PR that touches `template/**` or `skills/**`; non-empty `git diff` after the run fails the check (`copier-drift.yml`).

## Adding a new templated module

1. Drop a new `.jinja` file in `src/{{ pkg }}/`.
2. If it should be skipped for some skills, add an `_exclude` entry in `copier.yml` — match against the rendered (post-Jinja) destination path, not the `.jinja` source path. Patterns are themselves Jinja-rendered, so `"{% if not uses_oauth %}src/{{ pkg }}/auth.py{% endif %}"` works.
3. Run `copier update --defaults --trust` in each skill that should consume it; add a `.copier-answers.yml` if the skill is brand new.

## Adding a new skill

1. Write `bootstraps/<name>.yml` with the substitutions for that skill.
2. From the skill's destination dir, run:
   ```
   copier copy --data-file ../../template/bootstraps/<name>.yml --trust --defaults --overwrite ../../template .
   ```
   The relative `../../template` source path keeps the recorded `_src_path` portable across machines.
3. Register the new skill in `.claude-plugin/marketplace.json` and `README.md` per the top-level AGENTS.md.

## Bumping copier itself

Copier is installed via `uv tool install copier` (or `pipx install copier`); the CI workflow uses `pipx install copier`. There's no pin — the template should stay compatible with current Copier. If a template feature requires a minimum Copier version, set `_min_copier_version` in `copier.yml`.
