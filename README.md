# MoleGazer

*MoleGazer* is a python package designed to use image recognition to identify moles from photos of patients,
and then upload those to a database.


## Installation

To install *MoleGazer* you will first need to clone the repository using the `--recursive` flag
to also download the *MoleDB* submodule,

```bash
$ git clone git@github.com:MoleGazer/MoleGazer.git --recursive
```

*MoleGazer* can then be installed through pip or setup tools where you will need a minimum Python verison of 3.9.

```bash
$ pip install .
$ python setup.py install
```

A shell environment variable `MOLE_CONFIG` is also required, 
which points to the configuration file which configures *MoleGazer*,

```bash
$ export MOLE_CONFIG="/path/to/config/file"
```

or if you use fish,

```bash
$ set -gx MOLE_CONFIG "/path/to/config/file"
```

If this configuration file does not exist at this location, 
the default configuration file will be copied to this location.

## Usage

Initialise the database, and import the data on the 'standard views' in it using the database *MoleDB* as:

```bash
moledb init
moledb init views
```

Then, start watching the directory you'll be adding files to using:
```bash
molegazer watch images
```

This will run continuously. When you add any new files to the directory, 
they'll automatically be uploaded, and then parsed.

If you already have images in the directory, 
MoleGazer will automatically import them when it detects any other changes.
You can manually trigger this process by:

```bash
molegazer upload images
```

Once the images have been entered into the database, you can generate the stamps for them using:
```bash
molegazer create stamps
```
This process is not automatic. It can be scheduled using a cron job, or run manually.
