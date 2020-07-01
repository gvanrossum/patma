# Binder support for PEP-622 examples

This directory offers [Binder](https://mybinder.org) support for these
[PEP-622](https://www.python.org/dev/peps/pep-0622) examples, which
depend on a currently experimental build of Python 3.10.  It is
intended to facilitate testing and discussion of this proposed change
to Python so that users can play with the proposed syntax without
having to build and install everything themselves.

This directory contains all the necessary tools for Binder support,
all other content related to PEP-622 is in the rest of the repo and
doesn't need binder.  This repo uses two binder tools for setup:

1. An `apt.txt` file listing useful packages needed for the build.
2. A `postBuild` script that builds/installs CPython 3.10 from the
   right branch and then updates that installation with some necessary
   dependencies for testing/running the examples.


## Build notes

Since testing the pattern matching features requires a custom Python
build, we start from a standard Binder image and then build Python
3.10 in the container. Python 3.10 is new enough that we need to build
PyZMQ from the master branch, and use IPython master to have a
3.10-based kernel for Jupyter, and tab completion will not be working
until a fix is done upstream in _parso_ which his used for jedi. But
we can still use 3.10 at the command-line to test the examples, and
take advantage of the JupyterLab UI for easy experimentation
(terminals, text editors, etc).

The [experimental build of CPython
3.10](https://github.com/brandtbucher/cpython) (branch `patma`) needed
for this is installed in `$HOME/.local/bin`, and the source of the
build is available in `/tmp/cpython`, in case the user wants to
experiment with it.

The build dependencies listed in apt.txt can be found by using the
`apt-rdepends` package:

```
apt-rdepends --build-depends --follow=DEPENDS python3-defaults | grep Build-Depends | awk -F ' +' '{print $3}'
```

Normally this container will run automatically and provide a usable
URL with Jupyter in it if `jupyter-repo2docker .` is run at the top of
the repository. But if anything goes wrong and you need to debug, you
can find the image ID of the repo with `docker images` and then run it
interactively (with root privileges) by using:

```
docker run --interactive --tty --entrypoint=/bin/bash -e GRANT_SUDO=yes --user root <IMAGE> --login
```


## TODO

As IPython, pyzmq and other dependencies are released with Python 3.10
compatibility, this repo can be updated to have a proper 3.10 kernel
using released versions.
