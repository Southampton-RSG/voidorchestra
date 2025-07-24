from typing import Dict, List

from sqlalchemy.orm import Session

from voidorchestra.db import Sonification, SonificationProfile, LightcurveCollection


def assign_lightcurve_collection_subject_sets_to_workflows(
        session: Session,
        lightcurve_collection: LightcurveCollection,
        sonification_profile_to_workflow_id: Dict[SonificationProfile, int]
):
    sonifications_per_workflow_id: Dict[int, List[Sonification]] = {}

    for lightcurve in lightcurve_collection.lightcurves:
        for sonification in lightcurve.sonifications:
            workflow_id: int = sonification_profile_to_workflow_id[sonification.sonification_profile]

            sonifications_for_workflow: List[Sonification] = sonifications_per_workflow_id.get(
                workflow_id, []
            )
            sonifications_for_workflow.append(sonification)
            sonifications_per_workflow_id[workflow_id] = sonifications_for_workflow

