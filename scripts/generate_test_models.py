"""
Generates a 'test' model of a Lorentzian to explore visibility.

Call using python scripts/generate_test_models.py
"""
from logging import Logger

from astropy.time import TimeDelta
from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.db import commit_database, connect_to_database_engine
from voidorchestra.db.qpo_model import QPOModelLorentzian
from voidorchestra.log import get_logger
from voidorchestra.process.qpo_models import write_psd_images

logger: Logger = get_logger(__name__.replace(".", "-"))


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:
    # Has this already been done?
    try:
        if qpo_model_lorentzian := session.query(QPOModelLorentzian).where(
                QPOModelLorentzian.name == "Lorentzian Test Model",
        ).one_or_none():
            print(f"Found already defined model: {qpo_model_lorentzian}")

        else:
            qpo_model_lorentzian: QPOModelLorentzian = QPOModelLorentzian(
                name=f"Lorentzian Test Model",
                coherence=5.0,
                period_value=TimeDelta(1.0e6, format="sec").value,
                period_format="sec",
                variance_fraction=0.50,
            )
            session.add(qpo_model_lorentzian)
            commit_database(session)

        write_psd_images([qpo_model_lorentzian], filenames=["test_pure_lorentzian"])

    except Exception as e:
        print("Error: Multiple copies of Lorentzian test model in DB.")
