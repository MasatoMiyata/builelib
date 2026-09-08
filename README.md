<div align="center">

# 🏢 Builelib

### Building Energy-modeling Library

**Annual energy consumption calculation program for non-residential buildings**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.3.2-blue.svg)](https://github.com/MasatoMiyata/builelib)
[![uv](https://img.shields.io/badge/managed%20by-uv-7C3AED?logo=astral)](https://docs.astral.sh/uv/)

[日本語](README.ja.md) | [Website](https://builelib.net/) | [Manual](https://builelib.net/manual/) | [Changelog](CHANGELOG.md)

</div>

## Overview

Builelib is a Python library for calculating the annual energy consumption of non-residential buildings. It implements the calculation methods used by Japan's Building Energy Conservation Standard program for non-residential buildings (WEBPRO).

Builelib provides an Excel-based CLI, a Python API, a JSON-based FastAPI application, and a Docker configuration.

### Parse an input sheet in memory

```python
from builelib.input import parse_input_sheet

result = parse_input_sheet("input.xlsx")
print(result.data)
print(result.errors, result.warnings)
```

This API supports `.xlsx` and `.xlsm` WEBPRO input sheets and does not create an intermediate JSON file. Envelope consumers can also import `calculate_wall_u_value` and `calculate_window_performance` from `builelib.input`.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- Git
- Docker, only when running the containerized API

## Setup

### 1. Install uv

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the repository and install dependencies

```bash
git clone https://github.com/MasatoMiyata/builelib.git
cd builelib
uv sync --locked
```

`uv sync` creates the `.venv` virtual environment and installs the dependencies. `--locked` uses the committed `uv.lock` without changing it.

## Run from the CLI

### Run a calculation

```bash
uv run builelib <inputfile>
```

Replace `<inputfile>` with the path to an actual `.xlsx` or `.xlsm` file. Do not type the angle brackets themselves.

Example using the included sample file:

```bash
uv run builelib ./examples/Builelib_inputSheet_sample_001.xlsx
```

Quote paths that contain spaces.

```powershell
uv run builelib "C:\path with spaces\input.xlsx"
```

### Validate input without calculating

Pass `False` as the second argument to parse and validate the Excel input without running the energy calculations.

```bash
uv run builelib <inputfile> False
```

Validation-only mode still writes the converted input, validation results, per-system result files, and a ZIP archive.

### Output files

Output files are written next to the input Excel file. Existing files with the same names are overwritten.

| Output name | Contents |
|---|---|
| `<name>_input.json` | Input data converted from Excel |
| `<name>_validation.json` | Input validation results |
| `<name>_result.json` | Calculation results, including BEI |
| `<name>_result_*.json` | Per-system calculation results |
| `<name>_result_*.csv` | Detailed per-system or time-series results from a full calculation |
| `<name>.zip` | ZIP archive containing the main output files |

## Run from Python

### Calculate from an Excel file

```python
from builelib.runner import calculate

calculate("./examples/Builelib_inputSheet_sample_001.xlsx")
```

`calculate()` writes JSON, CSV, and ZIP files next to the input Excel file instead of returning the results. Pass `False` as the second argument to validate the input only.

```python
calculate("./examples/Builelib_inputSheet_sample_001.xlsx", False)
```

### Calculate from JSON data in memory

`calculate_from_json()` accepts a dictionary that conforms to webproJsonSchema and returns a result dictionary without creating files.

```python
from builelib.runner import calculate_from_json

output = calculate_from_json(input_data)
print(output["result"])
print(output["errors"])
```

## Run the Web API

Start the local development server:

```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

After the server starts, open the interactive API documentation:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

Main endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/calculate` | Calculate from an Excel file on the server |
| `POST` | `/calculate` | Calculate from JSON input data |
| `POST` | `/validate` | Validate JSON input data |
| `GET` | `/schema` | Retrieve the JSON schema |
| `GET` | `/options` | Retrieve the available input options |
| `POST` | `/project/{project_id}/save` | Save a project |
| `GET` | `/project/{project_id}` | Load a project |

## Run with Docker

`compose.yaml` uses an external volume and an external network. Create them once before the first start.

```bash
docker volume create builelib_data
docker network create mynetwork
```

Build and start the service:

```bash
docker compose up --build -d
```

The API documentation is available at <http://localhost:8081/docs>.

Stop the service with:

```bash
docker compose down
```

The external `builelib_data` volume is not removed by `docker compose down`.

## Create input data

Enter the building specifications in a WEBPRO input sheet, using the same input procedure as WEBPRO.

Add the Builelib-specific **SP sheet (Form SP)** to the WEBPRO input sheet to specify detailed calculation conditions. Sample files are available in [`examples`](examples/).

See the [manual](https://builelib.net/manual/) for details.

## Tests

```bash
uv run python -m pytest tests
```

Example that runs a specific test file:

```bash
uv run python -m pytest tests/test_api.py -v
```

## Remove the development environment

Builelib is installed in the repository-local `.venv`. To remove the development environment, move to the repository's parent directory and delete the `builelib` directory.

Windows PowerShell:

```powershell
cd ..
Remove-Item -Recurse -Force .\builelib
```

macOS / Linux:

```bash
cd ..
rm -rf ./builelib
```

## References

- [WEBPRO for non-residential buildings](https://building.app.lowenergy.jp/)
- [Engineering reference](https://webpro-nr.github.io/BESJP_EngineeringReference/index.html)
- [Engineering reference source](https://github.com/WEBPRO-NR/BESJP_EngineeringReference)

## License

[MIT License](LICENSE)

© Masato Miyata
