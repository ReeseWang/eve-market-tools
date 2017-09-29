#!/bin/bash

if [ ! -d db ]; then
	mkdir db
fi
echo "Getting the SQLite conversion of the latest SDE..."
curl https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2 \
	--create-dirs -o ./db/sde.sqlite.bz2
echo "Decompressing bzip2..."
bzip2 -d -v ./db/sde.sqlite.bz2
echo "Done."
