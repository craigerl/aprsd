# CONTRIBUTING

Code contributions are welcomed and appreciated. Just submit a PR!

The current build environment uses `pre-commit`, and `uv`.

### Environment setup:

```console
pip install uv
git clone git@github.com:craigerl/aprsd.git
cd aprsd
uv venv
uv pip install -e ".[dev]"
uv run pre-commit install

# Optionally run the pre-commit scripts at any time
uv run pre-commit run --all-files
```

### Running and testing:

From the aprsd directory:

```console
# Running
uv run aprsd

# Testing
uv run pytest tests

# Full matrix (lint + all supported Python versions)
uv run tox
```
