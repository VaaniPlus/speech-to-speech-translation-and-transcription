# Backend

The backend is a standalone Python 3.11 uv project. Install uv, then start the
API from this directory:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Authentication uses PostgreSQL. From the repository root, start the local
database before using the auth endpoints:

```powershell
docker compose up -d postgres
```

Copy `.env.example` to `.env` and set a random `JWT_SECRET_KEY` before sharing
the API outside local development. The default database URL matches the
included Docker Compose service.

The first authentication request seeds a local demo account using
`DEFAULT_USER_EMAIL` and `DEFAULT_USER_PASSWORD` (defaults are
`proindra@example.com` and `VaaniProindra#2026`). These are development-only
credentials; change them in `.env` before using a non-demo environment.

The API provides registration and login, plus `GET /api/auth/me` for the
current bearer-token account. Authenticated requests to `POST /api/translate`
and `POST /api/speech-translate` save source text, translation, and direction
to that user's history. `GET /api/conversions/history` returns the newest five
conversions for the signed-in user. Requests without a token remain usable but
do not save history. See the [API guide](../docs/api.md) for request details.

`uv run` creates and syncs the project environment automatically. Run the tests
from `backend/` with:

```powershell
uv run pytest
```

Mock providers are the default and do not load model packages or download
weights. To install optional local inference dependencies, sync the `ml` extra:

```powershell
uv sync --extra ml
```

Real providers may download model weights on first use. Configure the backend
with environment variables or `backend/.env`. To create the local configuration:

```powershell
Copy-Item .env.example .env
```

For Windows model setup and provider options, see the
[Windows setup guide](../docs/windows-setup.md).
