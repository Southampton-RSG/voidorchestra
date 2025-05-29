Project
=======

To classify if a stamp image contains or does not contain a mole, the `Zooniverse <https://www.zooniverse.org>`__
infrastructure is used. Zooniverse provides ready-made workflows and pipelines for uploading/managing data, collecting
user classifications and for data reduction. A large chunk of the *MoleMarshal* package deals with getting data into and
out of the Zooniverse servers.

The :meth:`molemarshal.zooniverse.zooniverse` module contains functions to do generic (or things which don’t fit
elsewhere) operations related to the project in Zooniverse.

Access to the project and data
------------------------------

The project on Zooniverse, named `MoleMarshal <https://www.zooniverse.org/projects/edward-rse/molemarshal>`__, is
private and you need to be a collaborator to gain access to and classify any images.

Given the sensitivity of the medical data, and that it cannot leave Southampton servers, Zooniverse will serve
URLs which are hosted behind the university VPN. This approach satisfies keeping data on Southampton servers, as well as
keeping the data private and granting access to only those who are part of the collaboration.

The stamp images will be served (using nginx) from an iSolutions virtual machine, with the web address
https://molegazer.soton.ac.uk/. Images are served from the directory,

.. code:: output

   /mnt/rawdata/moleverse/stamps


Connecting to the Panoptes API
------------------------------

To modify the project on Zooniverse, we first need to make a connection to the Panoptes API and log in. This is not
handled with an API key. You instead need to provide your Zooniverse username and password to ``panoptes_client``. The
function :meth:`molemarshal.zooniverse.zooniverse.connect_to_zooniverse` is a wrapper around the ``panoptes_client``
API which handles getting the appropriate credentials and making the connection. The user credentials should be set in
the configuration file.

The Zooniverse project
----------------------

To edit the MoleMarshal Zooniverse project using the ``panoptes_client``, the project can be retrieved using the
function :meth:`molemarshal.zooniverse.zooniverse.open_zooniverse_project`. You will need to provide the project ID and
it will return a `Project <https://panoptes-python-client.readthedocs.io/en/latest/panoptes_client.html#module-panoptes_client.project>`__
object, which you can use to modify various top level data about the Zooniverse project.

The below table lists the important parts of the project and their Zooniverse IDs.

================ ================ ======
Component        Name             ID
================ ================ ======
Project          MoleMarshal      19578
Workflow         Is there a mole? 22510
Main subject set Mole Stamps      111809
================ ================ ======
