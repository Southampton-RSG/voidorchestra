import voidorchestra.db
import molemarshal

from sqlalchemy.orm import Session
import numpy

with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
    subjects = session.query(voidorchestra.db.subject.Subject).filter(
        voidorchestra.db.subject.Subject.workflow_id == voidorchestra.config["ZOONIVERSE"]["workflow_id"]
    )
    for i, subject in enumerate(subjects):
        subject.stamp.machine_confidence = numpy.random.rand()
    session.commit()
