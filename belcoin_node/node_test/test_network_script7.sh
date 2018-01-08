#!/bin/sh

rm -rf ~/.belcoin
mkdir ~/.belcoin
rm -rf output
mkdir output

pkill -f -9 node

python ../node.py 0 7080 http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084,http://127.0.0.1:7085,http://127.0.0.1:7086 localhost:27870 localhost:27871,localhost:27872,localhost:27873,localhost:27874,localhost:27875,localhost:27876 50050 &>> output/0.txt
python ../node.py 1 7081 http://127.0.0.1:7080,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084,http://127.0.0.1:7085,http://127.0.0.1:7086 localhost:27871 localhost:27870,localhost:27872,localhost:27873,localhost:27874,localhost:27875,localhost:27876 50051 &>> output/0.txt
python ../node.py 2 7082 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7083,http://127.0.0.1:7084,http://127.0.0.1:7085,http://127.0.0.1:7086 localhost:27872 localhost:27870,localhost:27871,localhost:27873,localhost:27874,localhost:27875,localhost:27876 50052 &>> output/0.txt
python ../node.py 3 7083 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7084,http://127.0.0.1:7085,http://127.0.0.1:7086 localhost:27873 localhost:27870,localhost:27871,localhost:27872,localhost:27874,localhost:27875,localhost:27876 50053 &>> output/0.txt
python ../node.py 4 7084 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7085,http://127.0.0.1:7086 localhost:27874 localhost:27870,localhost:27871,localhost:27872,localhost:27873,localhost:27875,localhost:27876 50054 &>> output/0.txt
python ../node.py 5 7085 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084,http://127.0.0.1:7086 localhost:27875 localhost:27870,localhost:27871,localhost:27872,localhost:27873,localhost:27874,localhost:27876 50055 &>> output/0.txt
python ../node.py 6 7086 http://127.0.0.1:7080,http://127.0.0.1:7081,http://127.0.0.1:7082,http://127.0.0.1:7083,http://127.0.0.1:7084,http://127.0.0.1:7085 localhost:27876 localhost:27870,localhost:27871,localhost:27872,localhost:27873,localhost:27874,localhost:27875 50056 &>> output/0.txt

sleep 5

python ../client.py

exit