"""
Link Subjects in the Zooniverse database linked to a project to a specific
subject set.
"""

import pickle
from panoptes_client import Subject
from sqlalchemy.orm import Session
from tqdm import tqdm

import molemarshal
import molemarshal.secrets

import molemarshal.zooniverse.subject_sets
from molemarshal import database

COMMIT_FREQUENCY = 1000
PROJECT_ID = 19578
SUBJECT_SET_ID = 109373

molemarshal.molemarshal.zooniverse.connect_to_zooniverse()
project = molemarshal.molemarshal.zooniverse.open_zooniverse_project(PROJECT_ID)
subject_set = molemarshal.zooniverse.subject_sets.get_named_subject_set_in_project(project, "Mole Stamps")

# subject_set.remove(list(subject_set.subjects))
# subject_set.save()
# exit(1)

print("Find dangling subjects -- those in the servers but not assigned to a subject set")

try:
    with open("dangling_subjects.pickle", "rb") as file_in:
        dangling_subjects = pickle.load(file_in)
except (IOError, EOFError):
    all_subjects_for_project = Subject.where(project_id=PROJECT_ID)
    print(f"Found {all_subjects_for_project.meta['count']} for project")
    dangling_subjects = []
    image_names_seen = []

    num_wrong_meta = 0
    num_not_a_stamp = 0
    num_duplicate = 0

    with Session(molemarshal.database.connect_to_database()) as session:
        for i, subject in enumerate(
            tqdm(
                all_subjects_for_project, desc="finding dangling subjects", total=all_subjects_for_project.meta["count"]
            )
        ):
            try:
                subject_image_name = subject.metadata["name"]
            except KeyError:
                num_wrong_meta += 1
                continue  # old subjects which don't have the new metadata, skip

            # if the image name is not in the stamp database, we don't want it
            stamp_in_database = (
                session.query(database.Stamp).filter(database.Stamp.stamp_name == subject_image_name).first()
            )
            if not stamp_in_database:
                num_not_a_stamp += 1
                continue

            # don't want duplicates either, as I uploaded the same subject set a few times
            if subject_image_name in image_names_seen:
                num_duplicate += 1
                continue

            image_names_seen.append(subject_image_name)
            dangling_subjects.append({"subject": subject, "stamp": stamp_in_database})

        print(f"{num_wrong_meta = }")
        print(f"{num_not_a_stamp = }")
        print(f"{num_duplicate = }")

        # with open("dangling_subjects.pickle", "wb") as file_out:
        #     pickle.dump(dangling_subjects, file_out, protocol=pickle.HIGHEST_PROTOCOL)

print(f"Adding {len(dangling_subjects)} dangling subjects to database")
exit(1)

with Session(molemarshal.database.connect_to_database()) as session:
    for n, subject in enumerate(progress_bar := tqdm(dangling_subjects, "adding dangling subjects to database")):

        stamp = subject["stamp"]
        subject = subject["subject"]

        entry = database.Subject(
            subject_id=subject.id,
            stamp_id=stamp.stamp_id,
            subject_set_id=SUBJECT_SET_ID,
            project_id=PROJECT_ID,
            owner=molemarshal.secrets.get_secret("username"),
        )

        session.add(entry)

        if (n + 1) % 1000 == 0:
            database.tqdm_commit_database(session, progress_bar)

    database.tqdm_commit_database(session, progress_bar)

print("Adding subjects to the subject set -- async no progess bar")

with Subject.async_saves():
    with Session(molemarshal.database.connect_to_database()) as session:
        database_subjects = session.query(database.Subject)
    for subject in database_subjects:
        s = Subject(subject.subject_id)
        subject_set.input(s)
        subject_set.save()
