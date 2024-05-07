set -ex

python -m drepr \
    examples/dreprs/Mudd-and-Jowitt-2022-Nickel.yml \
    default=examples/tables/Mudd-and-Jowitt-2022-Nickel.csv \
    --outfile examples/ttls/Mudd-and-Jowitt-2022-Nickel.ttl \
    --progfile examples/programs/Mudd-and-Jowitt-2022-Nickel.py

python -m drepr \
    examples/dreprs/Mudd-and-Jowitt-2018-Copper.yml \
    default=examples/tables/Mudd-and-Jowitt-2018-Copper.csv \
    --outfile examples/ttls/Mudd-and-Jowitt-2018-Copper.ttl \
    --progfile examples/programs/Mudd-and-Jowitt-2018-Copper.py

python -m drepr \
    examples/dreprs/Mudd-and-Jowitt-2017-Zinc.yml \
    default=examples/tables/Mudd-and-Jowitt-2017-Zinc.csv \
    --outfile examples/ttls/Mudd-and-Jowitt-2017-Zinc.ttl \
    --progfile examples/programs/Mudd-and-Jowitt-2017-Zinc.py