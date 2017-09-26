#:/bin/bash

./fetch-market-data.py
./group-orders-by-type-id-and-location.py
rm ./result.txt
./find-haul-route.py
