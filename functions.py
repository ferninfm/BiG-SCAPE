#!/usr/bin/env python

"""
BiG-SCAPE

PI: Marnix Medema

Developers:
Jorge Navarro                   jorge.navarromunoz@wur.nl
Emmanuel (Emzo) de los Santos   E.De-Los-Santos@warwick.ac.uk
Marley Yeong                    marleyyeong@live.nl

Functions used by bigscape.py


# License: GNU Affero General Public License v3 or later
# A copy of GNU AGPL v3 should have been included in this software package in LICENSE.txt.
"""

import os
import subprocess
import sys
from encodings import gbk
from Bio import SeqIO
import copy
import math

global verbose
verbose = False


def create_directory(path, kind, clean):
    try:
        os.mkdir(path)
    except OSError as e:
        # 17 (Linux): "[Errno 17] File exists";
        # 183 (Windows) "[Error 183] Cannot create a file when that file already exists"
        if "Errno 17" in str(e) or "Error 183" in str(e):
            print(" " + kind + " folder already exists")
            if clean:
                print("  Cleaning folder")
                for thing in os.listdir(path):
                    os.remove(os.path.join(path,thing))
        else:
            print("Error: unexpected error when " + kind + " folder")
            sys.exit(str(e))


def get_anchor_domains(filename):
    """Get the anchor/marker domains from a txt file.
    This text file should contain one Pfam id per line"""

    domains = []
    
    try:
        handle = open(filename, 'r')
    except IOError:
        print "You have not provided the anchor_domains.txt file."
        print "if you want to make use of the anchor domains in the DDS distance metric,\
        make a file that contains a Pfam domain on each line."
        return []
        
    raw_domains = handle.readlines()
    for line in raw_domains:
        domains.append(line.strip())
    handle.close()
    return domains
        

def get_domain_list(filename):
    """Convert the Pfam string in the .pfs files to a Pfam list"""
    handle = open(filename, 'r')
    domains_string = handle.readline().strip()
    domains = domains_string.split(" ")
    handle.close()
    
    return domains


def check_overlap(pfd_matrix, overlap_cutoff):
    """Check if domains overlap for a certain overlap_cutoff.
     If so, remove the domain(s) with the lower score."""
    
    delete_list = []
    for i in range(len(pfd_matrix)-1):
        for j in range(i+1, len(pfd_matrix)):
            row1 = pfd_matrix[i]
            row2 = pfd_matrix[j]
            
            #check if we are the same CDS
            if row1[-1] == row2[-1]:
                #check if there is overlap between the domains
                if no_overlap(int(row1[3]), int(row1[4]), int(row2[3]), int(row2[4])) == False:
                    overlapping_nucleotides = overlap(int(row1[3]), int(row1[4]), int(row2[3]), int(row2[4]))
                    overlap_perc_loc1 = overlap_perc(overlapping_nucleotides, int(row1[4])-int(row1[3]))
                    overlap_perc_loc2 = overlap_perc(overlapping_nucleotides, int(row2[4])-int(row2[3]))
                    #check if the amount of overlap is significant
                    if overlap_perc_loc1 > overlap_cutoff or overlap_perc_loc2 > overlap_cutoff:
                        if float(row1[1]) >= float(row2[1]): #see which has a better score
                            delete_list.append(row2)
                        elif float(row1[1]) < float(row2[1]):
                            delete_list.append(row1)

    for lst in delete_list:
        try:
            pfd_matrix.remove(lst)
        except ValueError:
            pass
        
    # for some reason, some coordinates in genbank files have ambiguous 
    # starting/ending positions for the CDS. In this case we need the 
    # absolute start position of each domain so the loci start coordinate
    # needs to be checked
    absolute_start_positions = [] # we have to take care of strandedness of the origin gene
    for row in pfd_matrix:
        if row[7][0] == "<" or row[7][0] == ">":
            row[7] = row[7][1:]
        if row[8][0] == "<" or row[8][0] == ">":
            row[8] = row[8][1:]
        
        loci_start = int(row[7])
        loci_end = int(row[8])
        domain_start = int(row[3])
        domain_end = int(row[4])
        width = 3*(domain_end - domain_start)
        strand = row[9].split(":")[-1]
        if strand == "+":
            absolute_start_positions.append(3*domain_start + loci_start)
        else:
            absolute_start_positions.append(loci_end - 3*domain_start - width)
        
    try:
        # sorted by absolute position: env coordinate start + gene locus start
        pfd_matrix = [x for (y,x) in sorted(zip(absolute_start_positions,pfd_matrix), key=lambda pair:pair[0])]
    except ValueError as e:
        print("Something went wrong during the sorting of the fourth column (ValueError): " + str(e))
        print(pfd_matrix)
        sys.exit()
        
    domains = []
    for row in pfd_matrix:
        domains.append(row[5]) #save the pfam domains for the .pfs file

    return pfd_matrix, domains                       
                        

