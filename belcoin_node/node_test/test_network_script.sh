#!/bin/sh

rm -rf ~/.belcoin
mkdir ~/.belcoin
rm -rf output
mkdir output

pkill -f -9 node

python ../node.py 0 7080 http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084 localhost:27870 localhost:27871,localhost:27872,localhost:27873,localhost:27874 50050 &>> output/0.txt
python ../node.py 1 7081 http://127.0.0.1:7080,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084 localhost:27871 localhost:27870,localhost:27872,localhost:27873,localhost:27874 50051 &>> output/0.txt
python ../node.py 2 7082 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7083,http://127.0.0.1:7084 localhost:27872 localhost:27870,localhost:27871,localhost:27873,localhost:27874 50052 &>> output/0.txt
python ../node.py 3 7083 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7084 localhost:27873 localhost:27870,localhost:27871,localhost:27872,localhost:27874 50053 &>> output/0.txt
python ../node.py 4 7084 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083 localhost:27874 localhost:27870,localhost:27871,localhost:27872,localhost:27873 50054 &>> output/0.txt

sleep 5

python ../client.py

exit