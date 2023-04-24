# File Splitter

This is an experimental tool that breaks apart god files.

## Usage

Currently, we do not provide a distributable package (i.e. something that could be installed with pip.) Instead, work is done by cloning the repository, setting up a virtual environment, and then using Jupyter notebooks or the provided CLI.
```
# Clone this repository
git clone https://github.com/jlefever/filesplitter
cd filesplitter

# Create a virtual environment called ".venv"
python -m venv .venv

# Activate the ".venv" virtual environment
# If not using bash, see https://docs.python.org/3/library/venv.html#how-venvs-work
source .venv/bin/activate

# Install the requirements
python -m pip install -r requirements.txt
```

For the command line interface:
```
python -m filesplitter --help
```

For Jupyter:
```
python -m jupyterlab
```

You can also open the root of the project in VSCode and interact with Jupyter notebooks that way (just make sure you select the `.venv` kernel.)

## Development

Project dependencies are recoreded in the `requirements.in` file. We use [pip-tools](https://github.com/jazzband/pip-tools) to keep the virtual environment in-sync with this file.

If you need to modify this project's dependencies, first edit the `requirements.in` file. Then use pip-tools to regenerate the `requirements.txt` file:
```
python -m piptools compile --resolver=backtracking
```

Next, update the virtual environment with the new or removed packages:
```
python -m piptools sync
```

## Sample Data

The supplied Jupyter notebooks assume there are some SQLite databases in a `data/` directory at the root of this repository. You can download the sample databases from [here](https://github.com/jlefever/ase2023-replication/releases/download/snapshot-1/snapshot-1-dbs.zip). These databases were created with [cochange-tool](https://github.com/jlefever/cochange-tool) and [depends](https://github.com/multilang-depends/depends). This tool takes SQLite databases like these as input.