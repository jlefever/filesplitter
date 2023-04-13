# File Splitter

This is an experimental tool that breaks apart god files.

## Usage

Currently, we do not provide a distributable package (i.e. something that could be installed with pip.) Instead, work is done by cloning the repository and using the provided minimal CLI or through a Jupyter notebook. 
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

## Development

Project metadata and dependencies are kept in the `pyproject.toml` file (see [here](https://snarky.ca/what-the-heck-is-pyproject-toml/) if unfamiliar.) We use [pip-tools](https://github.com/jazzband/pip-tools) to make it easier to keep the virtual environment in-sync with this file.

To add a new dependency, first edit the `dependencies` key of the `pyproject.toml` file. Then install pip-tools into your virtual environment if not already installed.
```
# Activate the ".venv" virtual environment
source .venv/bin/activate

# Install pip-tools
python -m pip install pip-tools
```

Next, re-generate the `requirements.txt` file.
```
python -m piptools compile
```

Finally, update the virtual environment with the new or removed packages.
```
python -m piptools sync
```
