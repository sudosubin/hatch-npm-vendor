# hatch-npm-vendor

[![version](https://badgen.net/github/release/sudosubin/hatch-npm-vendor?label=version)](https://github.com/sudosubin/hatch-npm-vendor/releases)
[![license](https://badgen.net/github/license/sudosubin/hatch-npm-vendor?color=green)](LICENSE)

Hatchling build hook that downloads pinned npm packages (with Subresource Integrity
checks) into `node_modules` and includes them in wheels via `force_include`.

## Usage

```toml
[build-system]
requires = ["hatchling>=1.27", "hatch-npm-vendor"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.npm-vendor]
dependencies = ["hatch-npm-vendor"]

[[tool.hatch.build.targets.wheel.hooks.npm-vendor.packages]]
dest = "my_pkg/assets/node_modules/some-npm-package"
package = "some-npm-package"
version = "1.2.3"
integrity = "sha512-…"

# Additional packages (any destination you like):
[[tool.hatch.build.targets.wheel.hooks.npm-vendor.packages]]
dest = "my_pkg/assets/vendor/another-package"
package = "another-package"
version = "4.5.6"
integrity = "sha512-…"
```

| Option | Default | Description |
| --- | --- | --- |
| `packages` | (required) | Array of tables, one per npm package (at least one). |
| `src` | `"src"` | Project source root; each `dest` is relative to it. |
| `registry` | `https://registry.npmjs.org` | npm registry base URL. |

Each `packages` entry (all fields required):

- `dest`: directory, relative to `src`, that the package is extracted into
  (replaced on every build) and shipped at the same path in the wheel.
- `package`, `version`: the npm package to fetch.
- `integrity`: the `sha512-…` value from the registry
  (`npm view <package>@<version> dist.integrity`).

Set `HATCH_NPM_VENDOR_SKIP=1` to skip vendoring (e.g. sdist-only workflows).

## Development

```sh
prek install
uv sync
uv run pytest
uv build
```

## Releasing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
(checked by the `commitizen` hook in `prek.toml`; run `prek install` once).

```sh
uv run cz bump              # bump version, update CHANGELOG.md, commit and tag
git push --follow-tags      # the v* tag triggers the Release workflow
```

The Release workflow publishes to PyPI and creates a GitHub Release whose body
is the matching `CHANGELOG.md` section.
