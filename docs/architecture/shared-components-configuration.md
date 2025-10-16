# Shared Components & Configuration

## Shared Libraries
- `.bmad-core/` templates + tasks ensure consistent agent behavior.  
- `framework/` exposes reusable base agent classes for Python.  
- TypeScript `types/core.ts` standardizes data contracts for CLI.

## Configuration Management
- `.env` for local; `.env.example` recommended (create).  
- `config/config.py` centralizes Python config (feature flags, tokens).  
- TypeScript uses `dotenv` in CLI; environment variables required before run.  
- Secrets pulled via AWS Secrets Manager in prod.

## Feature Flags
- `FEATURES` dictionary (Python) for gating features (e.g., `email_integration`).  
- `FC_PREVIEW_MODE` env var toggles CLI preview vs auto-create.  
- Plan: unify via LaunchDarkly or simple database-driven flags.