def write_pfd(pfd_handle, matrix):
    for row in matrix:
        row = "\t".join(row)
        pfd_handle.write(row+"\n")
        
    pfd_handle.close() 
    

def hmmscan(pfam_dir, fastafile, outputdir, name, cores):
    """Runs hmmscan"""
    #removed --noali par

    hmmscan_cmd = "hmmscan --cpu " + str(cores) + " --domtblout " + os.path.join(outputdir, name+".domtable") + " --cut_tc " + os.path.join(pfam_dir,"Pfam-A.hmm") + " " + str(fastafile)
    if verbose == True:
        print("   "+hmmscan_cmd)
    
    subprocess.check_output(hmmscan_cmd, shell=True)
    
    
def get_domains(filename):
    handle = open(filename, 'r')
    domains = []
    for line in handle:
        if line[0] != "#":
            domains.append(filter(None, line.split(" "))[1])
            
    return domains


def no_overlap(locA1, locA2, locB1, locB2):
    """Return True if there is no overlap between two regions"""
    if locA1 < locB1 and locA2 < locB1:
        return True
    elif locA1 > locB2 and locA2 > locB2:
        return True
    else:
        return False


def overlap_perc(overlap, len_seq):
    return float(overlap) / len_seq
    

def overlap(locA1, locA2, locB1, locB2):
    """Returns the amount of overlapping nucleotides"""

    if locA1 < locB1:
        cor1 = locA1
    else:
        cor1 = locB1

    if locA2 > locB2:
        cor2 = locA2
    else:
        cor2 = locB2

    total_region = cor2 - cor1
    sum_len = (locA2 - locA1) + (locB2 - locB1)

    return sum_len - total_region

  
def BGC_dic_gen(filtered_matrix):
    """Generates the: { 'general_domain_name_x' : ['specific_domain_name_1',
     'specific_domain_name_2'] } part of the BGCs variable."""
    bgc_dict = {}
    for row in filtered_matrix:
        header = row[-1] + ":" + row[3] + ":" + row[4]
        try: #Should be faster than performing if key in dictionary.keys()
            bgc_dict[row[5]]
            bgc_dict[row[5]].append(header)
        except KeyError: #In case of this error, this is the first occurrence of this domain in the cluster
           bgc_dict[row[5]]=[header]
            
    return bgc_dict

    
def save_domain_seqs(filtered_matrix, fasta_dict, domains_folder, outputbase):
    """Write fasta sequences for the domains in the right pfam-domain file"""
    for row in filtered_matrix:
        domain = row[5]
        header = row[-1].strip()
        seq = fasta_dict[header] #access the sequence by using the header
        

        domain_file = open(os.path.join(domains_folder, domain + ".fasta"), 'a') #append to existing file
        domain_file.write(">" + header + ":" + row[3] + ":" + row[4] \
        + "\n" + seq[int(row[3]):int(row[4])] + "\n") #only use the range of the pfam domain within the sequence
            
        domain_file.close()


def network_parser(network_file, Jaccardw, DDSw, GKw, anchorboost):
    network = {}
    
    try:
        with open(network_file, "r") as handle:
            next(handle) # ignore first line with column names
            for line in handle:
                if line[0] != "#":
                    strippedline = line.strip().split("\t")
                    
                    # don't read the combined and shared group (last two columns)
                    # as these are generated by write_network_matrix()
                    network[strippedline[0], strippedline[1]] = strippedline[2:6]
                    network[strippedline[0], strippedline[1]].extend(float(x) for x in strippedline[6:-2]) 
        handle.close()
    except IOError:
        sys.exit("Error: Cannot open file " + network_file)
    
    # re-calculate raw distance with potentially new weights
    for (a, b) in network:
        Jaccard = network[a,b][7]
        #DDS = network[a,b][8] <- will be recalculated
        AI = network[a,b][9]
        
        DDS_non_anchor = network[a,b][10]
        DDS_anchor = network[a,b][11]
        S_anchor = network[a,b][12]
        S = network[a,b][13]
        
        # Calculate DDS
        if S_anchor != 0 and S != 0:
            non_anchor_prct = S / (S + S_anchor)
            anchor_prct = S_anchor / (S + S_anchor)
            
            non_anchor_weight = non_anchor_prct / (anchor_prct*anchorboost + non_anchor_prct)
            anchor_weight = anchor_prct*anchorboost / (anchor_prct*anchorboost + non_anchor_prct)
        
            DDS = (non_anchor_weight*DDS_non_anchor) + (anchor_weight*DDS_anchor)
            
        elif S_anchor == 0:
            DDS = DDS_non_anchor
            
        else: #only anchor domains were found
            DDS = DDS_anchor
            
        DDS = 1 - DDS
        
        distance = 1- (Jaccardw * Jaccard) - (DDSw * DDS) - (AIw * AI)
        
        if distance <= 0:
            logscore = float("inf")
        else:
            logscore = -log(distance, 2)
            
        sqrd_similarity = (1-distance)**2
        
        network[a,b][4] = logscore
        network[a,b][5] = distance
        network[a,b][6] = sqrd_similarity
        network[a,b][8] = DDS
        
    return network


