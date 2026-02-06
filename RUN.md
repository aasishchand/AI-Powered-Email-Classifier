# Run the project (today / local)

## 1. Backend (Terminal 1)

**Important:** Run these commands from the project root (the folder that contains `email-api` and `faculty-email-dashboard`). If you get 404 on Settings → Connect mailbox, the backend was started without the mailbox routes — stop it (Ctrl+C) and start again.

```powershell
cd email-api
pip install -r requirements.txt
python -m scripts.seed_users
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

When the backend starts, you should see in the terminal: `Mailbox API loaded: /api/v1/mailbox/connect, ...` If you don't, the mailbox routes are not loaded; restart the backend.

## 2. Frontend (Terminal 2)

```powershell
cd faculty-email-dashboard
npm install
npm run dev
```

## 3. Open the app

- **URL:** http://localhost:5173/ (or the port Vite shows, e.g. 5174 if 5173 is in use)
- **Login:** `faculty@university.edu` / `faculty123` (or `admin@university.edu` / `admin123`)

## Notes

- Frontend `.env` is set to use `http://localhost:8000/api/v1` so API calls go to the backend.
- Backend uses SQLite by default (`email_platform.db` in `email-api`).
- For real-time mailbox: after login go to **Settings**, connect your Gmail/Outlook (use App Password for Gmail), then **Sync now**. Emails will appear on the **Emails** page.
