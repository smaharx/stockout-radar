# Contributing to Stockout Radar

Thank you for considering a contribution.

## Before making changes

1. Check existing issues and pull requests to avoid duplicate work.
2. Create a feature branch from the latest `main`.
3. Keep changes focused and explain their user or research value.
4. Do not commit datasets, database files, credentials, generated environments, build output or unrelated reports.
5. Preserve the original project/contributor attribution.

## Development setup

Follow the [README local development instructions](README.md#local-development).

## Quality gates

Before opening a pull request, run:

```bash
APP_ENV=local PYTHONPATH=src python -m pytest -q
python -m pip check

cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

Include the command results in the pull request description. Add or update tests when changing forecasting, API, database, authentication or inventory behaviour.

## Pull request expectations

A pull request should include:

- A concise summary and motivation.
- A list of changed areas.
- Tests/checks run and their result.
- Screenshots for visible frontend changes.
- Notes for environment-variable, database or deployment changes.
- Any known limitations, migration steps or rollback considerations.

Never include real `.env` contents, API keys, passwords, production database URLs, customer information or private deployment logs.

## Modelling and data changes

- Preserve chronological evaluation and embargo boundaries for multi-week targets.
- Avoid future leakage in feature engineering.
- Compare model changes with the current baseline and report aggregate as well as product-level performance.
- Document the data period, model artifact version, evaluation split and known limitations.
- Do not describe demand forecasting as observed stockout prediction unless appropriate stockout labels and validation data are introduced.
