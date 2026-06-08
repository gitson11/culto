from src.database import initialize_database
from src.gui import CultoLouveAppManager
from src.logger import get_logger, setup_logging


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Abrindo Culto LouveApp Manager")
    initialize_database()
    app = CultoLouveAppManager()
    app.mainloop()


if __name__ == "__main__":
    main()
