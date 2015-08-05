#-*- coding:utf8 -*-
import sys
import re

dict = {}

cond_freqs = {}
prefix_freqs = {}
total_prefixes = 0

def good_word(word):
  for letter in word:
    if not (letter >= u"a" and letter <= u"я" or letter >= u"0" and letter <= u"9" or letter in u"ёй-_"):
      return False
  return True

processed = 0
for line in open("dict.txt"):
  word = line.decode("utf8").split("\t")[0]
  freq = int(line.decode("utf8").split("\t")[1])
  if freq > 1:
    dict[word] = freq
  processed += 1
  if processed % 1000000 == 0:
    sys.stderr.write(str(processed) + "\n")
    sys.stderr.flush()
  
  if freq > 30 and len(word) > 2 and good_word(word): 
    total_prefixes += freq 
    prefix_freqs.setdefault(word[:2], 0)
    prefix_freqs[word[:2]] += freq
    for start in xrange(2, len(word)):
     prefix = word[start - 2:start]
     value = word[start]
     cond_freqs.setdefault(prefix, {}).setdefault(value, 0)
     cond_freqs[prefix][value] += freq
     cond_freqs[prefix].setdefault("__all__", 0)
     cond_freqs[prefix]["__all__"] += freq
for prefix in prefix_freqs.keys():
  prefix_freqs[prefix] = prefix_freqs[prefix] / float(total_prefixes)
  #print prefix.encode("utf8"), prefix_freqs[prefix]

"""
print total_prefixes
for prefix, values in cond_freqs.items():
  print prefix.encode("utf8") + "\t" +  " ".join(value.encode("utf8") + "=" + str(freq) for value, freq in values.items())
exit()
"""

sys.stderr.write("uploaded\n")
sys.stderr.flush()


templates = {}
for line in open("templates.txt"):
  template, freq = line.decode("utf8")[:-1].split("\t")
  templates[template] = int(freq)

values = [char for char in u"абвгдеёжзийклмнопрстуфхцчшщьъэюяы"] + [""]

def get_max_prob(word):
  mult = [(0, "")]
  if word in dict:
   mult = [(dict[word], word)]
  return max(mult)

def find_replacements_simple(word):
  replaces = set()
  for position in xrange(len(word) + 1):
   for first in values:
     replaced = word[:position] + first + word[position + 1:] 
     replaces.add(replaced)
  checked_replaces = [(val in dict and dict[val] or 1, val) for val in replaces if val in dict and good_word(val)]
  checked_replaces.sort(reverse=True)
  return checked_replaces[:100]

def find_replacements(word):
  replaces = set()
  for position in xrange(len(word) + 1):
   for first in values:
    for second in values:
     replaced = word[:position] + first + second + word[position + 1:] 
     replaces.add(replaced)
     if second:
      replaced = word[:position] + first + second + word[position + 2:] 
      replaces.add(replaced)
  checked_replaces = [(val in dict and dict[val] or 1, val) for val in replaces if val in dict and good_word(val)]
  if 0 and not checked_replaces and len(word) > 5:
    second_round = []
    for val in replaces:
      second_round += find_replacements_simple(val)
    checked_replaces = [val for val in set(second_round)]
  checked_replaces.sort(reverse=True)
  return checked_replaces[:100]



def trigram_prob(word):
 if len(word) < 2:
   return 0
 prefix = word[:2]
 prob = prefix in prefix_freqs and prefix_freqs[prefix] or min(prefix_freqs.values())
 for start in xrange(2, len(word)):
   prefix = word[start - 2:start]
   value = word[start]
   if prefix in cond_freqs and value in cond_freqs[prefix]:
     prob *= cond_freqs[prefix][value] / float(cond_freqs[prefix]["__all__"])
   else:
     prob = 0
 return prob
 
def correct(word):
  if word in dict and dict[word] > 10 and good_word(word):
    return word
  if len(word) < 4: 
    return word
  replaces = find_replacements(word)
  if not replaces:
    return word
  if replaces and replaces[0][0] > 50 and (len(replaces) == 1 or replaces[1][0] < 5):
    return replaces[0][1]
  reweighted = []
  for freq, replacement in replaces:
    orig = word
    repl = replacement
    while orig and repl and orig[0] == repl[0]:
     orig = orig[1:]
     repl = repl[1:]
    while orig and repl and orig[-1] == repl[-1]:
     orig = orig[:-1]
     repl = repl[:-1]
    template = orig + "->" + repl 
    templ_freq = template in templates and templates[template] + 1 or 1
    reweighted += [(templ_freq * freq * trigram_prob(replacement), replacement)]
  reweighted.sort(reverse=True)
  #print "---> ", word.encode("utf8"), ", ".join(wrd.encode("utf8") + "=" + str(w)  for w, wrd in reweighted[:10])
  if len(reweighted) == 1 or reweighted[1][0] * 2 < reweighted[0][0]:
    return reweighted[0][1]
  return word

  

def join_broken_words(words):
  for index in xrange(len(words) - 2, 1, -2):
   between = words[index - 1].strip()
   if not between or not (between in u"‒–—―-"):
     continue
   if words[index - 2][0] in "0123456789":
     continue
   if words[index][0] in "0123456789":
     continue
   compound = (words[index - 2] + words[index]).lower()
   if compound in dict and dict[compound] > 50:
     words = words[:index -2] + [words[index - 2] + words[index]] + words[index + 1:]
  return words

import re
by_freq = []
for line in sys.stdin:
 text = line.decode("utf8")[:-1]
 if 1:
   orig_words = [chunk for chunk in re.findall(u"[a-zA-Zа-яА-Я0-9_]+[^\s]*[a-zA-Zа-яА-Я0-9_]+|[a-zA-Zа-яА-Я0-9_]+|[^a-zA-Zа-яА-Я0-9_]+", text)]
   words = join_broken_words(orig_words)
   lowers = [word.lower() for word in words] 
   freqs = [word in dict and dict[word] or 0 for word in lowers[0:len(lowers):2] if len(word) > 1]
   low_freq = sum(1 for freq in freqs if freq < 10)
   if low_freq * 2 > len(freqs) or low_freq < 3:
     continue
 replaced = text
 iter = 0
 while True:
  iter += 1
  if iter > 5:
    break
  orig_words = [chunk for chunk in re.findall(u"[a-zA-Zа-яА-Я0-9_]+[^\s]*[a-zA-Zа-яА-Я0-9_]+|[a-zA-Zа-яА-Я0-9_]+|[^a-zA-Zа-яА-Я0-9_]+", replaced)]
  words = join_broken_words(orig_words)
  corrected = []
  for index in xrange(len(words)):
    word = words[index]
    if index % 2 == 1:
      corrected += [word]
      continue
    lower = word.lower()
    corr_lower = correct(lower)
    if corr_lower == lower:
      corrected += [word]
    else:
      corrected += [corr_lower]
  if "".join(corrected) == replaced:
    break
  replaced = "".join(corrected)
 print text.encode("utf8") 
 print replaced.encode("utf8")
 print
 sys.stdout.flush()

