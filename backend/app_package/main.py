# app_package/main.py
"""
TrueTag API - Blockchain-backed product authentication platform.

Initializes the FastAPI application, mounts static file serving,
and registers routers. Database migration is handled via Alembic.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import auth, products, tags, dashboard, users, verify

app = FastAPI(
    title="TrueTag API",
    description="Blockchain-backed product authentication platform",
    version="1.0.0"
)

# NOTE: For production, a dedicated web server like Nginx or a CDN
# should serve static files to improve performance and security.
app.mount("/statics", StaticFiles(directory="statics"), name="static")

# Register API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(tags.router)
app.include_router(dashboard.router)
app.include_router(verify.router)

@app.get("/", tags=["Health Check"])
async def root() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Welcome message and API version.
    """
    return {
        "message": "Welcome to TrueTag API - Blockchain-backed product authentication",
        "version": "1.0.0"
    }

"""
truetag/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── versions/
├── app_package/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── batch.py
│   │   ├── password_reset_token.py
│   │   ├── product.py
│   │   ├── scan.py
│   │   ├── tag.py
│   │   ├── user.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   └── products.py
│   │   └── tags.py
│   │   └── users.py
│   │   └── verify.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── batch.py
│   │   ├── dashboard.py
│   │   ├── product.py
│   │   ├── scan.py
│   │   ├── tag.py
│   │   └── user.py
│   │   └── verification.py
│   ├── services/
│   │   ├── blockchain_service.py
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── oauth2.py
│   ├── utils.py
├── scripts/
│   ├── bulk_minter.py
├── statics/ # temporary fro holding pictures from the manufacturer
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
├── README.md
└── run_server.py
"""