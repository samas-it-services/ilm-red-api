# ILM Red Sample Data

**Source**: Azure PostgreSQL Production Database
**Exported**: 2026-01-12T00:00:15.663297
**Host**: ilmred-prod-postgres.postgres.database.azure.com

## Data Sanitization

All sensitive data has been sanitized:
- Emails: Replaced with @test.com addresses
- Passwords: All reset to hashed "test123"
- Display names: Anonymized for users with real-looking names
- Extra data: Removed

## Files

- `books.json` - 50 books (various categories, visibility)
- `users.json` - 20 sanitized users (various roles)
- `ratings.json` - 2 book ratings
- `favorites.json` - 11 favorite books
- `chat_sessions.json` - 5 AI chat sessions
- `chat_messages.json` - 0 chat messages
- `page_images.json` - 0 page images (5 books)

## Usage

Import this data to your local database using:

```bash
python scripts/import_sample_data.py
```

## Test Credentials

All users have password: `test123`

Example users:
- Admin user: Check users.json for role='super_admin'
- Regular users: Check users.json for role='user'
