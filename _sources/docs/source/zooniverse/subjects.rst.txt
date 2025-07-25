Subjects
========

Subjects and subject sets are one of the core components of a Zooniverse project. A subject is a single item which
users on Zooniverse will classify, so each subject is a mole stamp. A subject most importantly contains the medium to
be classified, such as a URL to an image or the actual image itself. A subject will also contain metadata which will
help identify the subject to be match to a stamp image. A subject set a collection of subjects, which are assigned to
a workflow (a set of questions to answer about each subject in included subject sets). Subjects can be allocated and
removed from a subject set dynamically, with fairly little processing time required for new subjects to become
available.

Once enough users have classified a subject, a consensus is reached and the subject is "retired" from the workflow
where the consensus has been reached. When a subject has been retired, it is not removed from the subject set but it
is also not shown again to be classified by users. The consensus classification and retirement process is all handled
by the Zooniverse backend, but can be managed manually if desired.

Uploading new subjects to a project or subject set counts towards a subject limit on Zooniverse. Each user in a project
has a limit of 10,000 subjects. It is imperative that any subject uploaded is somehow accounted for, as it is easy to
upload duplicate subjects or to accidentally remove a subject from a subject, which results in "dangling" subjects.
The reason why this is so important is that it is *very hard* (if not impossible without a Zooniverse admin account)
to remove any subjects once they have been uploaded. So it is very easy to fill up your quota. This is discussed in
further detail later in :ref:`Dealing with dangling subjects`.

Uploading subjects to Zooniverse, the easy way
----------------------------------------------

Turning stamps in the *MoleMarshal* database into subjects is handled by the ``molemarshal`` command, which does all of
the heavy listing of uploading subjects and assigning subjects to subject sets and workflows. All the stamps in the
stamp database will be uploaded by default. It is possible to upload a subset of stamps instead, though this is probably
a feature that will not see much use.

To upload subjects,

.. code:: bash

   $ molemarshal upload subjects

The workflow ID (in the configuration file) is used to link the subject set to the workflow. You therefore need an
already created (and ideally, but not required) configured workflow before running the command. The best way to create a
workflow is using the Zooniverse web interface for the project.

You can additionally provide a subject set ID, using ``-id SUBJECT_SET_ID``, to upload to a specific subject set. The
default choice is to upload (and create if missing) to a subject set named "Mole Stamps".

.. It is possible to upload a subset of stamps, rather than the entire database. To do this, you need to put images into a
.. directory or provide a text file of stamp images with a file path to a stamp on each line. For example,

.. .. code:: bash

..    $ molemarshal_m.py 19578 22510 -subset stamp_sub/ --verbose

.. The script will now look for stamps in the directory ``stamp_sub/`` and upload those. The stamps in this directory
.. **must** be in the stamp table in the database, otherwise the script will be unable to proceed as *MoleMarshal* will not
.. be able to effectively track these subjects. In this case, you will need to run ``molemarshal`` for
.. that directory.

Current limitations
--------------------

The *MoleMarshal* package has been written with the assumption that only **one** main subject set will exist for the
lifetime of the project. When subjects are added to a subject set, it is checked if the stamp already exists as a
subject. It **is not** checked if the subject has already been uploaded but may exist in a different subject set. It is
therefore not possible to have duplicate subjects in the same project linked to different subject sets. This is not a
limitation of the Zooniverse infrastructure, but a *forced* limitation of the database design to help avoid situations
where a stamp may exists as multiple subjects.

Future versions of *MoleMarshal* with active learning support will have support for multiple subject sets, but will
still enforce that a subject may only exist in one subject set.

Keeping the subject database up-to-date
---------------------------------------

Sometimes the subject database can become out of sync with the subjects uploaded to Zooniverse. This can happen if you
are re-building the database, creating a development database or if subjects have been uploaded from some other
machine. The ``molemarshal`` command has an option to bring the subject database inline with all the subjects on
Zooniverse.

This can be done at the project, subject set or workflow level, e.g.,

.. code:: bash

   $ molemarshal sync subjects project

.. code:: bash

   $ molemarshal sync subjects subject-set

.. code:: bash

   $ molemarshal sync subjects workflow

Uploading subjects to Zooniverse, the hard way
----------------------------------------------

If you need finer control over the subject creation and uploading process, then you can do things manually using the
functions in the :meth:`molemarshal.zooniverse.subjects` module.

Creating a new subject
^^^^^^^^^^^^^^^^^^^^^^

