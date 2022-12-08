from classes.guide_container import GuideContainer
from scorers.scorer_base import Scorer
import utils.find_cas9_guides_in_seq


class DummyScorer(Scorer):
    def __init__(self) -> None:
        super().__init__()
        

    def score_sequence(self, guide_container: GuideContainer) -> list[tuple[str, str, float]]:
        '''
        Assigns all guides a score of 1.0
        '''
        sequence = guide_container.get_sequence()
        guide_strand_score_tupe_list = utils.find_cas9_guides_in_seq.find_guides_and_indicate_strand(sequence=sequence)
        return guide_strand_score_tupe_list
