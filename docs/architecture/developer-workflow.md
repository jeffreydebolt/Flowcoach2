# Developer Workflow

## Repo Standards
- Python formatting via `black`, lint with `flake8`.  
- TypeScript lint via `eslint`, format with `prettier`.  
- `pre-commit` hook recommended to run both.  
- Branch naming: `feature/<slug>`, `fix/<slug>`.

## Local Development
1. `pip install -r requirements.txt` & `npm install`.  
2. Copy `.env.example` ➜ `.env`, fill tokens (or mocks).  
3. Run Slack bot: `python app.py`.  
4. Run CLI: `npm run dev -- organize "<tasks>"`.  
5. Use `flowcoach.db` for local persistence; reset with `rm flowcoach.db` if needed.

## CI/CD Workflow
- GitHub Actions pipeline stages: `lint`, `test`, `build`, `package`, `deploy`.  
- Secrets stored in repo environment (use OpenID Connect -> AWS).  
- Require PR approval + status checks.

## Release Management
- Semantic versioning applied to CLI and Slack bot; tag repository on release.  
- Change log maintained in this architecture doc + `ROADMAP.md`.  
- Use feature flags for dark launches.
