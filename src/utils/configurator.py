# Functions imported by ALLEGRO. No need to run it manually.
import os
import re
import sys
import time
import yaml
import pandas
import signal
import argparse
from datetime import timedelta

from utils.shell_colors import bcolors
from utils.iupac_codes import iupac_dict


# Thank you ChatGPT
def sanitize_filename(filename, max_length=255):
    # Remove disallowed characters (e.g., /, \0, *, ?, ", <, >, |)
    sanitized = re.sub(r'[\/\0\*\?"<>\|]', '', filename)
    
    # Replace whitespace characters with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # Optionally, remove leading periods to avoid hidden files, unless it's a special case (e.g., ".", "..")
    if sanitized.startswith('.') and sanitized not in ['.', '..']:
        sanitized = sanitized.lstrip('.')

    # Böse böse...
    if sanitized == '.':
        sanitized = '._'
    elif sanitized == '..':
        sanitized = '.._'
    
    # Shorten the filename to comply with filesystem limits
    if len(sanitized.encode('utf-8')) > max_length:
        # Shorten while trying to preserve file extension
        name, dot, extension = sanitized.rpartition('.')
        if dot and extension and len(extension) <= max_length - 1:
            # Shorten name part, leave room for dot and extension
            name = name[:max_length - len(extension) - 2]
            sanitized = f"{name}.{extension}"
        else:
            # If there's no extension or it's too long, just truncate the name
            sanitized = sanitized[:max_length]
    
    return sanitized


def signal_handler(sig, frame):
    print(f'\n{bcolors.BLUE}>{bcolors.RESET} Interrupted {bcolors.ORANGE}ALLEGRO{bcolors.RESET}. Ciao.')
    sys.exit(0)


