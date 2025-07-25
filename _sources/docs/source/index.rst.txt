.. MoleMarshal documentation master file, created by
   sphinx-quickstart on Thu Oct 27 16:01:35 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

MoleMarshal Documentation
=========================

*MoleMarshal* is a supporting Python package for the `MoleMarshal Zooniverse project
<https://www.zooniverse.org/projects/edward-rse/molemarshal>`_. Its purpose is to automate the creation and management
of subjects and subject sets, and to link classifications to subjects.

Installation
------------

For the most part, all of the dependencies are easily installed using :code:``conda`` or :code:``pip``. It's strongly
recommended that you create a virtual environment to manage your dependencies, e.g.,

.. code:: bash

   $ conda env create -f environment.yaml

.. code:: bash

   $ python -m venv /path/to/new/env
   $ source /path/to/new/env/bin/activate && pip install .

A shell environment variable ``MOLE_CONFIG`` is also required, which points to the configuration file which
configures *MoleMarshal*,

.. code :: bash

    $ export MOLE_CONFIG="/path/to/config/file"

or if you use fish,

.. code :: fish

    $ set -gx MOLE_CONFIG "/path/to/config/file"

If this configuration file does not exist at this location, the default configuration file will be copied.

To suppress certain warnings you will also need to install ``libmagic``, which can usually be found in your system
package manager, e.g.

.. code:: bash

   $ brew install libmagic

.. code:: bash

   $ sudo apt install libmagic-dev

Terminology
-----------

There is a lot of terminology used throughout this documentation related to Zooniverse. It's mostly obvious but for the
sake of clarity, the table below describes what they mean.

+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Term         | Definition                                                                                                                 |
+==============+============================================================================================================================+
| Panoptes     | The Zooniverse backend responsible for pretty much everything                                                              |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Caesar       | The Zooniverse automatic data aggregation tool, used to calculate consensus classifications                                |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Extractor    | A tool for extracting data into a "nice" format from a user classification                                                 |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Reducer      | A tool for aggregating multiple classifications for a subject (from multiple users) into one consensus classification      |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Project      | The user facing Zooniverse project                                                                                         |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Subject      | An image with associated metadata and classifications, shown to a user. This is what a stamp image is on Zooniverse        |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Subject set  | A collection of subjects, which are assigned to a workflow                                                                 |
+--------------+----------------------------------------------------------------------------------------------------------------------------+
| Workflow     | A collection of tasks a user completes to classify the subjects in an assigned subject set                                 |
+--------------+----------------------------------------------------------------------------------------------------------------------------+

.. toctree::
   :hidden:
   :maxdepth: 1

   quickstart
   configuration

.. toctree::
   :hidden:
   :caption: Zooniverse

   zooniverse/project
   zooniverse/subjects
   zooniverse/classifications

.. toctree::
   :hidden:
   :caption: Active Learning

   active_learning/introduction
   active_learning/selection

.. toctree::
   :hidden:
   :caption: Reference

   api
   genindex
