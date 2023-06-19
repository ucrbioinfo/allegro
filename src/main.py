import sys

import utils.configurator as configurator
import utils.postprocessing as postprocessing
import utils.write_solution_to_file as write_solution
from cython_libs.kirschtorte import KirschtorteCython as coverset  # type: ignore


def main() -> int:
    configurator.greet()  # Guten Tag!
    
    # Read command line arguments and config.yaml
    # Settings specified on the command line have priority over and will replace those in config.yaml
    args = configurator.parse_configurations()
    args = configurator.check_and_fix_configurations(args)  # Warnings and info to help with user error

    # Create the output folder using the output directory and experiment name
    args.output_directory = configurator.create_output_directory(args.output_directory, args.experiment_name)
    
    scorer_settings = configurator.configure_scorer_settings(args)
    configurator.log_args(args)  # Write the current configuration to a log file in the output folder
    
    coversets_obj = coverset(
        beta=args.beta,
        cut_multiplicity=args.multiplicity,
        monophonic_threshold=args.mp_threshold,
        track=args.track,
        num_trials=args.num_trials,
        cas_variant='cas9',
        guide_length=20,
        scorer_name=args.scorer,
        scorer_settings=scorer_settings,
        output_directory=args.output_directory,
        input_directory=args.input_directory,
        file_column_name=args.input_species_path_column,
        input_species_csv_file_path=args.input_species_path,
    )

    output_path = write_solution.write_solution_to_file(
        species_names=coversets_obj.species_names,
        solution=coversets_obj.solution,
        experiment_name=args.experiment_name,
        input_csv_path=args.input_species_path,
        input_directory=args.input_directory,
        paths_csv_column_name=args.input_species_path_column,
        species_names_csv_column_name='species_name',
        output_directory=args.output_directory
    )

    num_clusters = 0
    if args.cluster_guides:
        num_clusters = postprocessing.cluster_solution(
            output_path,
            args.seed_region_is_n_from_pam,
            args.mismatches_allowed_after_seed_region)

    return 0


if __name__ == '__main__':
    sys.exit(main())