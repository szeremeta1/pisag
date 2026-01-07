# Database Guide

## Schema Overview
- **pagers**: Pager directory with RIC address and metadata. Indexed on `ric_address`.
- **messages**: Outgoing messages with type, status, RF parameters, duration, and optional error text. Indexed on `timestamp` and `status`.
- **message_recipients**: Join table linking messages to pagers/addresses. Indexed on `message_id` and `pager_id`.
- **system_config**: Key/value store for runtime overrides. Unique index on `key`.
- **transmission_logs**: Timeline of message transmission stages. Indexed on `message_id` and `timestamp`.

Relationships:
- `pagers` 1—N `message_recipients`
- `messages` 1—N `message_recipients`
- `messages` 1—N `transmission_logs`

## Session Management Patterns
- Use `get_db_session()` context manager for scripts:
  ```python
  from pisag.models import get_db_session
  with get_db_session() as session:
      ...
  ```
- In Flask views, use `get_request_session()` from `pisag.utils.database` to reuse a request-scoped session. Sessions close automatically via app teardown.
- For background jobs, wrap functions with `@with_db_session` decorator.

## Migrations
- Alembic configured in project root. Apply migrations:
  ```bash
  alembic upgrade head
  ```
- Create new migration after model changes:
  ```bash
  alembic revision --autogenerate -m "describe change"
  ```
- Downgrade if needed:
  ```bash
  alembic downgrade -1
  ```

## Common ORM Queries
- Recent messages: `Message.get_recent(session, limit=10)`
- Messages by status: `Message.get_by_status(session, "queued")`
- Pager lookup: `Pager.find_by_ric(session, "0012345")`
- Config value: `SystemConfig.get_by_key(session, "frequency")`
- Transmission logs: `TransmissionLog.get_for_message(session, message_id)`

## Analytics Helpers
- `get_message_with_recipients(session, message_id)`
- `get_messages_by_date_range(session, start, end)`
- `get_pager_activity(session, pager_id)`
- `get_analytics_summary(session)` returns totals, success rate, and average duration.

## Troubleshooting
- If migrations fail, ensure `alembic.ini` `sqlalchemy.url` matches the configured database path.
- For SQLite locking issues, avoid long-running transactions and close sessions promptly.
- To inspect schema:
  ```bash
  sqlite3 pisag.db ".schema"
  sqlite3 pisag.db ".indexes"
  ```