def write_network_matrix(matrix, cutoffs_and_filenames, include_singletons, clusterNames, group_dict):
    """
    An entry in the distance matrix is currently (all floats):
      0         1           2      3      4       5    6    7    8      9     10   11
    clus1Idx clus2Idx bgcClassIdx rawD  sqrtSim  Jac  DDS  AI rDDSna  rDDSa   S    Sa
    
    The final row in the network file is currently:
      0      1      2     3      4   5   6     7       8    9   10    11       12
    clus1  clus2  rawD  sqrtSim  J  DDS  AI  rDDSna  rDDSa  S   Sa  combGrp  ShrdGrp
    """
    
    #Open file handles for each cutoff
    networkfiles = {}
    cutoffs, filenames = zip(*cutoffs_and_filenames)
    for cutoff, filename in cutoffs_and_filenames:
        with open(filename, "w") as networkfile:
            networkfile.write("Clustername 1\tClustername 2\tRaw distance\tSquared similarity\tJaccard index\tDDS index\tAdjacency index\traw DDS non-anchor\traw DDS anchor\tNon-anchor domains\tAnchor domains\tCombined group\tShared group\n")
      
    #Dictionaries to keep track of connected nodes, to know which are singletons
    clusterSetAllDict = {}
    clusterSetConnectedDict = {}
    for cutoff in cutoffs:
        clusterSetAllDict[cutoff] = set()
        clusterSetConnectedDict[cutoff] = set()

    for matrix_entry in matrix:
        gc1 = clusterNames[int(matrix_entry[0])]
        gc2 = clusterNames[int(matrix_entry[1])]
        row = [gc1, gc2]
        
        # get AntiSMASH annotations
        clus1group = group_dict[gc1][0]
        clus2group = group_dict[gc2][0]
        
        # add all the other floats
        row.extend(matrix_entry[3:-2])
        
        # add number of anchor/non-anchor domains as integers
        row.append(int(matrix_entry[-2]))
        row.append(int(matrix_entry[-1]))

        # prepare combined group
        if clus1group != "" and clus2group != "": #group1, group2
            row.append(" - ".join(sorted([clus1group,clus2group])))
        elif clus2group != "":
            row.append(clus2group)
        elif clus1group != "":
            row.append(clus1group)
        else:
            row.append("NA")
    
        # prepare share group (if they indeed share it)
        if clus1group == clus2group:
            row.append(clus1group)
        else:
            row.append("")

        for cutoff, filename in cutoffs_and_filenames:
            clusterSetAllDict[cutoff].add(gc1)
            clusterSetAllDict[cutoff].add(gc2)
            
            if row[2] < cutoff:
                clusterSetConnectedDict[cutoff].add(gc1)
                clusterSetConnectedDict[cutoff].add(gc2)
                
                with open(filename, "a") as networkfile:
                    networkfile.write("\t".join(map(str,row)) + "\n")


    #Add the nodes without any edges, give them an edge to themselves with a distance of 0
    if include_singletons == True:
        for cutoff, filename in cutoffs_and_filenames:
            for gc in clusterSetAllDict[cutoff]-clusterSetConnectedDict[cutoff]:
                #Arbitrary numbers for S and Sa domains: 1 of each (logical would be 0,0 but 
                # that could mess re-analysis;
                with open(filename, "a") as networkfile:
                    networkfile.write("\t".join([gc, gc, "0", "1", "1", "1", "1", "0", "0", "1", "1", "", ""]) + "\n")

    #Close all files
    for networkfile in networkfiles.values():
        networkfile.close()


