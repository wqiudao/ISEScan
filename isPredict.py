#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, random
import os
import argparse
import sys
import datetime
import operator
import concurrent.futures

import constants
import tools
import is_analysis
import pred


def genome2proteome(args2concurrent):
	print("\nBegin to translate genome into proteome.")

	for args in args2concurrent:
		outs = is_analysis.translate_genome_dna_v3(args)
		dna_file = args[0]
		if outs == 0:
			print('Translating genome into proteome for', dna_file, ', return ', outs)
		else:
			e = "Translating genome into proteome for {}, return error!".format(dna_file)
			raise RuntimeError(e)

	print("\nFinish translating genome into proteome.", datetime.datetime.now().ctime())


# proteome_file: (faaFileName, org)
# faaFileName: peptide sequence file output by FragGeneScan
# org: organism id which is the parent directory of DNA sequence file
# outFiles4phmmer: [output_file, ...]
# output_file: file, 
#	hmmer hits file with full path, e.g. /path/output4hmmsearch_illumina_5_cdhit30/HMASM/clusters.single.faa.SRS078176.scaffolds.fa.faa
def prepare4phmmer(clusterSeqFile4phmmer, proteome_files, path_to_hmmsearch_results, nthread):
	args2concurrent = []
	outFiles4phmmer = []
	query = os.path.basename(clusterSeqFile4phmmer)
	for proteome_file in proteome_files:
		faaFileName, org, update = proteome_file
		if not os.path.isfile(faaFileName) or os.stat(faaFileName).st_size == 0:
			print('No such file or Empty file', faaFileName)
			continue
		fileName = '.'.join([query, os.path.basename(faaFileName)])
		output_file = os.path.join(path_to_hmmsearch_results, org, fileName)
		callhmmer = False
		if update == True:
			callhmmer = True
		elif os.path.isfile(output_file) and os.stat(output_file).st_size > 0:
			fp = open(output_file, 'r')
			fp.seek(fp.seek(0,2)-len('# [ok]\n'))
			if '# [ok]\n' in fp.read():
				callhmmer = False
			else:
				# incomplete file missing the last line of the normal file created by hmmer-3.1b2
				callhmmer = True
		else:
			callhmmer = True

		if callhmmer == True:
			args2concurrent.append((clusterSeqFile4phmmer, faaFileName, output_file, nthread))
			tools.makedir(os.path.dirname(output_file))
		else:
			print('Skip phmmer {} against {}'.format(clusterSeqFile4phmmer, faaFileName))

		outFiles4phmmer.append(output_file)
	return (args2concurrent, outFiles4phmmer)

# outFiles4hmmsearch: [output_file, ...]
# output_file: output of hmmsearch, e.g. clusters.faa.hmm.NC_000913.fna.faa, clusters.faa.hmm.SRS014235.scaffolds.fa.faa 
def prepare4hmmsearch(hmms_file, proteome_files, path_to_hmmsearch_results, nthread):
	args2concurrent = []
	outFiles4hmmsearch = []
	query = os.path.basename(hmms_file)
	for proteome_file in proteome_files:
		faaFileName, org, update = proteome_file
		if not os.path.isfile(faaFileName) or os.stat(faaFileName).st_size == 0:
			print('No such file or Empty file', faaFileName)
			continue
		fileName = '.'.join([query, os.path.basename(faaFileName)])
		output_file = os.path.join(path_to_hmmsearch_results, org, fileName)
		callhmmer = False
		if update == True:
			callhmmer = True
		elif os.path.isfile(output_file) and os.stat(output_file).st_size > 0:
			fp = open(output_file, 'r')
			fp.seek(fp.seek(0,2)-len('# [ok]\n'))
			if '# [ok]\n' in fp.read():
				callhmmer = False
			else:
				# incomplete file missing the last line of the normal file created by hmmer-3.1b2
				callhmmer = True
		else:
			callhmmer = True
		if callhmmer == True:
			args2concurrent.append((hmms_file, faaFileName, output_file, nthread))
			tools.makedir(os.path.dirname(output_file))
		else:
			print('Skip hmmsearch {} against {}'.format(hmms_file, faaFileName))

		outFiles4hmmsearch.append(output_file)
	return (args2concurrent, outFiles4hmmsearch)

def hmmSearch(args2concurrent):
	print("\nBegin to profile HMM search against proteome database.", datetime.datetime.now().ctime())

	for args in args2concurrent:
		outs = is_analysis.is_hmmsearch_v2(args)
		hmms_file, proteome_file, hmmHitsFile, nthread = args
		if outs == 0:
			print('Finish Profile HMM searching', hmms_file, ' against', proteome_file, ', output', hmmHitsFile)
		else:
			e = 'Profile HMM searching ' + hmms_file + ' against ' + proteome_file + ', return error!\n'
			raise RuntimeError(e)

	print("\nFinish profile HMM searching against proteome database.", datetime.datetime.now().ctime())

def phmmerSearch(args2concurrent4phmmer):
	print("\nBegin to phmmer search against proteome database.", datetime.datetime.now().ctime())

	for arg in args2concurrent4phmmer:
		outs = is_analysis.is_phmmer(arg)
		seqFile, proteome_file, hmmHitsFile, nthread = arg
		if outs == 0:
			print('Finish phmmer searching', seqFile, ' against', proteome_file, ', output', hmmHitsFile)
		else:
			e = 'phmmer searching ' + seqFile + ' against ' + proteome_file + ', return error!\n'
			raise RuntimeError(e)

	print("\nFinish phmmer searching against proteome database.", datetime.datetime.now().ctime())


