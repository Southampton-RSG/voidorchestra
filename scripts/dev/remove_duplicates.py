import molemarshal
import voidorchestra.zooniverse.zooniverse
import voidorchestra.db

from panoptes_client import SubjectSet, Subject
from sqlalchemy.orm import Session

voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()

sets = {}
with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
    subjects = session.query(voidorchestra.db.Subject)
    unique_stamp_ids = set(subject.stamp_id for subject in subjects)

    for stamp_id in unique_stamp_ids:
        query = session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.stamp_id == stamp_id)

        if query.count() > 1:
            print(f"Stamp {stamp_id} has {query.count()} subjects")
            for subject in query[1:]:
                if subject.subject_set_id not in sets:
                    sets[subject.subject_set_id] = SubjectSet.find(subject.subject_set_id)
                sets[subject.subject_set_id].remove(Subject.find(subject.subject_id))
                session.delete(subject)

    session.commit()

for sub in sets.values():
    sub.save()
