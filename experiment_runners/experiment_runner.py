config_text = '''
# --------------------------------------------------------------------
# General settings
# --------------------------------------------------------------------
experiment_name: 'train_test'
# ---

# --------------------------------------------------------------------
# Path Settings
# --------------------------------------------------------------------
input_directory: 'data/input/cds/orthogroups/'
# input_directory: 'data/input/genomes/'
input_species_path: 'data/input/final_ncbi_concat_1k_input_species.csv'   # either a .csv file with the right format, or list of species paths
# input_species_path: 'data/input/three.csv'
input_species_path_column: 'cds_file_name'
# input_species_path_column: 'genome_file_name'
# ---

# track_a: any of the containers can be targeted.
# There will be multiplicity targets per container.
# track_e: each container has to be targeted at least multiplicity times,
track: 'track_a'
# ---

# Integer value, default: 1
# In track_a, every species needs to be targeted at least this many times anywhere.
# In track_e, each gene needs to be targeted at least this many times in that gene.
multiplicity: 1
# ---

# Integer value, default: 0
beta: 0   # The final size of the guides set must be <= than this. Think of it as your budget.
          # Set to 0 to disable: this causes ALLEGRO to find the smallest gRNA set IGNORING scores
          # (treats all of the guides as equals).
          # If set to the number of input species, the final size of the set may be up to
          # the number of species you have (worst case, one guide per species).
          # If set to a number HIGHER than the number of species, finds the best #beta guides
          # and ensures each species is hit at least once.
# ---

# Choices: 'dummy' (default), 'ucrispr', 'chopchop_METHOD'
# Choices for METHOD: "XU_2015", "DOENCH_2014", "DOENCH_2016", "MORENO_MATEOS_2015", "CHARI_2015", "G_20", "KIM_2018", "ALKAN_2018", "ZHANG_2019", "ALL"
# For example, scorer: "chopchop_doench_2016"
# scorer: 'ucrispr' uses a faster implementation of 'chopchop_zhang_2019'
# dummy assigns a score of 1.0 to all guides
scorer: 'ucrispr'
# ---

# (Affects running time and memory performance) Default: True
# True reduces running time and reduces memory consumption.
# If True, discards guides with 5 or more repeated 2-mers.
# For example, this cas9 guide will not be in the output: ACCACCACCACCACCACCAC
# since it contains 7 'AC' 2-mers.
# Also discards guides containing repeating 4- or 5-mers such as AAAAA or TTTT.
# Best when used with mode: from_genome as CDS tend not to have these repeats.
filter_repetitive: True
# ---

# (Affects running time and memory performance) Default: 4
# A higher number decreases running time and reduces memory consumption,
# especially when you have millions of guides.
# Pre-select guides that hit only up to this number of species to act as representatives
# for these species. Set to 0 to disable and save all guides to memory (memory inefficient).
mp_threshold: 4
# ---

# (Affects running time performance) Number of randomized rounding trials
# Default: 1000
# A higher number increases running time but attempts to find a smaller cover set.
# Integer value: Only used if the number of feasible guides is above the exhaustive_threshold.
# How many times to run the randomized rounding algorithm? Any value under 1 disables trials.
num_trials: 1000
# ---

# (Affects running time performance) Post-processing. Default: True, 10, 4
# Compresses the output guide set by clustering similar guides.
# Adds a new column 'cluster' to output.csv
cluster_guides: False
seed_region_is_n_from_pam: 10
mismatches_allowed_after_seed_region: 4
# ---
'''

import os
import pandas as pd
import numpy as np

input_csv = 'data/input/final_ncbi_concat_1k_input_species.csv'

df = pd.read_csv(input_csv)
dfs = np.array_split(df, len(df) // 50)  # split input into smaller dataframes of at most 50 rows each

for i, d in enumerate(dfs):
    new_exp_name = 'no_filter_ncbi_split_' + str(i)
    new_path = 'data/input/' + new_exp_name + '.csv'
    d.to_csv(new_path, index=False)  # type: ignore

    context = {
        'experiment_name': new_exp_name,
        'input_species_path': new_path,
        'mode': 'from_genome',
        'include_repetitive': True,
        'mp_threshold': 0
    }

    config_name = 'no_filter_temp_config_' + str(i) + '.yaml'
    with open(config_name, 'w') as f:
        f.write(config_text.format(**context))

    os.system('python src/main.py --config ' + config_name)