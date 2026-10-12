# AJ’s Academy

A private, single-family Streamlit learning hub with nine sections and a separate parent portal.

## Academy implementation

- Main app: `artifacts/ajs-academy/app.py`; visual layer: `visuals.py`; persistence: `store.py`; account calculations: `finance.py`; public-source/AI access: `content.py`; sourced college budgets: `schools.py`.
- Managed workflow: `artifacts/ajs-academy: web`; command `pnpm --filter @workspace/ajs-academy run dev`. The registered web artifact runs Python Streamlit, not the unused React scaffold.
- Python dependencies are managed in root `pyproject.toml` and `uv.lock`. Use the configured Python toolchain.
- Academy uses PostgreSQL directly through psycopg. `artifacts/ajs-academy/schema.sql` is the schema source; apply deliberately before running against a new database. Do not use Drizzle schema push to manage these tables.
- Parent access uses `PARENT_PASSWORD`. The welcome page previews all nine sections; “Let’s Begin” opens the existing family child view without a password, by the parent's explicit choice. Anyone able to reach the app can enter that view; it is not an anonymized demo. Parent controls remain protected; parents can hand off using “Switch to AJ’s view.” Sessions expire after 30 minutes without interaction.
- Private uploads use App Storage; binary data never goes into PostgreSQL. Structured family state is stored in a transactionally locked JSONB document.
- Imported financial history currently exists in the development database only. Do not assume publishing copies it; verify schema and reimport through the parent portal in a new environment.
- Current iteration does not claim reconciled portfolio performance: transaction net quantities are provisional. It supports public market-price history, contributions, and savings planning. Live LEGO prices/deal comparisons and automatic LinkedIn monitoring are not connected.
- University budgets have dated sources and editable assumptions; amounts are not live quotes. Public news and YouTube require parent supervision/review. AI stories require parent approval and voice transcription is opt-in.
- Unit/render checks use Streamlit AppTest; do not add production auth bypasses for screenshots.

## Other workspace services

The pnpm workspace retains its original Express API and component-preview sandbox.
They are separate from the Academy's Streamlit service. Python persistence does not
use the scaffold's generated API client or Drizzle schema.

## Checks

- `python -m compileall -q artifacts/ajs-academy`
- `pnpm --filter @workspace/ajs-academy run build`
- Streamlit AppTest can render authenticated views in an isolated test context;
  keep role injection in tests only, never in app routes.
