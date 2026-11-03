"""Créer les tables et appliquer l’évolution additive de l’historique privé."""
from sqlalchemy import inspect, text
from app.database import Base, engine
from app.models.analysis import Analysis  # noqa: F401
from app.models.user import MagicLink, User, UserSession  # noqa: F401


def main() -> None:
    with engine.begin() as connection:
        # Sérialise deux démarrages ; la transaction annule tout en cas d’échec.
        connection.execute(text("SELECT pg_advisory_xact_lock(673519024)"))
        Base.metadata.create_all(bind=connection)
        connection.execute(text("""
            ALTER TABLE analyses
                ADD COLUMN IF NOT EXISTS guest_hash VARCHAR(64),
                ADD COLUMN IF NOT EXISTS claim_email VARCHAR(254),
                ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id),
                ADD COLUMN IF NOT EXISTS corrected_csv BYTEA,
                ADD COLUMN IF NOT EXISTS correction_key VARCHAR(36),
                ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP WITH TIME ZONE
        """))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_analyses_user_id ON analyses(user_id)"
        ))
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP WITH TIME ZONE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_analyses_guest_hash ON analyses(guest_hash)"))
        print("Base prête. Tables :", inspect(connection).get_table_names())


if __name__ == "__main__":
    main()
