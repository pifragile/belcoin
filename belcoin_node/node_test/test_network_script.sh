#!/bin/sh

rm -rf ~/.belcoin
mkdir ~/.belcoin
rm -rf output
mkdir output

pkill -f -9 node

python belcoin_node/node.py 0 7080 http://127.0.0.1:7081,http://127.0.0.1:7082 localhost:27870 localhost:27871,localhost:27872 50050 &>> output/0.txt
python belcoin_node/node.py 1 7081 http://127.0.0.1:7080,http://127.0.0.1:7082 localhost:27871 localhost:27870,localhost:27872 50051 &>> output/0.txt
python belcoin_node/node.py 2 7082 http://127.0.0.1:7080,http://127.0.0.1:7081 localhost:27872 localhost:27870,localhost:27871 50052 &>> output/0.txt

sleep 5

python ../client.py

exit