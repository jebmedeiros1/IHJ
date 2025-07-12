# IHJ React + FastAPI

This is a minimal example showing how to replace the original Streamlit app with a
FastAPI backend and a React frontend.

## Backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend

The frontend uses Vite + React. To run it you'll need Node.js installed.

```
cd frontend
npm install
npm run start
```

Both services assume the PostgreSQL database configuration from the previous
Streamlit version. Adjust environment variables `DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER` and `DB_PASS` if necessary.