class Configurator:
    def __init__(self) -> None:
        self.start_time = time.thread_time()
        
        signal.signal(signal.SIGINT, signal_handler)

        self.target_lengths = {
            'cas9': 20
        }


    def begruessung(self) -> None:
        print(f'{bcolors.BLUE}>{bcolors.RESET} Welcome to {bcolors.ORANGE}ALLEGRO{bcolors.RESET}.')
        print(f'{bcolors.BLUE}>{bcolors.RESET} All unspecified command-line arguments default to the values in config.yaml.')


    # To use CHOPCHOP, ALLEGRO needs a conda environment called 'chopchop' with all the appropriate
    # CHOPCHOP dependencies and python 2.7. If not found, an error is printed out.
    def conda_env_exists(self, env_name: str) -> bool:
        if os.system(f'conda env list | grep {env_name} > /dev/null') == 0:
            return True
        else:
            return False
        

    def parse_configurations(self) -> argparse.Namespace:
        config_parser = argparse.ArgumentParser(add_help=False, formatter_class=argparse.RawTextHelpFormatter)

        help = "- The config file to use. Must be placed in the root folder."
        config_parser.add_argument(
            '-c',
            '--config',
            type=argparse.FileType(mode='r'),
            default='config.yaml',
            help=help,
        )
        
        config_args, remaining_args = config_parser.parse_known_args()

        config_arg_dict = vars(config_args)
        if config_args.config:
            config_arg_dict.update(yaml.load(config_args.config, Loader=yaml.FullLoader))

        parser = argparse.ArgumentParser(
            prog='ALLEGRO: An algorithm for a linear program to enhance guide RNA optimization',
            description='Find the smallest set of guide RNAs that cut through all species.',
            epilog="For more info, visit https://github.com/AmirUCR/allegro",
            parents=[config_parser],
            formatter_class=argparse.RawTextHelpFormatter
        )

        help = "- Name of the experiment. Output directory and file will be labeled with this."
        parser.add_argument(
            '-n',
            '--experiment_name',
            type=str,
            help=help
        )

        help = "- Files in this directory must end with .fna."
        parser.add_argument(
            '--input_directory',
            type=str,
            help=help,
        )


        help = "- The .csv file that includes three columns: species_name, genome_file_name, cds_file_name. genome_file_name rows start with species_name + _genomic.fna. cds_file_name rows start with species_name + _cds.fna.\n" + \
        "- Genome files must be placed in data/input/genomes while cds files must be placed in data/input/cds."
        parser.add_argument(
            '--input_species_path',
            type=str,
            help=help,
        )

        help = "- The desired column name of the .csv file that includes three columns: species_name, genome_file_name, cds_file_name. genome_file_name rows start with species_name + _genomic.fna. cds_file_name rows start with species_name + _cds.fna.\n" + \
        "- Genome files must be placed in data/input/genomes while cds files must be placed in data/input/cds."
        parser.add_argument(
            '--input_species_path_column',
            type=str,
            help=help,
        )

        help = "- Which track to use?\n" + \
        "- Options are 'track_e', 'track_a'\n" + \
        "- track_a: any of the genes in container_names can be targeted. There will be multiplicity targets per guide container (species or genes).\n" + \
        "- track_e: each species/gene has to be targeted at least multiplicity times."
        parser.add_argument(
            '--track',
            type=str,
            help=help,
        )

        help = "- Ensures to cut each species/gene at least this many times. Default: 1"
        parser.add_argument(
            '--multiplicity',
            type=int,
            default=1,
            help=help,
        )

        help = "- Beta represents a loose budge or threshold for the maximum number of guides you would like in the final covering set.\n" + \
        "- This is *not* a guaranteed maximum due to the hardness of the problem. See the topic on Integrality Gap."
        parser.add_argument(
            '--beta',
            type=int,
            default=0,
            help=help,
        )

        help = "- Only used in solving the ILP if there are remaining feasible guides with fractional values after solving the LP.\n" + \
        "- Stop searching for an optimal solution when the size of the set has stopped improving after this many seconds."
        parser.add_argument(
            '--early_stopping_patience',
            type=int,
            help=help,
        )

        parser.add_argument(
            '--filter_by_gc',
            type=bool,
            default=True,
        )

        parser.add_argument(
            '--gc_max',
            type=float,
            default=0.7,
        )

        parser.add_argument(
            '--gc_min',
            type=float,
            default=0.3,
        )

        help = "Supports up to 5 chained IUPAC codes; e.g., 'RYSN' ALLEGRO will output guides that do not contain any of the patterns in this list."
        parser.add_argument(
            '--patterns_to_exclude',
            type=list[str],
            help=help,
            default=['TTTT']
        )

        help = "- True/False boolean, significantly affects running time. True generates a report of gRNA with off-targets."
        parser.add_argument(
            '--output_offtargets',
            type=bool,
            help=help
        )

        help = "- Generate a report with gRNA with fewer <= N mismatches after the seed region.\n" + \
        "- May be 0, 1, 2, or 3."
        parser.add_argument(
            '--report_up_to_n_mismatches',
            type=int,
            help=help,
            default=3
        )

        help = "- Requires output_offtargets=True. In the generated report, discards gRNA with off-targets mismatching " + \
        "in the seed region upstream of PAM. For example, the following will NOT be considered an off-target " + \
        "when this value is set to 1:\n" + \
        "- Target: ACTGACTGACTGACTGACTTAGG\n" + \
        "- gRNA:   ACTGACTGACTGACTGACTGAGG\n" + \
        "                             ^\n" + \
        "- Since A and T mismatch in the seed region."
        parser.add_argument(
            '--seed_region_is_n_upstream_of_pam',
            type=int,
            help=help
        )

        help = '- The directory in which the input csv file with the name of the background fastas to check off-targets against lives.'
        parser.add_argument(
            '--input_species_offtarget_dir',
            type=str,
            help=help,
        )

        help = '- The column in the input csv file with the name of the background fasta to check off-targets against.'
        parser.add_argument(
            '--input_species_offtarget_column',
            type=str,
            help=help,
        )

        help = "- Which scoring method to use? Default: 'dummy'\n" + \
        "- Options are 'chopchop_METHOD', 'ucrispr', 'dummy' where 'dummy' assigns a score of 1.0 to all guides."
        parser.add_argument(
            '--scorer',
            type=str,
            default='dummy',
            help=help,
        )

        help = "- A higher number increases running time while decreasing memory consumption.\n" + \
        "- Pre-select guides that hit only up to this number of species/genes to act as representatives for them."
        parser.add_argument(
            '--mp_threshold',
            type=int,
            help=help,
            default=0
        )

        help = "- (Affects performance) Post-processing. Default: False\n" + \
        "Compresses the output guide set by clustering similar guides; adds a new column to output.csv"
        parser.add_argument(
            '--cluster_guides',
            type=bool,
            default=False,
            help=help,
        )

        help = "- Only used when cluster_guides is True. Default: 5\n" + \
        "- Choose how many mismatches after the seed region is allowed for placing guides with an identical seed region in the same cluster.\n" + \
        "- For example, guides AAACTGGTACTGACTGACCG and AAACCCCTACTGACTGACCG are placed in the same cluster when this number is 3 or higher."
        parser.add_argument(
            '--mismatches_allowed_after_seed_region',
            type=int,
            default=2,
            help=help,
        )

        parser.add_argument(
            '--output_directory',
            type=str,
            default="data/output/"
        )

        help = "- Boolean: True or False. Default: False\n" + \
        " - When a problem is deemed unsolvable by the LP solver (e.g., Status: MPSOLVER_INFEASIBLE), enabling diagnostics will attempt to relax each constraint and resolve the problem. If the new problem with the relaxed constraint is solvable, ALLEGRO outputs the internal name of the culprit gene/species. Currently, to stop this process, you need to find the PID of the python process running ALLEGRO using: $ top and kill it manually: $ kill -SIGKILL PID"
        parser.add_argument(
            '--enable_solver_diagnostics',
            type=bool,
            default=False,
            help=help
        )

        help = '''
        - Only cas9 is supported. Which cas endonuclease to use? Default: 'cas9'. Options are: 'cas9'.
        '''
        parser.add_argument(
            '--cas',
            type=str,
            default='cas9',
            help=help,
        )

        help = '''
        - Only NGG is supported.
        '''
        parser.add_argument(
            '--pam',
            type=str,
            default='NGG',
            help=help,
        )
        
        parser.set_defaults(**config_arg_dict)
        args = parser.parse_args(remaining_args)

        self.args = args

        return args


    def check_and_fix_configurations(self) -> tuple[argparse.Namespace, dict]:
        # ------------------------------------------------------------------------------
        #   experiment_name
        # ------------------------------------------------------------------------------
        # Bitte benehmen Sie sich
        self.args.experiment_name = sanitize_filename(self.args.experiment_name)

        # ------------------------------------------------------------------------------
        #   input_directory
        # ------------------------------------------------------------------------------
        if not os.path.exists(self.args.input_directory):
            print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot find directory {self.args.input_directory}. Did you spell its name (input_directory) correctly? Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   cas
        # ------------------------------------------------------------------------------
        if self.args.cas != 'cas9':
            print(f'{bcolors.RED}> Error{bcolors.RESET}: No cas endonuclease other than Cas9 is currently supported. Do not specify this parameter. Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   PAM
        # ------------------------------------------------------------------------------
        if self.args.pam != 'NGG':
            print(f'{bcolors.RED}> Error{bcolors.RESET}: No PAM other than NGG is currently supported. Do not specify this parameter. Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   input_species_path
        # ------------------------------------------------------------------------------
        try:
            species_df = pandas.read_csv(self.args.input_species_path)
        except pandas.errors.EmptyDataError:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: File {self.args.input_species_path} is empty. Exiting.')
            sys.exit(1)
        except FileNotFoundError:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot find file {self.args.input_species_path}. Did you spell the path/file name (input_species_path) correctly? Exiting.')
            sys.exit(1)
        
        # ------------------------------------------------------------------------------
        #   input_species_path_column
        # ------------------------------------------------------------------------------
        try:
            species_df[self.args.input_species_path_column]
        except KeyError:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot find column "{self.args.input_species_path_column}" in {self.args.input_species_path}. Did you spell the column name (input_species_path_column) correctly? Exiting.')
            sys.exit(1)
        
        # ------------------------------------------------------------------------------
        #   species_name
        # ------------------------------------------------------------------------------
        try:
            species_df["species_name"]
        except KeyError:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot find column "species_name" in {self.args.input_species_path}. Did you format the CSV file correctly? Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   patterns_to_exclude
        # ------------------------------------------------------------------------------
        if self.args.patterns_to_exclude:
            if type(self.args.patterns_to_exclude) == str:
                self.args.patterns_to_exclude = [self.args.patterns_to_exclude]

            patterns_to_remove = list()
            for pattern in self.args.patterns_to_exclude:
                for character in pattern:
                    if character not in iupac_dict:
                        print(f'{bcolors.RED}> Warning{bcolors.RESET}: patterns_to_exclude pattern "{pattern}" contains the letter "{character}" which is not an IUPAC code. Ignoring pattern.')
                        patterns_to_remove.append(pattern)

                if len(pattern) > self.target_lengths[self.args.cas]:
                    print(f'{bcolors.RED}> Warning{bcolors.RESET}: Pattern {pattern} is longer than the length of your guides ({self.target_lengths[self.args.cas]}). Ignoring pattern.')
                    patterns_to_remove.append(pattern)

            for pattern in patterns_to_remove:
                self.args.patterns_to_exclude.remove(pattern)

            # Do not allow more than 5 non-ACTG characters in exclusion patterns
            for pattern in self.args.patterns_to_exclude:
                if sum([i not in ['A', 'C', 'T', 'G'] for i in pattern]) > 5:
                    print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot have more than 5 non-ACTG IUPAC codes in pattern {pattern} due to the exponential number of combinations. Remove {pattern} from the list and retry. Exiting.')
                    sys.exit(1)

        # ------------------------------------------------------------------------------
        #   output_offtargets
        # ------------------------------------------------------------------------------
        if self.args.output_offtargets:
            try:
                species_df[self.args.input_species_offtarget_column]
            except KeyError:
                print(f'{bcolors.RED}> Error{bcolors.RESET}: Cannot find column "{self.args.input_species_offtarget_column}" in {self.args.input_species_path}. Did you format the CSV file correctly? Exiting.')
                sys.exit(1)
        
            if self.args.report_up_to_n_mismatches > 3 or self.args.report_up_to_n_mismatches < 0:
                print(f'{bcolors.RED}> Error{bcolors.RESET}: The value for report_up_to_n_mismatches may be 0, 1, 2, or 3. Exiting.')
                sys.exit(1)

            if self.args.seed_region_is_n_upstream_of_pam < 0:
                print(f'{bcolors.RED}> Warning{bcolors.RESET}: seed_region_is_n_upstream_of_pam ({self.args.seed_region_is_n_upstream_of_pam}) is set to negative. Auto adjusting to 0.')
                self.args.seed_region_is_n_upstream_of_pam = 0

            if not os.path.exists(f'{self.args.input_species_offtarget_dir}'):
                print(f'{bcolors.RED}> Error{bcolors.RESET}: Path {self.args.input_species_offtarget_dir} does not exist. Exiting.')
                sys.exit(1)
            elif len(os.listdir(f'{self.args.input_species_offtarget_dir}')) == 0:
                print(f'{bcolors.RED}> Error{bcolors.RESET}: Path {self.args.input_species_offtarget_dir} exists but is empty. Exiting.')
                sys.exit(1)

        # ------------------------------------------------------------------------------
        #   scorer
        # ------------------------------------------------------------------------------
        # If CHOPCHOP is the selected scorer, set the chopchop scoring method.
        if 'chopchop' in self.args.scorer or 'CHOPCHOP' in self.args.scorer:
            # Set paths for CHOPCHOP
            self.args.absolute_path_to_chopchop = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scorers/chopchop/'))
            self.args.absolute_path_to_genomes_directory = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..', 'data/input/genomes/'))
            
            if self.conda_env_exists('chopchop') == False:
                print(f'{bcolors.RED}> Error{bcolors.RESET}: You have selected CHOPCHOP as the guide RNA scorer. {bcolors.ORANGE}ALLEGRO{bcolors.RESET} will attempt to run CHOPCHOP with a conda environment called "chopchop" that must include python 2.7 and all the other python libraries for running CHOPCHOP.\n')
                print(f'{bcolors.BLUE}>{bcolors.RESET} For more info, see here https://bitbucket.org/valenlab/chopchop/src/master/\n')
                print(f'{bcolors.BLUE}>{bcolors.RESET} {bcolors.ORANGE}ALLEGRO{bcolors.RESET} ships with CHOPCHOP so you do not need to download the repository or set any paths manually. You only need to create a conda environment called "chopchop" with python 2.7, and install any required scorer libraries in it such as scikit-learn, keras, theano, and etc.\n')
                print(f'{bcolors.BLUE}>{bcolors.RESET} When CHOPCHOP is selected as the scorer, you need to place the genome fasta files of every input species in data/input/genomes/ to be used with Bowtie.')
                sys.exit(1)

            split = self.args.scorer.split('_')
            join = '_'.join(split[1:])

            if join == '':
                print(f'{bcolors.RED}> Error{bcolors.RESET}: Please select a scorer for CHOPCHOP in config.yaml (for example, scorer: "chopchop_doench_2016"). Exiting.')
                sys.exit(1)

            self.args.chopchop_scoring_method = join.upper()
            self.args.scorer = 'chopchop'

        # ------------------------------------------------------------------------------
        #   gc_max
        # ------------------------------------------------------------------------------
        if self.args.gc_max < self.args.gc_min:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: gc_max ({self.args.gc_max}) is set to be lower than gc_min ({self.args.gv_min}). Edit these values in the config. Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   gc_min
        # ------------------------------------------------------------------------------
        if self.args.gc_min < 0:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: gc_min ({self.args.gc_min}) is set to negative. Auto adjusting to 0.')
            self.args.gc_min = 0

        # ------------------------------------------------------------------------------
        #   report_up_to_n_mismatches
        # ------------------------------------------------------------------------------
        self.args.report_up_to_n_mismatches = int(self.args.report_up_to_n_mismatches)

        if self.args.report_up_to_n_mismatches > 3:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: report_up_to_n_mismatches ({self.args.report_up_to_n_mismatches}) is set to a value higher than 3. It may only be between 0 to 3. Adjust this value in the config and try again.')

        # ------------------------------------------------------------------------------
        #   mismatches_allowed_after_seed_region
        # ------------------------------------------------------------------------------
        self.args.mismatches_allowed_after_seed_region = int(self.args.mismatches_allowed_after_seed_region)

        if self.args.mismatches_allowed_after_seed_region < 0:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: mismatches_allowed_after_seed_region ({self.args.mismatches_allowed_after_seed_region}) is set to negative. Auto adjusting to 0.')
            self.args.mismatches_allowed_after_seed_region = 0

        # ------------------------------------------------------------------------------
        #   track
        # ------------------------------------------------------------------------------
        if self.args.track not in ['track_a', 'track_e']:
            print(f'{bcolors.RED}> Error{bcolors.RESET}: Unknown track "{self.args.track}" selected in config.yaml. Exiting.')
            sys.exit(1)

        # ------------------------------------------------------------------------------
        #   multiplicity
        # ------------------------------------------------------------------------------
        self.args.multiplicity = int(self.args.multiplicity)

        if self.args.multiplicity < 1:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: Multiplicity is set to {self.args.multiplicity}, a value smaller than 1. Auto adjusting multiplicity to 1.')
            self.args.multiplicity = 1

        # ------------------------------------------------------------------------------
        #   mp_threshold
        # ------------------------------------------------------------------------------
        self.args.mp_threshold = int(self.args.mp_threshold)

        if self.args.mp_threshold <= 0:
            print(f'{bcolors.BLUE}>{bcolors.RESET} mp_threshold is set to {self.args.mp_threshold} and thus disabled. Saving all guides to memory.')
            self.args.mp_threshold = 0

        # ------------------------------------------------------------------------------
        #   mp_threshold & multiplicity
        # ------------------------------------------------------------------------------
        if self.args.mp_threshold > 0 and self.args.mp_threshold < self.args.multiplicity:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: mp_threshold is set to {self.args.mp_threshold}, a positive value smaller than the multiplicity {self.args.multiplicity}.')
            print(f'{bcolors.ORANGE}ALLEGRO{bcolors.RESET} cannot remove all but {self.args.mp_threshold} guides from each container and still ensure each container is targeted at least {self.args.multiplicity} times.')
            print(f'{bcolors.BLUE}>{bcolors.RESET} Auto adjusting mp_threshold to be equal to multiplicity. You may also set mp_threshold to 0 to disable this feature. Refer to the manual for more details.')
            self.args.mp_threshold = self.args.multiplicity

        # ------------------------------------------------------------------------------
        #   beta
        # ------------------------------------------------------------------------------
        self.args.beta = int(self.args.beta)

        if self.args.beta <= 0:
            print(f'{bcolors.BLUE}>{bcolors.RESET} Beta is set to {self.args.beta} and thus disabled.')
            print(f'{bcolors.BLUE}>{bcolors.RESET} {bcolors.ORANGE}ALLEGRO{bcolors.RESET} will minimize the set size.')
            self.args.beta = 0

            if self.args.scorer != 'dummy':
                print(f'{bcolors.BLUE}>{bcolors.RESET} Scorer is set to {self.args.scorer}. {bcolors.ORANGE}ALLEGRO{bcolors.RESET} will score the guides for information only and will not use them in calculations.')
        
        if self.args.scorer == 'dummy' and self.args.beta > 0:
            # No feasible solutions if there are fewer guides than beta
            # Say there are 5 species, 5 guides total, and beta is set to 1. Say that none of the species share any guides.
            # This will ask ALLEGRO to find 1 guide out of 5 to cover all 5 species. There is no solution.
            print(f'{bcolors.BLUE}>{bcolors.RESET} The scorer is set to dummy and beta to the positive value {self.args.beta}. {bcolors.ORANGE}ALLEGRO{bcolors.RESET} will try to find (approximately) {self.args.beta} guides to cover all guide containers.')
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: {bcolors.ORANGE}ALLEGRO{bcolors.RESET} may find that there is no feasible solution if the number of shared guides is fewer than beta.')

        if self.args.beta > 0 and self.args.beta < self.args.multiplicity:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: Beta is set to {self.args.beta}, a positive value smaller than the multiplicity {self.args.multiplicity}')
            print(f'{bcolors.BLUE}>{bcolors.RESET} {bcolors.ORANGE}ALLEGRO{bcolors.RESET} cannot find a total of {self.args.beta} guides while each guide container is required to be targeted at least {self.args.multiplicity} times.')
            print(f'{bcolors.BLUE}>{bcolors.RESET} Auto adjusting beta to be equal to the multiplicity. You may also set beta to 0. Refer to the manual for more details.')
            self.args.beta = self.args.multiplicity

        # ------------------------------------------------------------------------------
        #   early_stopping_patience
        # ------------------------------------------------------------------------------
        self.args.early_stopping_patience = int(self.args.early_stopping_patience)

        if self.args.early_stopping_patience < 1:
            print(f'{bcolors.RED}> Warning{bcolors.RESET}: early_stopping_patience is {self.args.early_stopping_patience} < 1 second. Auto adjusting to 1. ALLEGRO may be able to find a smaller sized solution with a larger patience.')
            self.args.early_stopping_patience = 1

        scorer_settings = self.configure_scorer_settings()

        # Create the output folder using the output directory and experiment name
        self.args.output_directory = self.create_output_directory(self.args.output_directory, self.args.experiment_name)

        return self.args, scorer_settings


    def log_args(self) -> None:
        output_txt_path = os.path.join(self.args.output_directory, self.args.experiment_name + '_config_used.txt')

        with open(output_txt_path, 'w') as f:
            f.write(f'Config used for experiment {self.args.experiment_name}\n')
            for key, value in vars(self.args).items():
                f.writelines(f'{key}: {value}\n')

        self.output_txt_path = output_txt_path
        return output_txt_path


    def log_time(self, total_time_elapsed):
        end_time = time.thread_time()

        # Calculate the elapsed time in seconds
        elapsed_seconds = end_time - self.start_time + total_time_elapsed

        # Convert elapsed_seconds to a timedelta object
        time_elapsed = timedelta(seconds=elapsed_seconds)

        # Extract the time components (hours, minutes, seconds)
        hours = time_elapsed.seconds // 3600
        minutes = (time_elapsed.seconds // 60) % 60
        seconds = time_elapsed.total_seconds() % 60 

        print(f'{bcolors.BLUE}> {bcolors.ORANGE}ALLEGRO{bcolors.RESET} experiment took {hours} hours, {minutes} minutes, {seconds:.2f} seconds.')
        
        with open(self.output_txt_path, 'a') as f:
            f.write(f'ALLEGRO experiment took {hours} hours, {minutes} minutes, {seconds:.2f} seconds.')


    def create_output_directory(self, output_directory: str, experiment_name: str) -> str:
        dir_name = os.path.join(output_directory, experiment_name)

        # Check if the directory already exists
        if os.path.exists(dir_name):
            # If it exists, append a number to the directory name
            i = 1

            while os.path.exists(f'{dir_name}_{i}'):
                i += 1

            dir_name = f'{dir_name}_{i}'

        print(f'{bcolors.BLUE}>{bcolors.RESET} Creating directory {dir_name}')
        os.makedirs(dir_name)

        return dir_name


    def configure_scorer_settings(self) -> dict:
        scorer_settings = dict()

        match str(self.args.scorer).lower():
                case 'chopchop':
                    scorer_settings = {
                        'experiment_name': self.args.experiment_name,
                        'output_directory': self.args.output_directory,
                        'chopchop_scoring_method': self.args.chopchop_scoring_method,
                        'absolute_path_to_chopchop': self.args.absolute_path_to_chopchop,
                        'absolute_path_to_genomes_directory': self.args.absolute_path_to_genomes_directory,
                        'input_species_csv_file_path': self.args.input_species_path
                    }

                case 'dummy':
                    scorer_settings = {
                        'pam': 'NGG',
                        'protospacer_length': self.target_lengths['cas9'],
                        'patterns_to_exclude': self.args.patterns_to_exclude,
                        'context_toward_five_prime': 0,
                        'context_toward_three_prime': 0,
                    }

                case 'ucrispr':
                    scorer_settings = {
                        'pam': 'NGG',
                        'use_secondary_memory': True,
                        'protospacer_length': self.target_lengths['cas9'],
                        'patterns_to_exclude': self.args.patterns_to_exclude,
                        'context_toward_five_prime': 4,  # example: ACAATTTAAAGCTTGCCTCTAACTTGGCCA
                        'context_toward_three_prime': 3,  # 4 refers to ACAA, followed by a 20mer,
                                                            # then TGG PAM, then 3 bases CCA 
                    }

                case _:
                    print(f'{bcolors.RED}> Error{bcolors.RESET}: Unknown scorer "{self.args.scorer}" selected in config.yaml. Exiting.')
                    sys.exit(1)
        
        return scorer_settings