# dnaFiles: [(file, org), ..., (file, org)]
def translateGenomeByFGS_v2(dnaFiles, dir2proteome, nthread):
	#seq_type = '1'
	#train_model = 'complete'
	seq_type = '0'
	#train_model = 'sanger_5'
	#train_model = 'sanger_10'
	#train_model = '454_5'
	#train_model = '454_10'
	#train_model = '454_30'
	train_model = 'illumina_5'
	#train_model = 'illumina_10'

	proteome_files = []
	args2concurrent = []
	for item in dnaFiles:
		dna_file, org = item

		outputFile = os.path.basename(dna_file)
		output_file = os.path.join(dir2proteome, org, outputFile)

		faaFile = output_file + '.faa'
		# prepare to translate genome into proteome if protome file has not been available.
		update = False
		if not os.path.isfile(faaFile):
			tools.makedir(os.path.dirname(faaFile))
			args2concurrent.append((dna_file, output_file, seq_type, train_model, nthread))
			update = True
		elif os.stat(faaFile).st_size > 0:
			print('Skip translating {} into {}'.format(dna_file, faaFile))
		else:
			print('No gene was found for', dna_file)
			continue

		proteome_files.append((faaFile, org, update))
	
	# Translate genome into proteome.
	if len(args2concurrent) > 0:
		genome2proteome(args2concurrent)
	else:
		print('Skip translating genome into proteome.')
	return proteome_files

# Based on .faa and .ptt files, it read annotated protein sequence from NCBI 
# and then write a protein sequence file same as the output of FragGeneScan.
# dnaFiles: [(file, org), ..., (file, org)]
def proteinFromNCBI(dnaFiles, dir2proteome):
	proteome_files = []
	# Convert GeneBank protein info (NC_000913.faa and NC_000913.ptt)
	# into FragGeneScan protein file format(NC_000913.fna.faa)
	update = True
	for item in dnaFiles:
		fnaFile, org = item
		#faaFile = fnaFile[:-4] + '.faa'
		#pttFile = fnaFile[:-4] + '.ptt'
		gbkFile = fnaFile[:-4] + '.gbk'
		fgsFile = os.path.join(dir2proteome, org, os.path.basename(fnaFile + '.faa'))
		#tools.gb2fgs4protein(fnaFile, faaFile, pttFile, fgsFile)
		tools.gbk2fgs4protein(fnaFile, gbkFile, fgsFile)
		proteome_files.append((fgsFile, org, update))
	return proteome_files

def isPredict(dna_list, output, removeShortIS, translateGenome,
		nthread=1):
	dnaFiles = tools.rdDNAlist(dna_list)
	path_to_proteome = os.path.join(output, 'proteome')
	if translateGenome == True:
		print ("predict and translate genes from genome sequence into protein database using FragGeneScan program")
		proteome_files = translateGenomeByFGS_v2(dnaFiles, path_to_proteome, nthread)
	else:
		print ("use NCBI protein database")
		proteome_files = proteinFromNCBI(dnaFiles, path_to_proteome)

	clusterSeqFile4phmmer = constants.file4clusterSeqFile4phmmer
	hmms_file = constants.file4clusterHMM

	# HMM searches against protein database
	#
	path_to_hmmsearch_results = os.path.join(output, 'hmm')
	if os.path.isfile(clusterSeqFile4phmmer) and os.stat(clusterSeqFile4phmmer).st_size > 0:
		args2concurrent4phmmer, outFiles4phmmer = prepare4phmmer(clusterSeqFile4phmmer, 
				proteome_files, path_to_hmmsearch_results, nthread)
	else: # no valid clusters.single.faa available
		#args2concurrent4phmmer,outFiles4phmmer = [], []
		e = clusterSeqFile4phmmer + ' is not found or empty!\n'
		raise RuntimeError(e)
	if len(args2concurrent4phmmer) > 0:
		phmmerSearch(args2concurrent4phmmer)

	if os.path.isfile(hmms_file) and os.stat(hmms_file).st_size > 0:
		args2concurrent4hmmsearch, outFiles4hmmsearch = prepare4hmmsearch(hmms_file, 
				proteome_files, path_to_hmmsearch_results, nthread)
	else: # no valid clusters.faa.hmm available
		#args2concurrent4hmmsearch, outFiles4hmmsearch = [], []
		e = hmms_file + ' is not found or empty!\n'
		raise RuntimeError(e)
	if len(args2concurrent4hmmsearch) > 0:
		hmmSearch(args2concurrent4hmmsearch)

	# Select significant ones (predictions) from hits returned by HMM search
	hitsFile = outFiles4phmmer + outFiles4hmmsearch
	if len(hitsFile) > 0:
		args4pred = {
			'dna_list': dna_list,
			'output': output,
			'path_to_proteome': path_to_proteome,
			'path_to_hmmsearch_results': path_to_hmmsearch_results,
			'hitsFile': hitsFile,
			'removeShortIS' : removeShortIS,
			'nthread': nthread,
			}
		pred.pred(args4pred)
		if removeShortIS is False:
			print('Both complete and partial IS elements are reported.')
		else:
			print('Only complete IS elements are reported.')
	else:
		e = 'No hit was returned by HMM search against protein database. ' + datetime.datetime.now().ctime()
		print(e)
