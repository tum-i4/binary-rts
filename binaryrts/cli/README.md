# BinaryRTS CLI

The CLI for BinaryRTS is developed in [Python](https://www.python.org/downloads/) (>=3.8) and
uses [Poetry](https://python-poetry.org/docs/#installation) for package
management.

## Prerequisites

The CLI uses [`ctags`](https://github.com/universal-ctags/ctags) and [`cscope`](http://cscope.sourceforge.net/) to
analyze C/C++ source files.
For Windows, the binaries should be put into [`src/binaryrts/bin`](./src/binaryrts/bin).
The `cscope` binary is already available there, whereas an up-to-date pre-built `ctags` binary can be
downloaded [here](https://github.com/universal-ctags/ctags-win32).
To use the BinaryRTS CLI on Linux or macOS, install them as follows:

```shell
# ctags
# macOS
$ brew tap universal-ctags/universal-ctags
$ brew install --HEAD universal-ctags

# Linux
$ git clone https://github.com/universal-ctags/ctags.git
$ cd ctags
$ ./autogen.sh
$ ./configure --prefix=/where/you/want # defaults to /usr/local
$ make
$ make install # may require extra privileges depending on where to install

# cscope
# macOS
$ brew install cscope

# Linux
$ sudo apt install cscope
```

## Setup

To install the Python package with `poetry`, run:

```sh
$ poetry install
```

## Run

By default, Poetry will create a virtual environment in `.venv`, where the `binaryrts` is installed. You can simply run
the CLI via:

```shell
$ poetry run binaryrts
# or activate the virtual environment in the current shell
$ poetry shell
$ binaryrts
```

## Test

To execute the test suite, run:

```shell
$ poetry run pytest
```

## Build (Python wheel package)

To build a Python wheel package with `poetry`, run:

```shell
$ poetry build
Building binaryrts (0.1.0)
  - Building sdist
  - Built binaryrts-0.1.0.tar.gz
  - Building wheel
  - Built binaryrts-0.1.0-py3-none-any.whl
```

You can then distribute the `.whl` file to anywhere and install the wheel package with:

```shell
$ pip install --user binaryrts-0.1.0-py3-none-any.whl
```

## Usage

### CLI

Once the package is installed, the CLI can be used as follows:

```sh
$ binaryrts --help
Usage: binaryrts [OPTIONS] COMMAND [ARGS]...

  BinaryRTS CLI

Options:
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or
                        customize the installation.
  --help                Show this message and exit.

Commands:
  convert  Convert test traces
  select   Select tests
```

