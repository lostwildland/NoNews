"""Declared public source files permitted in the managed processing payload."""

BACKEND_SOURCES = (
    '__init__.py', 'causes.py', 'content_store.py', 'core.py', 'delivery.py',
    'feed_settings.py', 'folders.py', 'job_stream.py', 'jobs.py',
    'legacy_content_migration.py', 'literature.py', 'literature_mapping.py',
    'media_jobs.py', 'media_raw_activation.py', 'media_store.py', 'news_media.py',
    'pipeline.py', 'projection.py', 'reading_notes.py', 'reconciliation.py',
    'reject_cleanup.py', 'reject_media_cleanup.py', 'schema.py',
    'schema_semantics.py', 'server.py', 'service.py', 'settings.py', 'zotero.py',
)
ROOT_SOURCES = ('stdio_service.py', 'PROVENANCE.md', 'JOBS-IPC.md', 'requirements.lock')
