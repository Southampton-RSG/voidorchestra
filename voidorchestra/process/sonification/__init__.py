from logging import INFO, Logger
from pathlib import Path
from typing import List
from uuid import NAMESPACE_URL, uuid5

from astropy.timeseries import TimeSeries
from moviepy import AudioFileClip, ImageClip
from plotly.graph_objects import Figure
from sqlalchemy.orm import Session
from strauss.sonification import Sonification as StraussSonification
from tqdm import tqdm

from voidorchestra import config, config_paths
from voidorchestra.db import Sonification, commit_database
from voidorchestra.log import get_logger
from voidorchestra.process.sonification.figure import plot_lightcurve

logger: Logger = get_logger(__name__.replace(".", "-"))


# Public functions ------------------------------------------------------------
def write_sonification_files(
    session: Session,
    sonifications: List[Sonification],
    commit_frequency: int = 1000,
) -> None:
    num_sonifications: int = len(sonifications)
    video_fps: float = config["SONIFICATION"].getfloat("video_fps")

    for i, sonification in enumerate(
        tqdm(
            sonifications,
            "Creating sonification files",
            unit="sonifications",
            leave=logger.level <= INFO,
            disable=logger.level > INFO,
        )
    ):
        lightcurve: TimeSeries = sonification.lightcurve.get_data()
        strauss_sonification: StraussSonification = sonification.sonification_profile.create_sonification(lightcurve)
        strauss_sonification.render()

        path_wav: Path = Path(sonification.path_audio).with_suffix(".wav")
        strauss_sonification.save(path_wav, embed_caption=False)
        audio: AudioFileClip = AudioFileClip(path_wav)
        audio.write_audiofile(Path(sonification.path_audio), codec="mp3")

        figure: Figure = plot_lightcurve(lightcurve)
        figure.write_image(Path(sonification.path_image))

        video: ImageClip = ImageClip(Path(sonification.path_image))
        video.duration = audio.duration
        video.audio = audio
        video.write_videofile(
            filename=Path(sonification.path_video),
            fps=video_fps,
        )
        # Delete the .wav file
        path_wav.unlink()
        sonification.processed = True
        session.add(sonification)

        if i % commit_frequency == 0:
            commit_database(session)
            logger.debug(
                "Processed %d/%d (%.0f%%) sonifications",
                i + 1,
                num_sonifications,
                (i + 1) / num_sonifications * 100,
            )