def fasta_parser(handle):
    """Parses a fasta file, and stores it in a dictionary.
    Only works if there are no duplicate fasta headers in the fasta file"""
    
    fasta_dict = {}
    header = ""
    for line in handle:
        if line[0] == ">":
            header=line.strip()[1:]
        else:
            try:
                fasta_dict[header] += line.strip()
            except KeyError:
                fasta_dict[header] = line.strip()

    return fasta_dict


def get_fasta_keys(handle):
    """Parses a fasta file, only stores headers
    """
    
    header_list = []
    for line in handle:
        if line[0] == ">":
            header_list.append(line.strip()[1:])
            
    return header_list


def domtable_parser(gbk, dom_file):
    """Parses the domain table output files from hmmscan"""
    
##example from domain table output:
# target name        accession   tlen query name                                    accession   qlen   E-value  score  bias   #  of  c-Evalue  i-Evalue  score  bias  from    to  from    to  from    to  acc description of target
#------------------- ---------- -----                          -------------------- ---------- ----- --------- ------ ----- --- --- --------- --------- ------ ----- ----- ----- ----- ----- ----- ----- ---- ---------------------
#Lycopene_cycl        PF05834.8    378 loc:[0:960](-):gid::pid::loc_tag:['ctg363_1'] -            320   3.1e-38  131.7   0.0   1   1   1.1e-40   1.8e-36  126.0   0.0     7   285    33   295    31   312 0.87 Lycopene cyclase protein
    
#pfd_matrix columns: gbk filename - score - gene id - first coordinate - second coordinate - pfam id - domain name -start coordinate of gene - end coordinate of gene - cds header
    
    pfd_matrix = []
    try:
        dom_handle = open(dom_file, 'r')
    except IOError:
        print("  Error! Could not find file " + dom_file)
    else:
        for line in dom_handle:        
            if line[0] != "#":
                splitline = filter(None, line.split(" "))
                pfd_row = []
                pfd_row.append(gbk)         #add clustername or gbk filename
                
                pfd_row.append(splitline[13]) #add the score

                header_list = splitline[3].split(":")
                try:
                    pfd_row.append(header_list[header_list.index("gid")+1]) #add gene ID if known
                except ValueError:
                    print "No gene ID in ", gbk
                    pfd_row.append('')
                    
                pfd_row.append(splitline[19])#first coordinate, env coord from
                pfd_row.append(splitline[20])#second coordinate, env coord to
                
                #===================================================================
                # loc_split = header_list[2].split("]") #second coordinate (of CDS) and the direction
                # pfd_row.append(loc_split[1]) #add direction          
                #===================================================================
                
                pfd_row.append(splitline[1]) #pfam id
                pfd_row.append(splitline[0]) #domain name
                pfd_row.append(header_list[header_list.index("loc")+1]) #start coordinate of gene
                pfd_row.append(header_list[header_list.index("loc")+2]) #end coordinate of gene
                
                pfd_row.append(splitline[3])#cds header
                pfd_matrix.append(pfd_row)

    return pfd_matrix


def sort_bgc(product):
    """Sort BGC by its type. Uses AntiSMASH annotations
    (see http://antismash.secondarymetabolites.org/help.html#secmettypes)"""
    # PKS_Type I
    if product == 't1pks':
        return("PKSI")
    # PKS Other Types
    elif product in ('transatpks', 't2pks', 't3pks', 'otherks', 'hglks'):
        return("PKSother")
    # NRPs
    elif product == 'nrps':
        return("NRPS")
    # RiPPs
    elif product in ('lantipeptide', 'thiopeptide', 'bacteriocin', 'linaridin', 'cyanobactin', 'glycocin', 'LAP', 'lassopeptide', 'sactipeptide', 'bottromycin', 'head_to_tail', 'microcin', 'microviridin', 'proteusin'):
        return("RiPPs")
    # Saccharides
    elif product in ('amglyccycl', 'oligosaccharide', 'cf_saccharide'):
        return("Saccharides")
    # Terpenes
    elif product == 'terpene':
        return("Terpene")
    # PKS/NRP hybrids
    elif len(product.split("-")) > 1:
        #print("  Possible hybrid: (" + cluster + "): " + product)
        # cf_fatty_acid category contains a trailing empty space
        subtypes = set(s.strip() for s in product.split("-"))
        if len(subtypes - set(['t1pks', 'transatpks', 't2pks', 't3pks', 'otherks', 'hglks', 'nrps'])) == 0:
            if 'nrps' in subtypes:
                return("PKS-NRP_Hybrids")
            else:
                return("PKSother") # pks hybrids
        elif len(subtypes - set(['lantipeptide', 'thiopeptide', 'bacteriocin', 'linaridin', 'cyanobactin', 'glycocin', 'LAP', 'lassopeptide', 'sactipeptide', 'bottromycin', 'head_to_tail', 'microcin', 'microviridin', 'proteusin'])) == 0:
            return("RiPPs")
        else:
            return("Others") # other hybrid
    # Others
    elif product in ('arylpolyene', 'aminocoumarin', 'ectoine', 'butyrolactone', 'nucleoside', 'melanin', 'phosphoglycolipid', 'phenazine', 'phosphonate', 'other', 'cf_putative', 'resorcinol', 'indole', 'ladderane', 'PUFA', 'furan', 'hserlactone', 'fused', 'cf_fatty_acid', 'siderophore', 'blactam'):
        return("Others")
    # ??
    else:
        return("Others")


