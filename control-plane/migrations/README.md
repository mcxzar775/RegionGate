# Alembic migrations

For production use Alembic. Dev bootstrap currently uses `Base.metadata.create_all` in app lifespan.

```bash
# Initialize (once)
alembic init -t async migrations_alembic

# Generate after model changes
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Tables defined in `app/models.py` match project brief section 10.
