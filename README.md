# QSafeRx — updated Qure frontend + Qiskit backend + DailyMed benchmark

This folder uses the supplied new Medication Galaxy frontend as the web UI while preserving the supplied Qure FastAPI backend and bundled DailyMed-derived benchmark data unchanged.

## Run on macOS / Linux

```bash
cd QSafeRx_merged
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or simply:

```bash
./run.sh
```

Then open:

**http://127.0.0.1:8000**

## Run on Windows

```bat
run.bat
```

## Important

You do **not** need to run `pip install -e .` to start the website. The previous version attempted an editable package install and setuptools interpreted `app`, `web`, and `data` as multiple top-level packages. This version uses `requirements.txt` for the runnable app, and `pyproject.toml` has explicit setuptools package discovery for `app*` if packaging is needed later.

## Main integrated API

- `GET /api/health`
- `GET /api/local/catalog`
- `POST /api/local/optimize`
- Existing RxNorm/openFDA endpoints remain available under `/api/...`.

## Local benchmark

The bundled benchmark contains 10 drugs, 6 required conditions, and DailyMed-derived interaction evidence. The benchmark patient/condition instance is synthetic and is not a real patient.

## Quantum method

The local optimization route uses the supplied Qiskit Grover implementation and compares its result against exhaustive classical enumeration over the same search space. The app reports qubits, Grover iterations, circuit depth, shots, and whether the quantum candidate matches the classical optimum.

## Safety

QSafeRx is a computational research prototype for candidate regimen selection under predefined constraints. It is not a medical device, prescription engine, or clinical recommendation system.


## Frontend update

The supplied new Qure frontend replaces the previous `web/index.html`. Backend routes, optimization code, and bundled benchmark data are preserved. The UI includes a small backend health indicator when served through FastAPI.

## Patient database

Patients are persisted in `data/patients.db` using SQLite. The Patients page now supports:

- `+ Add patient` — enter name, age, sex, conditions, and daily pill limit and save to SQLite.
- `Edit patient` — update an existing patient and persist the changes.
- `Load into screening` — use a saved patient for the existing screening UI.

The database is initialized with the three demo patients that were previously hardcoded in the frontend.

## Frontend drug-catalog integration

The final frontend no longer keeps a separate hard-coded 8-drug list. On startup it calls `GET /api/local/catalog` and uses the returned catalog as the single source of truth for:

- Medication Galaxy nodes and connections
- Drug Library search/filtering
- Interaction Matrix
- Candidate-condition filtering
- Grover's browser-side demonstration search space
- Dashboard combination counts
- Command-palette drug search

The bundled benchmark currently exposes 10 drugs and 6 conditions. The Grover demo therefore adapts its search space automatically to `2^N` candidate states instead of assuming 8 drugs / 256 states.

## Patient-specific drug selection

The latest build personalizes the optimization candidate set to the patient's selected health conditions. When no explicit candidate list is supplied, the backend selects only drugs with verified coverage for at least one requested condition; the feasibility rules still require every selected condition to be covered and enforce interaction and pill-limit constraints.

The Medication Galaxy and Drug Library still expose the full catalog, but clearly mark which medicines are candidates for the current patient. Non-relevant medicines cannot be added to the patient-specific basket from those views.

Custom/free-text patient conditions can be saved. The bundled benchmark will not invent drug coverage for an unsupported custom condition; optimization reports that verified coverage is missing until appropriate coverage data is added.
