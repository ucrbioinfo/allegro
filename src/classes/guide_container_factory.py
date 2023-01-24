from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from classes.species import Species

import re
from Bio import SeqIO

from classes.gene import Gene
from classes.chromosome import Chromosome
from classes.guide_container import GuideContainer


class GuideContainerFactory:
    def __init__(self, guide_source: str) -> None:
        self.guide_source = guide_source


    def make_guide_containers(self, species_object: Species) -> list[GuideContainer]:
        guide_container_list: list[GuideContainer] = list()

        cds_path = species_object.cds_path
        genome_path = species_object.genome_path
        guide_scorer_obj = species_object.guide_scorer

        match self.guide_source:
            case 'from_orthogroups':
                records = list(SeqIO.parse(open(cds_path), 'fasta'))

                gene_regex = r'\[gene=(.*?)\]'
                tag_regex = r'\[locus_tag=(.*?)\]'
                protein_id_regex = r'\[protein_id=(.*?)\]'
                reference_species_regex = r'\[ref_species=(.*?)\]'
                orthologous_name_regex = r'\[orthologous_to=(.*?)\]'

                for id, cds_record in enumerate(records):
                    tag_match = re.search(tag_regex, cds_record.description)
                    locus_tag = tag_match.group(1) if tag_match is not None else 'N/A'

                    gene_match = re.search(gene_regex, cds_record.description)
                    gene_name = gene_match.group(1) if gene_match is not None else 'N/A'

                    ortho_to_match = re.search(orthologous_name_regex, cds_record.description)
                    ortho_name = ortho_to_match.group(1) if ortho_to_match is not None else 'N/A'

                    protein_id_match = re.search(protein_id_regex, cds_record.description)
                    protein_id = protein_id_match.group(1) if protein_id_match is not None else 'N/A'

                    reference_species_match = re.search(reference_species_regex, cds_record.description)
                    ref_species = reference_species_match.group(1) if reference_species_match is not None else 'N/A'

                    guide_container_list.append(Gene(
                        integer_id=id,
                        gene_name=gene_name,
                        locus_tag=locus_tag,
                        protein_id=protein_id,
                        species=species_object,
                        string_id=cds_record.id,
                        ref_species=ref_species,
                        orthologous_to=ortho_name,
                        sequence=str(cds_record.seq),
                        guide_scorer=guide_scorer_obj,
                        )
                    )

            case 'from_genome':
                records = list(SeqIO.parse(open(genome_path), 'fasta'))
                
                for id, chromosome_record in enumerate(records):
                    guide_container_list.append(Chromosome(
                        integer_id=id,
                        species=species_object,
                        guide_scorer=guide_scorer_obj,
                        string_id=chromosome_record.id,
                        sequence=str(chromosome_record.seq).upper(),
                        )
                    )
                    
            case _:
                print('No such source as {source}. Check config.yaml'.format(source=self.guide_source))
                raise NotImplementedError

        return guide_container_list