# AGENTS.md

Flask + Vue3 web automation testing platform: manage test cases/elements/variables/tasks in a Vue UI, execute them via Playwright from a Flask backend, and view reports.

For full architecture, data flow, API routes, and module details, see [项目架构文档.md](项目架构文档.md). For the variable scoping model (env + project uniqueness), see [变量管理功能说明.md](变量管理功能说明.md).

## Run & Build

- Backend (dev): `cd backend && python app.py` — Flask serves on port `8081` (see [start.sh](start.sh), which activates `venv/` first).
- Frontend (dev): `cd frontend && npm run dev` — Vite dev server proxies `/api` and `/screenshots` to `http://localhost:8081` (see [vite.config.js](frontend/vite.config.js)).
- Frontend (build): `cd frontend && npm run build` — outputs to `frontend/dist`, which Flask serves as static files in production (`app = Flask(__name__, static_folder="../frontend/dist")` in [app.py](backend/app.py)).
- Full deploy: [deploy.sh](deploy.sh) (npm install + build, create venv, `pip install -r requirements.txt`, `playwright install`).
- Stop background server: [stop.sh](stop.sh) uses `backend/server.pid`.
- No automated test suite exists yet (`test_executor.py` is the Playwright execution engine, not a test file) — verify changes manually by running a test case through the UI.

## Backend conventions (`backend/`)

- All persistent app data lives in flat JSON files in `backend/` (`data.json`, `elements.json`, `reports.json`, `tasks.json`, `variables.json`, `variables_config.json`, `projects.json`, `environments.json`, `databases.json`, `settings.json`) — there is no ORM/migrations for app data. Follow the existing `load_*`/`save_*` function pattern per file when adding fields.
- External MySQL/PostgreSQL databases (configured in `databases.json`) are only used for the `database`-type variable lookups, not for app storage.
- Test execution writes a temporary report with `status: "executing"` immediately, then overwrites the same report `id` with the final result — preserve this pattern so the frontend can poll in-progress runs.
- Logging goes through the module-level `logger` (`logging.getLogger("flask_api")`), configured to write to both console and `app.log`. Use `logger.info/error`, not `print`.
- Variable references in test steps use `${varName}` syntax, resolved via `TestExecutor.resolve_variable` (supports nested refs).

## Frontend conventions (`frontend/`)

- Vue 3 with Naive UI (`n-*` components) and Chinese UI text — match existing component style/language.
- Routes are registered in [router/index.ts](frontend/src/router/index.ts); one top-level component per route under `src/components/`.
- API calls go through Axios directly to `/api/...`; rely on the Vite dev proxy (port 8081) rather than hardcoding backend URLs.
