#-*- coding:utf8 -*-
import sys
import re


def good_word(word):
  for letter in word:
    if not (letter >= u"a" and letter <= u"я" or letter >= u"0" and letter <= u"9" or letter in u"ёй-_"):
      return False
  return True
  
def is_alpha(word):
  for letter in word:
    if not (letter >= u"a" and letter <= u"я" or letter in u"ёй-"):
      return False
  if len(word) < 8 and ("-" in word or "_" in word):
      return False
  return True
  
  
def tokenize(text):
    tokens = [chunk for chunk in re.findall(u"[a-zA-Zа-яА-Я0-9]+[^\s]*[a-zA-Zа-яА-Я0-9_]+|[a-zA-Zа-яА-Я0-9]+|[^a-zA-Zа-яА-Я0-9_\s]+", text)]
    return tokens

"""
out = open("freq_dict.txt", "w")
for line in open("dict.txt"):
  word = line.decode("utf8").split("\t")[0]
  freq = int(line.decode("utf8").split("\t")[1])
  if freq > 50:
      out.write(word.encode("utf8") + "\t" + str(freq) + "\n")
out.close()
exit()
"""


  


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

class TGrammarCorrector():
    def __init__(self):
        self.dict = {}
        self.cond_freqs = {}
        self.prefix_freqs = {}
        self.templates = {}
        self.total_prefixes = 0
        processed = 0
        for line in open("dict.txt"):
          word = line.decode("utf8").split("\t")[0]
          freq = int(line.decode("utf8").split("\t")[1])
          if freq > 1:
            self.dict[word] = freq
          processed += 1
          if processed % 1000000 == 0:
            sys.stderr.write(str(processed) + "\n")
            sys.stderr.flush()
          if freq > 30 and len(word) > 2 and good_word(word): 
            self.total_prefixes += freq 
            self.prefix_freqs.setdefault(word[:2], 0)
            self.prefix_freqs[word[:2]] += freq
            for start in xrange(2, len(word)):
                prefix = word[start - 2:start]
                value = word[start]
                self.cond_freqs.setdefault(prefix, {}).setdefault(value, 0)
                self.cond_freqs[prefix][value] += freq
                self.cond_freqs[prefix].setdefault("__all__", 0)
                self.cond_freqs[prefix]["__all__"] += freq
        for prefix in self.prefix_freqs.keys():
          self.prefix_freqs[prefix] = self.prefix_freqs[prefix] / float(self.total_prefixes)
        self.min_prefix_freq_val = min(self.prefix_freqs.values())
        sys.stderr.write("uploaded\n")
        sys.stderr.flush()
        for line in open("templates.txt"):
          template, freq = line.decode("utf8")[:-1].split("\t")
          self.templates[template] = int(freq)
        self.values = [char for char in u"абвгдеёжзийклмнопрстуфхцчшщьъэюяы"] + [""]

    def find_replacements_simple(self,word):
      replaces = set()
      for position in xrange(len(word) + 1):
       for first in self.values:
         replaced = word[:position] + first + word[position + 1:] 
         replaces.add(replaced)
      checked_replaces = [(val in self.dict and self.dict[val] or 1, val) for val in replaces if val in self.dict and good_word(val)]
      checked_replaces.sort(reverse=True)
      return checked_replaces[:100]
    
    def find_replacements(self, word):
      replaces = set()
      for position in xrange(len(word) + 1):
       for first in self.values:
        for second in self.values:
         replaced = word[:position] + first + second + word[position + 1:] 
         replaces.add(replaced)
         if second:
          replaced = word[:position] + first + second + word[position + 2:] 
          replaces.add(replaced)
      checked_replaces = [(val in self.dict and self.dict[val] or 1, val) for val in replaces if val in self.dict and good_word(val)]
      if 0 and not checked_replaces and len(word) > 5:
        second_round = []
        for val in replaces:
          second_round += self.find_replacements_simple(val)
        checked_replaces = [val for val in set(second_round)]
      checked_replaces.sort(reverse=True)
      return checked_replaces[:100]
    
    
    
    def trigram_prob(self, word):
     if len(word) < 2:
       return 0
     prefix = word[:2]
     prob = prefix in self.prefix_freqs and self.prefix_freqs[prefix] or self.min_prefix_freq_val
     for start in xrange(2, len(word)):
       prefix = word[start - 2:start]
       value = word[start]
       if prefix in self.cond_freqs and value in self.cond_freqs[prefix]:
         prob *= self.cond_freqs[prefix][value] / float(self.cond_freqs[prefix]["__all__"])
       else:
         prob = 0
     return prob
    
    def correct_word(self, word):
      if word in self.dict and self.dict[word] > 10 and good_word(word):
        return word
      if len(word) < 4: 
        return word
      replaces = self.find_replacements(word)
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
        templ_freq = template in self.templates and self.templates[template] + 1 or 1
        reweighted += [(templ_freq * freq * self.trigram_prob(replacement), replacement)]
      reweighted.sort(reverse=True)
      #print "---> ", word.encode("utf8"), ", ".join(wrd.encode("utf8") + "=" + str(w)  for w, wrd in reweighted[:10])
      if len(reweighted) == 1 or reweighted[1][0] * 2 < reweighted[0][0]:
        return reweighted[0][1]
      return word

  

"""
import re
by_freq = []
for line in sys.stdin:
 text = line.decode("utf8")[:-1]
 if 1:
   orig_words = tokenize(text)
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
  orig_words = tokenize(replaced)
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
"""
