
import os
import numpy
import sys

prev_key = None
total_freq = 0
for line in sys.stdin:
    key, freq = line.decode("utf8").split("\t")
    if key != prev_key:
        sys.stdout.write(prev_key.encode("utf8") + "\t" + str(total_freq) + "\n")
        total_freq = 0
        prev_key = key
    total_freq += int(freq)
sys.stdout.write(prev_key.encode("utf8") + "\t" + str(total_freq) + "\n")
