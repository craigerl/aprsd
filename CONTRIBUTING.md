# CONTRIBUTING

Code contributions are welcomed and appreciated. Just submit a PR!

The current build environment uses `pre-commit`, and `uv`.

### Environment setup:

```console
pip install uv
uv venv
uv pip install pip-tools
git clone git@github.com:craigerl/aprsd.git
cd aprsd
pre-commit install

# Optionally run the pre-commit scripts at any time
pre-commit run --all-files
```

### Running and testing:

From the aprstastic directory:

```console
cd aprsd
uv pip install -e .

# Running
uv run aprsd
```
