
import os
import numpy
import sys

for line in sys.stdin:
    ngrams = {}
    text =  line.decode("utf8")
    for start in xrange(len(text) - 20):
        for length in xrange(11, 15):
            ngram = text[start:start+length]
            ngrams.setdefault(ngram, 0)
            ngrams[ngram] += 1           
    for key, val in ngrams:
        sys.stdout.write(key.encode("utf8") + "\t" + str(val) + "\n")
     