def write_parameters(output_folder, options):
    """Write a file with all the details of the run.
    Will overwrite previous versions"""
    
    pf = open(os.path.join(output_folder,"parameters.txt"), "w")
    
    pf.write("Input directory:\t" + options.inputdir + "\n")
    pf.write("Cores:\t" + str(options.cores) + "\n")
    
    pf.write("Verbose:\t" + ("True" if options.verbose else "False"))
    if not options.verbose:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
    
    pf.write("Include disc nodes:\t" + ("True" if options.include_singletons else "False"))
    if not options.include_singletons:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
    
    pf.write("Domain overlap cutoff:\t" + str(options.domain_overlap_cutoff))
    if options.domain_overlap_cutoff == 0.1:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("Minimum size of BGC:\t" + str(options.min_bgc_size))
    if options.min_bgc_size == 0:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")

    #pf.write("Sequence distance networks:\t\"" + str(options.seqdist_networks) + "\"")
    #if options.seqdist_networks == "A":
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
    
    #pf.write("Domain distance networks:\t\"" + str(options.domaindist_networks) + "\"")
    #if options.domaindist_networks == "":
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")

    #pf.write("Jaccard weight:\t" + str(options.Jaccardw))
    #if options.Jaccardw == 0.2:
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
        
    #pf.write("DDS weight:\t" + str(options.DDSw))
    #if options.DDSw == 0.75:
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
        
    #pf.write("GK weight:\t" + str(options.GKw))
    #if options.GKw == 0.05:
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
        
    #pf.write("Anchor domain weight:\t" + str(options.anchorboost))
    #if options.anchorboost == 0.1:
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")

    #pf.write("Output folder for domain fasta files:\t" + options.domainsout)
    #if options.domainsout == "domains":
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
        
    pf.write("Location of Pfam files:\t" + options.pfam_dir)
    if options.pfam_dir == os.path.dirname(os.path.realpath(__file__)):
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("Anchor domains file:\t" + options.anchorfile)
    if options.anchorfile == "anchor_domains.txt":
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("String for exclusion of gbk files:\t" + options.exclude_gbk_str)
    if options.exclude_gbk_str == "final":
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
    
    pf.write("Skip hmmscan?:\t" + ("True" if options.skip_hmmscan else "False"))
    if not options.skip_hmmscan:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("Skip Multiple Alignment?:\t" + ("True" if options.skip_ma else "False"))
    if not options.skip_ma:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("Skip all?:\t" + ("True" if options.skip_all else "False"))
    if not options.skip_all:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
    
    pf.write("Cutoff values for final network:\t" + ",".join([str(c) for c in options.cutoffs]))
    #if options.cutoffs == "1.0":
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
        
    #pf.write("Neighborhood variable for GK:\t" + str(options.nbhood))
    #if options.nbhood == 4:
        #pf.write("\t(default)\n")
    #else:
        #pf.write("\n")
    
    pf.write("\nMA parameters:\n")
    
    pf.write("Additional MAFFT parameters:\t\"" + options.mafft_pars + "\"")
    if options.mafft_pars == "":
        pf.write("\t(default)\n")
    else:
        pf.write("\n")

    pf.write("Alignment method for MAFFT:\t\"" + options.al_method + "\"")
    if options.al_method == "--retree 2":
        pf.write("\t(default)\n")
    else:
        pf.write("\n")

    pf.write("Maxiterate:\t" + str(options.maxit))
    if options.maxit == 1000:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")
        
    pf.write("Threads in MAFFT:\t" + str(options.mafft_threads))
    if options.mafft_threads == -1:
        pf.write("\t(default)\n")
    else:
        pf.write("\n")

    pf.close()

