from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.db import connect_to_database_engine
from voidorchestra.db.lightcurve.synthetic import LightcurveSyntheticRegular
from voidorchestra.db.qpo_model import QPOModelBPL, QPOModelComposite, QPOModelLorentzian
from voidorchestra.db.sonification import Sonification, create_sonification
from voidorchestra.db.sonification_profile import SonificationProfile


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:
    composite_model: QPOModelComposite = QPOModelComposite(
        name="Composite mostly Lorentzian",
    ).add_components(
        [
            {
                'model': QPOModelBPL,
                'arguments': dict(
                    variance_fraction=0.4,
                    coherence=5.0,
                    period_value=21,
                    period_format='jd',
                ),
            }
        ]
    )
    session.add(composite_model)

    lightcurve: LightcurveSyntheticRegular = LightcurveSyntheticRegular(
        name="Composite model 100 day",
        start_time=datetime.now(),
        observation_count=100,
        cadence_value=3,
        cadence_format='jd',
        rate_mean_value=25.0,
        rate_mean_units='1 /s',
        qpo_model=composite_model,
    )
    session.add(lightcurve)

    sonification_profile: SonificationProfile = session.query(SonificationProfile).where(SonificationProfile.id==0).one()

    sonifications: List[Sonification] = [
        create_sonification(
            lightcurve=lightcurve,
            sonification_profile=sonification_profile,
        ) for i in range(5)
    ]
    session.add_all(sonifications)
    session.commit()



#
# standard_parameters: Dict[str, Any] = {
#     "repeats": [0, 1, 2],
#     "rate_mean": 25 * u.s**-1,
#     "observation_cadence": TimeDelta(3, format="jd"),
#     "campaign_length": TimeDelta(360, format="jd"),  # ~17 periods
#     "model_definition": [
#         QPOModelBPL(
#             name="BPL",
#             variance_fraction=0.4,
#             coherence=5.0,
#             period=TimeDelta(21, format="jd"),
#         ),
#         QPOModelComposite(
#             name="Composite mostly BPL",
#             qpo_model_children=[
#                 QPOModelBPL(
#                     variance_fraction=0.3,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#                 QPOModelLorentzian(
#                     variance_fraction=0.1,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#             ]
#         ),
#         QPOModelComposite(
#             name="Composite 50:50 BPL:Lorentzian",
#             qpo_model_children=[
#                 QPOModelBPL(
#                     variance_fraction=0.2,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#                 QPOModelLorentzian(
#                     variance_fraction=0.2,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#             ]
#         ),
#         QPOModelComposite(
#             name="Composite mostly Lorentzian",
#             qpo_model_children=[
#                 QPOModelBPL(
#                     variance_fraction=0.1,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#                 QPOModelLorentzian(
#                     variance_fraction=0.3,
#                     coherence=5.0,
#                     period=TimeDelta(21, format="jd"),
#                 ),
#             ]
#         ),
#         QPOModelLorentzian(
#             name="Basic Lorentzian",
#             variance_fraction=0.4,
#             coherence=5.0,
#             period=TimeDelta(21, format="jd"),
#         ),
#     ],
# # }