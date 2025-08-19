# Void Orchestra

*Void Orchestra* is a python package designed to create lightcurves of quasi-periodic oscillations,


## Requirements

### Package Manager 
**Void Orchestra** uses the Python package manager [**uv**](https://docs.astral.sh/uv/). 
This can easily be installed system-wide using `pipx`:

```bash
$ sudo apt install pipx  # Or if on RHEL, sudo yum install pipx
$ pipx install uv
```

### Plot Graphics
Plots are generated using the `plotly` Python package, which requires a working browser.
If using a server that doesn't have a browser by default, install **chromium**:
```bash
$ sudo apt install chromium  # 
```

### Environment Variables

A shell environment variable `VOIDORCHESTRA_CONFIG` is also required, 
which points to the configuration file which configures *Void Orchestra*,

```bash
$ export VOIDORCHESTRA_CONFIG="/path/to/config/file"
```

or if you use fish,

```bash
$ set -gx VOIDORCHESTRA_CONFIG "/path/to/config/file"
```

If this configuration file does not exist at this location, 
the default configuration file will be copied to this location.

## Installation

To install *Void Orchestra*, create a `/var/www` directory (if it doesn't already exist) and clone the repository there:

```bash
mkdir /var/www 
cd /var/www
git clone https://github.com/Southampton-RSG/voidorchestra.git 
```

Then, enter the directory, install the software and initialise the database, before installing the 'fixtures' containing
pre-set sonification methods and profiles:

```bash 
cd voidorchestra
make install
make database 
make fixtures
```

## Usage

Once the database has been installed and initialised, you can begin creating new sonifications.

### File Server

To serve the files to Zooniverse, you can use the provided Nginx container.
Launch a screen, start the server, then disconnect:

```bash
screen
docker compose up
[Ctrl-A, Ctrl-D]
```

Using `docker compose up` will launch Nginx, and serve files from the output directory.
If using this on a machine serving multiple sites, 
you can instead add the configuration file to your existing Nginx setup. 
Assign ownership of the directory to the `voidorchestra-staff` group and add `nginx` to it:
```bash 
sudo usermod -a -G voidorchestra-staff nginx
sudo chgrp -R voidorchestra-staff /var/www/voidorchestra
sudo chmod -R g+rw /var/www/voidorchestra 
```

Then, depending on your Linux distribution:

#### Debian/Ubuntu
Copy or link `nginx/voidorchestra.conf` to your `/etc/nginx/sites-enabled/` directory, then restart Nginx:
```bash
ln -s /var/www/voidorchestra/nginx/voidorchestra.conf /etc/nginx/sites-enabled/ 
sudo systemctl reload nginx
sudo systemctl restart nginx
```


#### Fedora/RHEL
Copy `nginx/voidorchestra.conf` file to your `/etc/nginx/conf.d` directory, 
then flag the log directory as permitted by SELinux:
```bash 
sudo cp /var/www/voidorchestra/nginx/voidorchestra.conf /etc/nginx/conf.d/
sudo chcon -R system_u:object_r:httpd_log_t:s0 /var/www/voidorchestra/logs 
```

  
