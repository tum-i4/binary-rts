# BinaryRTS Frida Instrumentation Agent

**Caveat:** Experimental, Windows-only

## Concept

The goal of this agent is to provide a different approach for binary
instrumentation that copes with the oftentimes high overhead of DynamoRIO.

To instrument binaries with the Frida instrumentation agent, you first need to
extract all functions from all binaries that you want to instrument.
Use the [BinaryRTS extractor](../extractor) project (currently Windows-only) to extract all funtions including their locations from the binaries (e.g., EXEs and DLLs).
Then, use the Frida agent to run the test executable or attach it to an existing
process.
The agent will hook all function offsets at run-time and remove the probes once a
function gets executed.
When the process is terminated, the agent dumps the collected function coverage
into a log file which can be used together with the BinaryRTS CLI to generate
test traces.

## Development

The BinaryRTS Frida instrumentation agent is developed as a standalone tool, to ease development and integration into other projects.
It consists of an instrumentation agent (written in TypeScript) as well as a Python script that steers the agent.

## Prerequisites

- [Python](https://www.python.org/downloads/) (>=3.8)
- [Poetry](https://python-poetry.org/docs/#installation)
- [NodeJS](https://nodejs.org/en/) (ideally >=14)

## Setup

To install the Python package with `poetry`, run:

```shell
$ poetry install
```

Alternatively, you can also install `frida` and `frida-tools` with `pip`:
```shell
$ pip3 install frida frida-tools
```

## Run

By default, Poetry will create a virtual environment in `.venv`, where the `binaryrts-frida` is installed. You can simply run
the CLI via:

```shell
# If you want to use the agent standalone, simply run:
$ python3 src/binaryrts_frida/main.py
# If using poetry, run:
$ poetry run binaryrts-frida
# or activate the virtual environment in the current shell
$ poetry shell
$ binaryrts-frida
```

## Build (Python wheel package)

To build a Python wheel package with `poetry`, run:

```shell
$ poetry build
```

You can then distribute the `.whl` file to anywhere and install the wheel package with:

```shell
$ pip install --user binaryrts-frida-0.1.0-py3-none-any.whl
```
