from datetime import datetime
from pathlib import Path
from typing import List, Dict
from uuid import uuid4

import cv2

from numpy import float32, float64
from numpy._typing import NDArray
from sqlalchemy.orm import Session

import voidorchestra.db
import molegazer.log
from voidorchestra.db import Image, Stamp, Mole
from molegazer import config
from molegazer.process.stamps.blob import _create_blob_image, detect_blobs, filter_blobs
from molegazer.process.stamps.mask import mask_image
from molegazer.util.image import read_image_nef
from molegazer.input.config import load_feature_params


logger = molegazer.log.get_logger(__name__.replace(".", "-"))


def generate_stamps_single(
        session: Session, images: List[Image], test: bool = False
) -> List[Stamp]:
    """
    Given the images added to the database, creates 'stamps' depicting their

    Parameters
    ----------
    session: Session
        The current database session
    images: List[Image]
        The images added in this database session
    test: bool = False
        Whether to write the images out step-by-step

    Returns
    -------
    List[Stamp]: The stamps created in this process
    """

    stamps_new: List[Stamp] = []
    moles_new: List[Mole] = []
    directory_single: Path = Path(config['PATHS']['stamps_single'])

    blob_params: Dict[str, float] = load_feature_params()

    num_moles_total: int = 0

    for image in images:
        num_moles: int = 0
        num_skipped: int = 0
        num_filtered: int = 0

        logger.debug(f"Processing {image}: {image.filepath}")

        image_raw: NDArray[float32] = read_image_nef(image)
        image_colour_masked, image_grey_masked = mask_image(image_raw, blob_params)

        if test:
            # For 'test' runs, we want to write out the masks for comparison
            cv2.imwrite(f'test_{image.image_name}_raw.jpeg', cv2.cvtColor(image_raw, cv2.COLOR_RGB2BGR))
            cv2.imwrite(f'test_{image.image_name}_masked.jpeg', image_grey_masked)

        blobs: NDArray[float64] = detect_blobs(image_grey_masked, params=blob_params)
        blobs_filtered: NDArray[float64] = filter_blobs(blobs, image_colour_masked, params=blob_params)

        num_filtered += len(blobs) - len(blobs_filtered)

        # Create stamp images from blobs
        for blob_filtered in blobs_filtered:
            # Extract the position and size
            blob_y: int = int(blob_filtered[0])
            blob_x: int = int(blob_filtered[1])
            blob_size: float64 = blob_filtered[2]

            # Try and crop the image
            image_crop: NDArray[float32] = _create_blob_image(
                image_raw, position_x=blob_x, position_y=blob_y, size=blob_size
            )
            if image_crop is None:
                # If the crop failed as it was beyond the image bounds, skip this blob
                num_skipped += 1
                continue

            # Is this a new mole? If so, create a new mole entity
            # And commit to the DB so that we get the key to use later
            num_moles += 1
            mole: Mole = Mole(
                date_new=image.date,
                image_id=image.image_id,
                patient_id=image.patient_id,
            )
            session.add(mole)
            session.commit()

            # Path to write to features a UUID
            path_image_raw: Path = Path(image.filepath)
            path_stamp_single: Path = (
                    directory_single /
                    path_image_raw.with_name(
                        f"{path_image_raw.stem}_x{blob_x}-y{blob_y}-r{blob_size.round()}_{uuid4()}"
                    ).with_suffix('.jpeg')
            )
            path_stamp_single.parent.mkdir(parents=True, exist_ok=True)

            cv2.imwrite(
                str(path_stamp_single),
                cv2.cvtColor(image_crop, cv2.COLOR_RGB2BGR)
            )

            stamp: Stamp = Stamp(
                stamp_name=path_stamp_single.stem,
                filepath_single=str(path_stamp_single.relative_to(directory_single)),
                image_id=image.image_id,
                patient_id=image.patient_id,
                mole_id=mole.mole_id,
                date=image.date,
                image_type='jpeg',
                machine_confidence=0.5,
                position_x=blob_x,
                position_y=blob_y,
                size=blob_size
            )
            session.add(stamp)

            # Now update the mole's path to point at the most recent stamp of it
            mole.filepath = stamp.filepath_single

            # Record the new records we've created
            moles_new.append(mole)
            stamps_new.append(stamp)

        logger.debug(
            f"Image {Image} contained {num_moles} moles, skipped {num_skipped} moles in image edges, "
            f"{num_filtered} blobs filtered out"
        )
        num_moles_total += num_moles
        image.date_processed = datetime.now()

    logger.info(
        f"Scanned {len(images)} image{'s' if len(images) > 1 else ''}, identified {num_moles_total} potential moles"
    )

    voidorchestra.db.commit_database(session)
    return stamps_new
