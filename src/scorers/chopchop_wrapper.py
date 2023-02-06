import os
import json
import pandas
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from classes.guide_container import GuideContainer
from scorers.scorer_base import Scorer


class ChopChopWrapper(Scorer):
    __slots__ = ['output_directory', 'scoring_method', 'absolute_path_to_chopchop',
    'absolute_path_to_genomes_directory', 'already_made_bowtie_index_for_these_species']

    output_directory: str
    scoring_method: str
    absolute_path_to_chopchop: str
    absolute_path_to_genomes_directory: str
    already_made_bowtie_index_for_these_species: set[str]

    def __init__(self, settings: dict[str, str]) -> None:
        super().__init__(settings=settings)

        self.output_directory = settings['output_directory']
        self.scoring_method = settings['chopchop_scoring_method']
        self.absolute_path_to_chopchop = settings['absolute_path_to_chopchop']
        self.absolute_path_to_genomes_directory = settings['absolute_path_to_genomes_directory']

        self.already_made_bowtie_index_for_these_species = set()


    def configure_chopchop(self) -> None:
        abs_path_to_bowtie = os.path.join(self.absolute_path_to_chopchop, 'bowtie/bowtie')
        abs_path_of_bowtie_indices = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', self.output_directory, 'bowtie_indices'))
        abs_path_to_chopchop_config_local_json = os.path.join(self.absolute_path_to_chopchop, 'config_local.json')

        content = dict()
        with open(abs_path_to_chopchop_config_local_json, 'r') as f:
            content = json.load(f)

        content['PATH']['BOWTIE'] = abs_path_to_bowtie
        content['PATH']['BOWTIE_INDEX_DIR'] = abs_path_of_bowtie_indices

        with open(abs_path_to_chopchop_config_local_json, 'w') as f:
            json.dump(content, f, indent=2)

        
    def make_species_bowtie_index(self, species_name: str) -> None:
        if species_name not in self.already_made_bowtie_index_for_these_species:
            self.already_made_bowtie_index_for_these_species.add(species_name)

            output_directory = self.output_directory + 'bowtie_indices/'
            absolute_path_to_species_genome = os.path.join(self.absolute_path_to_genomes_directory, species_name + '_genomic.fna')

            if not os.path.exists(output_directory):
                os.makedirs(output_directory)

            print('Running bowtie-build for', species_name)
            # conda run -n chopchop path_to/bowtie/bowtie-build ../../data/input/genomes/hpolymorpha_genomic.fna hpoly
            os.system('conda run -n chopchop' + ' ' + self.absolute_path_to_chopchop + 'bowtie/bowtie-build ' + absolute_path_to_species_genome + ' ' + species_name + ' ' + '-q')
            os.system('mv *.ebwt' + ' ' + output_directory)
            print('Bowtie is done.')


    def run_chopchop_for_fasta(
        self, 
        species_name: str,
        target_fasta_path: str, 
        output_directory: str,
        output_path: str,
        ) -> str:

        self.configure_chopchop()

        command = 'conda run -n chopchop ' + \
        self.absolute_path_to_chopchop + "chopchop.py" + \
        ' -F' + \
        ' -Target ' + target_fasta_path + \
        ' -o ' + output_directory + \
        ' -G ' + species_name + \
        ' --scoringMethod ' + self.scoring_method + \
        ' > ' + output_path

        print('Running ChopChop for', species_name)
        print(command)

        os.system(command)

        os.system('rm -rf ' + output_directory + '*.offtargets')
        print('ChopChop is done.')

        return output_path


    def score_sequence(
        self,
        guide_container: GuideContainer,
        ) -> tuple[list[str], list[str], list[str], list[int], list[float]]: 
        silent = True
        
        species_name = guide_container.species_name
        container_name = guide_container.string_id

        output_directory = os.path.join(self.output_directory, 'chopchop_scores/', species_name, '')
        output_path = os.path.join(output_directory, container_name + '_scores' + '.csv')
        target_fasta_path = os.path.join(output_directory, container_name + '_seq.fasta')

        if not os.path.exists(output_directory):
            print('Creating directory', output_directory)
            os.makedirs(output_directory)

        try:
            chopchop_output = pandas.read_csv(output_path, sep='\t')
            
            if not silent:
                print('Scores for {species} {gene} already exist in {path}. Reading existing scores.'.format(
                    species=species_name, 
                    gene=container_name, 
                    path=output_path,
                    )
                )
        except (FileNotFoundError, pandas.errors.EmptyDataError):
            # make chromosome fasta file
            sequence = SeqRecord(Seq(guide_container.sequence), id=guide_container.string_id)
            with open(target_fasta_path, 'w') as f:
                SeqIO.write(sequence, f, 'fasta')

            self.make_species_bowtie_index(species_name)

            output_path = self.run_chopchop_for_fasta(
                species_name=species_name, 
                target_fasta_path=target_fasta_path,
                output_directory=output_directory,
                output_path=output_path,
            )

        # read chopchop output -- remove NGG PAM: Keep only the spacer sequence for cas9
        chopchop_output = pandas.read_csv(output_path, sep='\t')
        chopchop_output['Target sequence'] = chopchop_output['Target sequence'].str[0:-3]

        # Map +/- to F/R -- make a new column.
        equivalent_strand = dict({'+': 'F', '-': 'R'})
        chopchop_output['F/R'] = chopchop_output['Strand'].map(equivalent_strand)

        chopchop_output['Genomic location'] = chopchop_output['Genomic location'].apply(
            lambda x: int(x.split(':')[1])
        )

        return (chopchop_output['Target sequence'].values.tolist(),
                chopchop_output['Target sequence'].values.tolist(),
                chopchop_output['F/R'].values.tolist(),
                chopchop_output['Genomic location'].values.tolist(),
                chopchop_output['Efficiency'].values.tolist()
        )
    