"""Create the application's database tables."""

from sqlalchemy import inspect

from app.database import engine
from app.models.analysis import Analysis


def main() -> None:
    Analysis.metadata.create_all(bind=engine)
    print("Database ready. Tables:", inspect(engine).get_table_names())


if __name__ == "__main__":
    main()