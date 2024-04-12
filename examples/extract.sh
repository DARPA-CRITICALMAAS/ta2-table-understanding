set -ex

python -m drepr \
    examples/dreprs/Mudd-and-Jowitt-2022-Nickel.yml \
    default=examples/tables/Mudd-and-Jowitt-2022-Nickel.csv \
    --outfile examples/ttls/Mudd-and-Jowitt-2022-Nickel.ttl \
    --progfile examples/programs/Mudd-and-Jowitt-2022-Nickel.py