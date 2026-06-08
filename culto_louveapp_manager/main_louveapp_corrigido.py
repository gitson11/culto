from src.config import APP_NAME
from src.database import initialize_database
from src.logger import get_logger, setup_logging


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Abrindo %s com importador LouveApp corrigido", APP_NAME)
    initialize_database()

    from src import gui as gui_module
    from src.louveapp_importer import import_louveapp_schedules

    gui_module.import_louveapp_schedules = import_louveapp_schedules

    app = gui_module.CultoLouveAppManager()
    app.mainloop()


if __name__ == "__main__":
    main()
