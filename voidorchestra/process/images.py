#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
This module contains scripts related to processing the Image database entries
for MoleGazer
"""
from datetime import date
from pathlib import Path
from typing import List, Optional

from imohash import hashfile
from sqlalchemy.orm import Session
from tqdm import tqdm

import voidorchestra.db
from voidorchestra.db.patient import Patient
from voidorchestra.db.image import Image

from molegazer.log import get_logger
from molegazer import config


logger = get_logger(__name__.replace(".", "-"))


def upload_images(directory_new: Optional[str]):
    """
    Scans the new files directory for new images and inputs them

    Recursively scans the directory passed for 

    Parameters
    ----------
    directory_new: Optional[str]
        The directory to scan for new images.
        If not provided, defaults to the PATHS:images_new configuration value.

    Returns
    -------

    """
    directory_new: Path = Path(config['PATHS']['images_new'])
    directory_raw: Path = Path(config['PATHS']['images_raw'])

    with Session(
        engine := voidorchestra.db.connect_to_database_engine(
            config['PATHS']["database"]
        )
    ) as session:
        logger.debug(
            f"Scanning {directory_new} for *.NEF...\n"
        )

        images_new: List[Image] = []
        count_patient_new: int = 0
        count_image_found: int = 0
        count_image_duplicate: int = 0

        tqdm_bar: tqdm = tqdm(
                directory_new.rglob('*.NEF'),
                "Uploading new images",
                unit=" images"
        )

        for path_image_new in tqdm_bar:
            tqdm_bar.set_postfix_str(
                f"Parsing '{path_image_new.relative_to(directory_new)}", refresh=True
            )

            logger.debug(
                f"Importing image {path_image_new.relative_to(directory_new)}\n"
            )

            count_image_found += 1

            # Hash image to see compare to those images in existing DB,
            # and if it's already in, delete the duplicate
            image_hash: str = hashfile(path_image_new)
            if session.query(Image).filter(Image.hash == image_hash).first():
                path_image_new.unlink()
                count_image_duplicate += 1
                continue

            # Extract data from filename
            patient_name, day, month, year, image_view = path_image_new.stem.split('_')
            image_date: date = date(
                year=int(year),
                month=int(month),
                day=int(day)
            )

            # Get patient if they exist, if not, then create them
            patient: Patient = session.query(Patient).filter(Patient.patient_name == patient_name).first()
            if not patient:
                patient: Patient = Patient(
                    patient_name=patient_name,
                    gender='not_specified',  # PLACEHOLDER
                    age=999  # PLACEHOLDER
                )
                session.add(patient)
                count_patient_new += 1
                session.commit()
                logger.info(
                    f"Committed new patient {patient} to database\n"
                )

            else:
                logger.debug(
                    f"Found existing patient {patient}\b"
                )

            # Create image, including moving the file to a new directory
            path_image_raw: Path = directory_raw / patient.patient_name / str(image_date) / path_image_new.name
            path_image_raw.parent.mkdir(parents=True, exist_ok=True)

            # Move the image to the raw directory
            path_image_new.rename(path_image_raw)

            image: Image = Image(
                image_name=path_image_raw.stem,
                filepath=str(path_image_raw.relative_to(directory_raw)),
                hash=image_hash,
                date=image_date,
                view_id=int(image_view),
                patient_id=patient.patient_id
            )

            session.add(image)
            images_new.append(image)

            tqdm_bar.set_postfix_str(
                f"Parsed '{path_image_new.relative_to(directory_new)}", refresh=True
            )

        tqdm_bar.set_postfix_str("Finished.", refresh=True)

        voidorchestra.db.commit_database(session=session)

        logger.info(f"Uploaded {len(images_new)} new images")
        logger.info(f"Created {count_patient_new} new patients")
        logger.info(f"Deleted {count_image_duplicate} duplicate images")
