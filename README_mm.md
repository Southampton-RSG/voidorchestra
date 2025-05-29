# MoleMarshal

The *MoleMarshal* Command Line Interface and Python package are  a collection of scripts designed to automate data
processes for the *MoleMarshal* Zooniverse project. This includes the creation of image manifests, subject sets and
an active learning workflow, as well as uploading subjects and subject sets and downloading aggregated classification
data from the Zooniverse workflow.

## Installation

To install *MoleMarshal* you will first need to clone the repository using the `--recursive` flag to also download
the MoleDB submodule,

```shell
$ git clone git@github.com:MoleGazer/MoleMarshal.git --recursive
```

*MoleMarshal* can then be installed through pip or setup tools where you will need a minimum Python verison of 3.9,

```shell
$ pip install .
```

```shell
$ python setup.py install
```

A shell environment variable ``MOLE_CONFIG`` is also required, which points to the configuration file which
configures *MoleMarshal*,

```shell
$ export MOLE_CONFIG="/path/to/config/file"
```

or if you use fish,

```shell
$ set -gx MOLE_CONFIG "/path/to/config/file"
```

If this configuration file does not exist at this location, the default configuration file will be copied to this
location.

To suppress some warnings associated with the `panoptes_client`, you will also need to install the `libmagic` library,
which should be in your package manager, e.g.

```shell
$ brew install libmagic
```

```shell
$ sudo apt install libmagic-dev
```

## Documentation

Documentation for the package can be found in the `docs` directory. The documentation can either be rendered as a
webpage or as a PDF document. It either case, documentation is built using `sphinx` which should be installed when
you configure your local python environment.

To build the HTML documentation, use the following command,

```bash
$ sphinx-build -a -j auto -b html docs/source/ docs/build/html
```

This will create a directory `docs/build/html` and you can view the documentation by opening
`docs/build/html/index.html` in your web browser.

## Development

Most of the dependencies for *MoleMarshal* can then be installed using `pip` or `conda`. It's strongly recommended,
especially for development, that you create a virtual environment to isolate and manage the dependencies, e.g.,

```shell
$ conda env create -f environment.yml
```

```shell
$ python -m venv /path/to/new/env
$ source /path/to/new/env/bin/activate && pip install -e .
```

where `-e` will install *MoleMarshal* in "editable" mode.
