Quickstart
==========

This page documents the typical use case of *MoleMarshal*, and will cover:

1. Uploading subjects to Zooniverse
2. Arranging subjects into active learning sub-groups
3. Downloading classifications from Zooniverse
4. Keeping the local database synced with Zooniverse

The *MoleMarshal* Zooniverse project is controlled by the ``molemarshal`` CLI, which is made up of several commands
and sub-commands. This is the tool which is used to upload and manage stamps to Zooniverse, and to manage the *MoleDB*
database. This program typically does not expect any arguments, as it will be configured with values from the
*MoleVerse* configuration file. More information about the configuration file can be found in
:ref:`Configuration`.

Uploading subjects to Zooniverse
--------------------------------

*MoleGazer* will periodically create new stamps which *MoleMarshal* can upload. Whenever this happens, you can use the
command

.. code:: bash

    $ molemarshal upload subjects

This command will upload any new subjects to Zooniverse and attempt to modify the location and metadata for subjects
which are already in Zooniverse. The default behaviour of this command will be to upload stamps to the default subject
set defined in the configuration file.

Arranging subjects into active learning sub-groups
--------------------------------------------------

To optimise the time of the users of *MoleMarshal*, an active learning approach is used which will preferentially show
subjects of low "machine confidence." This should significantly speed up model training for *MoleGazer* as it will mean
labels will be created for stamps which the model is struggling to identify.

The approach taken for active learning on Zooniverse is to split the stamps into several subject sets, each
with a different selection weighting set in the configuration file. Uploading subjects can be arranged into sub-groups
by using the command,

.. code:: shell

    $ molemarshal upload subject-weights

Downloading classifications fom Zooniverse
------------------------------------------

When a user submits a classifications, the Zooniverse data aggregation pipeline runs and the stamp can be updated near
instantly with the new classification. *MoleMarshal* downloads classifications in batch using the command,

.. code:: shell

    $ molemarshal sync classifications

There is some nuance to how classifications are stored in the *MoleDB* database however. Instead of *textual*
classifications being saved, an "answer index" is instead saved. The answer index corresponds to the index of the
answers defined in a workflow task on Zooniverse. For conveneince, the function
:meth:`molemarshal.zooniverse.classifications.convert_answer_index_to_value` is available to convert the answer indices
into *textual* answers for machine learning purposes.

Keeping the local database synched with Zooniverse
--------------------------------------------------

Sometimes the *MoleDB* database can become out of sync with Zooniverse. This usually happens when mananagement has been
done remotely on another computer, if a task failed in an unusual way, or if some of the Zooniverse infrastructure (such
as the subjects) are fiddled with in the web interface. To keep the database in tip-top condition, there are numerous
"sync" commands,

.. code:: shell

    $ molemarshal sync subjects [SOURCE]

.. code:: shell

    $ molemarshal sync subject-sets [SOURCE]

In both cases above ``[SOURCE]`` is the source where to sync from. Allowed values are typically workflow and project.

There are also some situations where subjects or subject sets are deleted online. This is typically rarer, but the
"dead" or "dangling" subjects/subject sets can be removed from the *MoleDB* database using,

.. code:: shell

    $ molemarshal admin cleanup-subjects

.. code:: shell

    $ molemarshal admin cleanup-subject-sets

Both of these commands will at the project level remove any subjects or subject sets which do not exist in the project.
