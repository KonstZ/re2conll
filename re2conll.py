# -*- coding: utf-8 -*-
	
import sys
import os
import argparse
import re

import gzip
import numpy as np

parser = argparse.ArgumentParser(description='RE to CONLL')
parser.add_argument('--re', type=str, help='REs to apply')
parser.add_argument('--data_dir', type=str, help='Folder with docs')
parser.add_argument('--file', type=str, help='Source file')
parser.add_argument('--lines', action='store_true', help='Lines as docs')
parser.add_argument('--bioes', action='store_true', help='Output BEOES encoding')
args = parser.parse_args()

def build_re():
	patterns = filter(lambda line : line and not line.startswith('#') and not line.isspace(), open(args.re).readlines())
	return map(lambda line: re.compile(line.strip().decode('utf8'), flags=re.U+re.M+re.S), patterns)

from pymystem3 import Mystem
mystem = Mystem(grammar_info=False, disambiguation=False)
mystem.start()

def parse_doc(mystem, text):
	morph_parse = mystem.analyze(text)
	current_pos = 0
	offsets = []
	lemmas = []
	words = []
	all_words = []
	for word_parse in morph_parse:
		word = word_parse['text']
		all_words.append(word)
		sword = word.strip(' ').replace('\n', u'\u2028')
		if re.search("\w", sword, flags=re.U):
			words.append(sword)
			analysis = word_parse.get('analysis')
			lemma = analysis[0]['lex'] if analysis else sword
			lemmas.append(lemma.lower())
			offsets.append((current_pos, current_pos+len(word)))
		else:
			for i, w in enumerate(word):
				if w != ' ':
					w = w.replace('\n', u'\u2028')
					words.append(w)
					lemmas.append(w)
					offsets.append((current_pos+i, current_pos+i+1))
		current_pos += len(word)

	return "".join(all_words).rstrip(), words, lemmas, np.asarray(offsets)

def convert_to_BEIOS(word_labels):
	for i in xrange(len(word_labels)):
		if word_labels[i] == "OUT":
			continue
		if i == 0 or not word_labels[i - 1].endswith(word_labels[i]):
			if i + 1 == len(word_labels) or word_labels[i] != word_labels[i+1]:
				word_labels[i] = "S-"+word_labels[i]
			else: 
				word_labels[i] = "B-"+word_labels[i]
		else:
			if i + 1 == len(word_labels) or word_labels[i] != word_labels[i+1]:
				word_labels[i] = "E-"+word_labels[i]
			else: 
				word_labels[i] = "I-"+word_labels[i]
			

def process_text(text, patterns):
	text, words, lemmas, offsets = parse_doc(mystem, text)
	
	word_labels = ["OUT"]*len(words)

	#if not type(patterns) in [list, tuple]:
	#	patterns = [patterns]
	text = re.sub(u"[«»]", '"', text, flags=re.U)	
	for pattern in patterns:
		results = [m.span() + (m.lastgroup if m.lastgroup else "RE",) for m in re.finditer(pattern, text)]
		if not results:
			continue

		current_word = 0
		current_match = 0
		while True:
			while current_word < offsets.shape[0] \
					and offsets[current_word,0] < results[current_match][0]:
				current_word += 1
			if current_word >= offsets.shape[0]:
				break
			while current_match < len(results) \
					and results[current_match][1] < offsets[current_word][0]:
				current_match += 1
			if current_match >= len(results):
				break
			if results[current_match][0] <= offsets[current_word][0] \
					and results[current_match][1] >= offsets[current_word][1]:
				word_labels[current_word] = results[current_match][2]
			current_word += 1		

	if args.bioes:
		convert_to_BEIOS(word_labels)

	#print "#", text.encode('utf8')
	current_sentence = 1
	for i in xrange(len(words)):
		word = words[i].strip(u'\u2028')
		if word:
			print "\t".join([str(current_sentence), word, lemmas[i].strip(u'\u2028'), word_labels[i]]).encode('utf8')
		else:
			current_sentence += 1
			print

def process_doc(fname, pattern):
	if args.lines:
		for line in open(fname):
			process_text(line.strip().decode('utf8'), pattern)
	else:
		text = open(fname).read().decode('utf8')
		process_text(text, pattern)

def process_folder(folder, pattern):
	for fname in os.listdir(folder):
		if fname.endswith(".txt"):
			process_doc(os.path.join(folder, fname), pattern)

patterns = build_re()
if args.file:
	process_text(open(args.file).read().decode('utf8'), patterns)
elif args.data_dir:
	process_folder(args.data_dir, patterns)


