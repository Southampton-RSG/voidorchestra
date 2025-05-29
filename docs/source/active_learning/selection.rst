Selection
=========

Once each stamp has been given a confidence, the subjects which represent these stamps on
Zooniverse will be arranged into different subject sets depending on their confidence. Each subject set will have a
different weighting which affects the probability a subject will be selected from a subject set.

Priority subject sets
---------------------

A "priority subject set" is the same as a "regular" subject set, except *MoleMarshal* has tagged them with
a priority and selection weight which tells Zooniverse which subjects should ideally be classified first. A subject set
with priority 1, and largest sample probability, contains the lowest confidence stamps and Zooniverse will present users
with stamps from this subject set more often.

The selection weight/probability of all the priority subject sets must sum to 1. If we have three subject sets, one with
a weight of 0.9 and the other 0.05, then for every 10 subjects randomly selected 9 of them will come from the first
two subjects sets and 1 from each of the other remaining subject sets (on average, at least).

Arranging subjects into subject sets
------------------------------------

The priority subject sets each represent an equal share of machine confidence parameter space, that is if there are four
priority subject sets then subject set 1 would cover a confidence interval of 0 - 0.25, and subject set 2 would cover
the interval 0.25 - 0.5, and so on. This translates into a bin width of ``bin_width = 1 / num_priority_sets``. The
binning of subjects by their machine confidence is straightforward ``priority_rank = confidence // bin_width``, with
appropriate upper and lower limits applied. Arranging the subjects into priority subject sets is done by the function
:meth:`bin_subjects_into_priority_subject_sets` which takes a list of the priority subject sets as input.

The function :meth:`bin_subjects_into_priority_subject_sets` will bin all of the subjects in the subject database which
have not been retired.

Subjects should only belong in one subject set in MoleMarshal, thus as subjects are moved around between the different
priority subject sets (if their machine confidence has change) additional bookkeeping is done to ensure that subjects
are only in one subject set.

Creating priority subject sets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creation of the priority subject sets is identical to regular subject sets, with the only difference being some
internal tracking in the *MoleMarshal* database which is used to put subjects into the correct priority subject set
depending on their weight.

To automatically create and retrieve priority subject sets, you will need the ID for the project and workflow they will
be assigned to as well as the number of priority subject sets,

.. code:: python

    from molemarshal.active_learning.weights import get_priority_subject_sets

    priority_subject_sets = get_priority_subject_sets(PROJECT_ID, WORKFLOW_ID, NUM_PRIORITY_SETS)

The above function will deal with getting subject sets from the *MoleMarshal* database (or Zooniverse) and creating any
missing subject sets and the necessary bookkeeping to track the priority and selection weighting. It is not really
advisable to create your own priority subject sets, as there is a lot of bookkeeping required to ensure that no
duplicate subject sets are created or linked to the wrong workflows.

The priority subject sets follow a standing naming convention,

.. code:: output

    WF(WORKFLOW_ID) Mole Stamp Priority Priority #(PRIORITY)

Where ``(WORKFLOW_ID)`` and ``(PRIORITY)`` reflect the workflow the subject set is assigned to and the priority ranking
respectively. Each workflow will have its own unique subject sets. *MoleMarshal* does not support linking a priority
subject set to multiple workflows, as given the setup and the name of the subject sets this would be too confusing. It
is possible to have *regular* subjects sets linked to multiple workflows however.

Selection weighting
-------------------

The selection weighting is set on a per workflow basis for each subject set. This actually means you can have the same
subject set in multiple workflows all with different selection weightings. The selection weights of the subjects are
updating using :ref:`molemarshal.active_learning.weights.set_priority_subject_set_weights_for_workflow` which takes a
list of subject set IDs and the workflow as input,

.. code:: python

    import molemarshal
    from molemarshal.active_learning.weights import set_priority_subject_set_weights_for_workflow

    workflow = Workflow.find(WORKFLOW_ID)
    priority_subject_sets = get_priority_subject_sets(PROJECT_ID, WORKFLOW_ID, NUM_PRIORITY_SETS)
    weights = molemarshal.config["ACTIVE LEARNING"]["selection-weights"]
    set_priority_subject_set_weights_for_workflow([subject_set_id for subject_set in priority_subject_sets], weights, workflow)

The selection weightings must all sum to 1 and all of the subject set IDs passed must belong to subject sets which are
assigned to the passed workflow. The function will fail otherwise.

If you want to get your hands dirty, you can modify the weights directly using the panoptes API as follows,

.. code:: python

    from math import isclose
    from panoptes_client import Workflow
    from molemarshal.active_learning.weights import get_priority_subject_sets

    # we can get subject sets using `get_priority_subject_sets` which will
    # return a list of subject sets
    priority_subject_sets = get_priority_subject_sets(PROJECT_ID, WORKFLOW_ID, NUM_PRIORITY_SETS)
    # what we also need is the IDs of the subject sets and the selection
    # weighting we want to give them
    ids = [str(subject_set.id) for subject_set in subject_set_ids]
    weights = [0.5, 0.5]
    # the weights SHOULD sum up to 1. There is nothing in the API to really stop
    # you from having weights which do not sum to 1 though
    assert isclose(sum(weights), 1)

    # we add the priority subject sets in the regular way
    workflow = Workflow.find(WORKFLOW_ID)
    workflow.add_subject_sets(priority_subject_sets)
    # the magic is in workflow.configuration, where we add a new key
    # "subject_set_weights", which is a dict of subject_set_id: weight.
    workflow.configuration["subject_set_weights"] = {ids[0]: weights[0], ids[1]: weights[1]}
    workflow.save()

Updating the weights on Zooniverse
----------------------------------

Updating the weights of priority subject sets on Zooniverse and the subject sets which subjects are in (e.g. if the
machine confidence of stamps have been updated) can be done using the `molemarshal` command,

.. code:: bash

    molemarshal upload subject-weights

This command will deal with creating/unlinking priority subject sets, setting their selection weights (as designed in
the configuration file) and with arrange the subjects into the correct subject sets given the machine confidence of
their stamps.

In cases where the number of priority subject sets stays the same but the selection weight is changed, the weights will
be updated for the workflow and database but nothing else will change. In the case of the number of subject sets
changing, then the subjects will be re-arranged into the new group of priority subject sets.
