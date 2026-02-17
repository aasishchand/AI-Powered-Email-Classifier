# Google OAuth & Gmail API Setup

This app supports **Sign in with Gmail** and syncs emails via the Gmail API (no 16-character app password required).

## 1. Google Cloud Console Setup

### Create a project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Note the project name (used for OAuth consent screen).

### Enable APIs

1. In the left menu go to **APIs & Services** → **Library**.
2. Search for **Gmail API** and click **Enable**.
3. Search for **Google People API** (or ensure **Google+ API** / userinfo is available) for profile/email — usually enabled with OAuth.

### Configure OAuth consent screen

1. Go to **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (or Internal for workspace-only).
3. Fill in **App name**, **User support email**, **Developer contact**.
4. Under **Scopes**, add:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `.../auth/gmail.readonly`
   - `.../auth/gmail.modify`
5. Save and continue. Add test users if the app is in "Testing" mode.

### Create OAuth 2.0 credentials

1. Go to **APIs & Services** → **Credentials**.
2. Click **Create credentials** → **OAuth client ID**.
3. Application type: **Web application**.
4. Name: e.g. "Email Dashboard".
5. **Authorized JavaScript origins** (optional for backend-only flow):
   - `http://localhost:5173`
   - Your production frontend URL.
6. **Authorized redirect URIs** (required):
   - `http://localhost:8000/api/v1/auth/google/callback`
   - For production: `https://your-api-domain.com/api/v1/auth/google/callback`
7. Create and copy the **Client ID** and **Client secret**.

## 2. Environment variables

In `email-api/.env` (or your deployment env):

```env
# Google OAuth (Gmail API – no app password)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# URLs (must match redirect URI and frontend)
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# Optional: encrypt OAuth tokens at rest (recommended in production)
# MAILBOX_ENCRYPTION_KEY=your-32-char-base64-key
```

- **BACKEND_URL**: Base URL of this API (used to build the Google redirect URI).
- **FRONTEND_URL**: Where to send the user after login (with `?token=...`).

## 3. Database schema (OAuth tokens)

OAuth tokens are stored in the `user_oauth` table (created automatically on startup):

| Column                   | Type        | Description                          |
|--------------------------|-------------|--------------------------------------|
| id                       | INTEGER     | Primary key                          |
| user_id                  | VARCHAR(36) | FK to users.id                       |
| provider                 | VARCHAR(50) | e.g. `google`                        |
| access_token_encrypted  | TEXT        | Encrypted access token               |
| refresh_token_encrypted  | TEXT        | Encrypted refresh token (nullable)   |
| expires_at              | TIMESTAMP   | Access token expiry                  |
| scopes                   | VARCHAR(512)| Optional scope list                  |
| created_at / updated_at  | TIMESTAMP   | Audit fields                         |

- Tokens are encrypted with Fernet (see `app.core.encryption`).
- Access tokens are refreshed automatically when expired using the refresh token.

## 4. Flow summary

1. User clicks **Sign in with Gmail** → frontend redirects to `GET /api/v1/auth/google`.
2. Backend redirects to Google consent with scopes: `openid`, `userinfo.email`, `userinfo.profile`, `gmail.readonly`, `gmail.modify`.
3. User signs in and approves → Google redirects to `GET /api/v1/auth/google/callback?code=...`.
4. Backend exchanges `code` for access + refresh tokens, fetches profile (email, name), creates or finds user, **stores encrypted tokens** in `user_oauth`, returns JWT and redirects to frontend with `?token=JWT`.
5. Frontend stores JWT and calls `POST /api/v1/emails/sync` to sync inbox via Gmail API.
6. Emails are listed from `GET /api/v1/emails/` (from synced data). Token refresh is handled in backend when calling Gmail API.

## 5. Security notes

- **HTTPS**: Use HTTPS in production for backend and frontend.
- **Encryption**: Set `MAILBOX_ENCRYPTION_KEY` in production (32-byte key, base64).
- **CORS**: Restrict `ALLOWED_ORIGINS` to your frontend origin(s).
- **Session**: JWT is used for API auth; OAuth tokens are only on the server and encrypted at rest.