Creating a new subjects is done by using the ``Subject`` object from the ``panotpes_client``` packages.

.. code:: python

   from panoptes_client import Subject
   from panoptes_client import Project

   from molemarshal.zooniverse.subjects import get_named_subject_set_in_project
   from molemarshal.zooniverse.zooniverse import connect_to_zooniverse
   from molemarshal.zooniverse.zooniverse import open_zooniverse_project

   connect_to_zooniverse()
   project = open_zooniverse_project(PROJECT_ID)
   subject_set = get_named_subject_set_in_project(project, SUBJECT_SET_NAME)

   # using the async ability, iterate over all the stamps and create a Subject()
   # object for each subject with the following links, location and metadata

   with Subject.async_saves():

       all_stamps = your_function_to_get_stamps_to_upload()

       for stamp in all_stamps:

           subject = Subject()

           # get the data of the stamp to turn into a subject

           url, stamp_name, image_type, patient, date, filepath, description = stamp

           # at a minimum, you need to link the subject set to a project. You can
           # also create other links here, to e.g. workflows.

           subject.links.project = project

           # in the case of subjects which are URLs to images, the "location" of
           # the image is a dictionary. The key takes the form of image/image_type,
           # e.g. image/png, and the value is the URL to the image

           subject.add_location({f"image/{image_type}": url})

           # the metadata is a dictionary. At a minimum the key name should be
           # included as this is used to match classifications to stamp images.
           # The other metadata keys are generally quite helpful, but not required.

           subject.metadata.update(
               {
                   "name": stamp_name,        # bare minimum, include the name in the metadata
                   "image_type": image_type,  # the rest is optional
                   "patient": patient,
                   "date": str(date),
                   "filepath": filepath,
                   "description": description,
               }
           )
           subject.save()

This will create subjects which are linked to the project, and could be considered "dangling" if you do not add
them to a subject set or keep track of them somehow.

Creating a subject set
^^^^^^^^^^^^^^^^^^^^^^

Subject sets can be created using the web interface, by using ``panoptes_client`` or by using
:meth:`molemarshal.zooniverse.subjects.get_named_subject_set_in_project`, which will either retrieve the named subject
set or create a new one.

A subject set can be assigned to a workflow using
:meth:`molemarshal.zooniverse.workflows.assign_workflow_to_subject_set`
where the workflow can be retrieved using :meth:`molemarshal.zooniverse.workflows.get_workflow`. Note that
:meth:`molemarshal.zooniverse.workflows.assign_workflow_to_subject_set` does not check if the subject set is already
assigned to the workflow and will raise an Exception if it is.

.. code:: python

   from molemarshal.zooniverse import zooniverse
   from molemarshal.zooniverse import subjects
   from molemarshal.zooniverse import workflows

   # connect to Zooniverse and retrieve project and subject set
   zooniverse.connect_to_zooniverse()
   project = zooniverse.open_zooniverse_project(PROJECT_ID)
   subject_set = subjects.get_named_subject_set_in_project(project, SUBJECT_SET_NAME)

   # Assign the subject set to a workflow
   workflow = workflows.get_workflow(WORKFLOW_ID)
   workflows.add_subject_set_to_workflow(workflow, subject_set)

Adding subjects to a subject set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Subjects are easily added and remove from a subject set using `panoptes_client`. You can also manage this using the
web interface on Zooniverse, but is very tedious to do so. Following from the previous code block, we can create a list
of subjects as new subjects are created. With this list you can add these subjects,

.. code:: python

   # subject.add will take a list of subjects or a single subject. We have to
   # remember to do subject_set.save or none of the changes we've made will
   # apply

   subject_set.add(subjects_to_add)
   subject_set.save()  # important!!

To remove subjects from the subject set, you will need a list of subjects again,

.. code::  python

   from panoptes_client import Subject

   # the best way to get subjects to remove is by using Subject.find in a list
   # comprehension (or in a more traditional for loop) with a function evaluate
   # the eligibility for a subject to be removed

   subjects_to_remove = [
      subject for subject in Subject.find(project_id=PROJECT_ID) if subject_removal_criteria(subject)
   ]

   # subject.remove will, again, take a list of subjects or a single subject

   subject_set.remove(subjects_to_remove)
   subject_set.save()

Dealing with dangling subjects
------------------------------

The Zooniverse API/backend does not check for duplicate subjects when creating a new subject or adding a new
subject to a subject set. *MoleMarshal* will not allow you to create or add a duplicate subject to a subject set or to a
project, but sometimes mistakes do happen. It’s not always easy to fix these mistakes, but there are a few things you
can do to fix your mistake.

Linking dangling subjects to a subject set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All the subjects related to a project can be found using,

.. code:: python

   from panoptes_client import Subject

   project_subjects = Subject.find(project_id=PROJECT_ID)

where ``project_subjects`` is an iterable, but not a list! You can also find the subjects iin a subject set using,

.. code:: python

   from panoptes_client import SubjectSet

   subject_set = SubjectSet.find(SUBJECT_SET_ID)
   subjects = subject_set.subjects

where ``subjects`` is also an iterator as before.

In any case, with either iterable you can iterate over the subjects to either use ``SubjectSet.add()`` or
``SubjectSet.remove()`` to link or remove subjects to/from a subject set. This is useful when there are dangling
subjects which are not linked to a subject set, but belong to a project. An (old and outdated) example of trying to link
dangling subjects to a subject set can be found in
`assign_dangling_subjects.py <../_static/assign_dangling_subjects.py>`__.

Updating subject metadata and location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to re-use a subject or change some incorrect metadata, you can modify the ``Subject`` object directly,

.. code:: python

   from panotpes_client import Subject

   subject = Subject.find(SUBJECT_ID)

   # You can assign subject.locations with your own list of locations,
   # it's not clear what multiple locations does

   subject.locations = [{"image/png": "https://new-url.net/"}]

   # since the subject metadata is a standard python dictionary, you can use
   # subject.metadata.update to add new keys or replace any existing ones

   subject.metadata.update(
      {
         "key_1": "value 1",
         "key_2": "value 2"
      }
   )

   # don't forget to save your changes

   subject.save()

Asking Zooniverse for more storage space
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As a last case scenario if you can't fix everything by re-assigning subjects or changing their metadata, you can ask
for a higher quota then the initial 10,000 limit by emailing `contact@zooniverse.org <mailto:contact@zooniverse.org>`__
and explaining the simulation.
