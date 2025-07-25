Configuration
=============

Many parts of the *MoleMarshal* package need to be configured to your project. Configuration is handled by a
configuration file. For *MoleMarshal* there are four sections with the following options,

.. code:: ini

    ;; filepaths for files in use
    [PATHS]
    database = moledb.sqlite.db

    ;; Zooniverse IDs for important entities, such as the project
    [ZOONIVERSE]
    host_address = https://molegazer.soton.ac.uk/context
    project_id = 19578
    workflow_id = 22510
    subject_set_id = 109373

    ;; login credentials for Zooniverse
    [CREDENTIALS]
    username =
    password =

    ;; Caesar reducers used in the workflow in the ZOONIVERSE section
    ;; reducer-key = task-index as configured on Caesar
    [REDUCERS]
    mole-classification = T0
    severity-classification = T1

    ;; This controls the active learning, which determines the number of
    ;; "priority" subject sets and their selection weighting
    [ACTIVE LEARNING]
    num_priority_sets = 3
    selection_weighting = 0.75, 0.125, 0.125

All of these options are mandatory. Some of the sections will be shared with other *MoleVerse* software, such as
*MoleGazer*. The location of this configuration file is not hardcoded and is read from the shell environment variable
``MOLE_CONFIG``. This can be set, e.g.,

.. code :: bash

    $ export MOLE_CONFIG="/path/to/config/file"

or if you use fish,

.. code :: fish

    $ set -gx MOLE_CONFIG "/path/to/config/file"

If this variable is not set or if the configuration file is not present at the filepath, the *MoleVerse* software will
throw an exception and exit.
