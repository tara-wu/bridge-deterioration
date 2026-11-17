STATE ?= GA
START ?= 1992
END   ?= 2025
DB    ?= data/warehouse/nbi.duckdb

.PHONY: setup download load dbt test all profile clean

setup:            ## create a virtual env and install everything
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

download:         ## fetch yearly NBI files into data/raw/nbi
	python -m nbi.download --state $(STATE) --start $(START) --end $(END)

load:             ## slice raw files into raw.nbi_records in DuckDB
	python -m nbi.load --raw data/raw/nbi --db $(DB)

dbt:              ## build staging + bridge_year and run all dbt tests
	cd dbt && dbt build --profiles-dir .

all: download load dbt

test:             ## Python + end-to-end tests on synthetic fixture files
	pytest -q

profile:          ## first-look checks on the finished table
	python -m nbi.checks --db $(DB)

clean:
	rm -rf dbt/target dbt/logs $(DB)
