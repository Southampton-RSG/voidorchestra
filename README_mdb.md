# MoleDB

MoleDB is the repository containing the code which defines and manages the database that both MoleGazer and
MoleMarshal use.

Please check the documentation API to learn how to connect to the database engine.

## Usage

The general use case of this package is to import this repository as a git submodule into your repository,

```bash
$ cd /path/to/your/repo
$ git submodule add git@github.com:MoleGazer/MoleDB.git
```

You can then choose how you import this module into your code. You may also wish to instead install the package to
your Python path to import it,

```bash
$ git clone git@github.com:MoleGazer/MoleDB.git
$ cd MoleDB
$ pip install -e .
```

## Documentation

Documentation for the package can be found in the `docs` directory. The documentation can either be rendered as a
webpage or as a PDF document. It either case, documentation is built using sphinx which should be installed when you
configure your local python environment.

To build the HTML documentation, use the following command,

```bash
$ sphinx-build -a -j auto -b html docs/source/ docs/build/html
```

This will create a directory `docs/build/html` and you can view the documentation by opening
`docs/build/html/index.html` in your web browser.
