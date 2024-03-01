#include "allegro/coverset.h"

namespace coversets
{
    CoversetCPP::CoversetCPP(std::size_t num_species, std::size_t guide_length, std::size_t num_trials, std::string output_directory)
    {
        this->num_species = num_species;
        this->guide_length = guide_length;
        this->num_trials = num_trials;
        this->output_directory = output_directory;
        this->bits_required_to_store_seq = guide_length * 2;

        this->all_species_bitset = boost::dynamic_bitset<>(num_species);
    }

    CoversetCPP::~CoversetCPP() {}

    // Called by coverset.pyx -- This is the first function called from Python after the initialization of this class.
    void CoversetCPP::encode_and_save_dna(std::string &seq, char score, unsigned short species_id)
    {
        std::string encoded_str = "";

        for (auto base : seq)
        {
            switch (base)
            {
            case 'A':
                encoded_str += sA_SHIFT;
                break;
            case 'C':
                encoded_str += sC_SHIFT;
                break;
            case 'G':
                encoded_str += sG_SHIFT;
                break;
            case 'T':
                encoded_str += sT_SHIFT;
                break;
            default:
                std::cerr << "Invalid DNA character: " << base << '\n';
            }
        }

        boost::dynamic_bitset<> encoded_bitset = boost::dynamic_bitset<>(encoded_str);

        // If seq already exists
        if (coversets.find(encoded_bitset) != coversets.end())
        {
            // Set the appropriate bit to indicate which species is hit by this guide.
            this->coversets[encoded_bitset].second.set(species_id);

            // todo: Update the average score of this guide
            // need to keep track of how many times this guide has been seen: n
            // new_average = old_average + (new_item - old_average) / (n + 1)
        }
        else
        {
            // If it is the first time we encounter this sequence
            boost::dynamic_bitset<> bitset(this->num_species);
            bitset.set(species_id);

            this->coversets[encoded_bitset] = std::pair<char, boost::dynamic_bitset<>>(score, bitset);
        }

        // Keep a record of which species should be hit. We compare against this later in randomized_rounding
        //  to determine if a set of feasible solutions hits all the required species or not.
        // We do this record keeping here instead of in the constructor because some species
        //  may not contain any guides and should be excluded from consideration (so we don't set those bits).
        this->all_species_bitset.set(species_id);
    }
    
    std::vector<std::pair<std::string, std::string>> CoversetCPP::randomized_rounding(std::vector<operations_research::MPVariable *> feasible_solutions)
    {
        // Algorithm source:
        // https://web.archive.org/web/20230325165759/https://theory.stanford.edu/~trevisan/cs261/lecture08.pdf
        std::cout << "Using randomized rounding with " << this->num_trials << " trials." << std::endl;
        this->log_buffer << "Using randomized rounding with " << this->num_trials << " trials." << std::endl;

        std::unordered_set<std::string> winners;
        std::size_t len_winners = INT_MAX; // Inifinity, initially
        std::size_t trial_with_smallest_size = 0;

        // On each invocation, dist(rng) returns a random floating-point value
        //  uniformly distributed in the range [min, max).
        boost::random::mt19937 rng(std::time(nullptr));
        boost::random::uniform_real_distribution<double> dist(0, 1);

        for (std::size_t trial = 1; trial < num_trials + 1; trial++)
        {
            // Species to cover
            boost::dynamic_bitset<> I_this_trial(this->num_species);
            std::unordered_set<std::string> winners_this_trial;
            std::size_t iterations_this_trial = 100000; // while-loop exit condition in case of bad luck

            while ((I_this_trial != this->all_species_bitset) && (iterations_this_trial != 0))
            {
                iterations_this_trial--;

                for (auto var_ptr : feasible_solutions)
                {
                    operations_research::MPVariable *var = var_ptr;

                    if ((var->solution_value() == 1.0) || (var->solution_value() > dist(rng)))
                    {
                        // Encoded binary DNA sequence
                        boost::dynamic_bitset<> bitset(var->name());

                        // The species bit vector hit by this binary DNA sequence
                        boost::dynamic_bitset<> species_hit_by_this_guide = this->coversets[bitset].second;

                        I_this_trial |= species_hit_by_this_guide;

                        winners_this_trial.insert(var->name());
                    }
                }
            }

            // double score_sum_this_trial = 0.0;
            // for (auto itr = winners_this_trial.begin(); itr != winners_this_trial.end(); itr++)
            // {
            //     boost::dynamic_bitset<> bitset(*itr);
            //     score_sum_this_trial += this->coversets[bitset].first;
            // }

            std::size_t len_winners_this_trial = winners_this_trial.size();

            if (len_winners_this_trial <= len_winners)
            {
                winners = winners_this_trial;
                len_winners = len_winners_this_trial;
                trial_with_smallest_size = trial;
            }
        }

        std::vector<std::pair<std::string, std::string>> decoded_winners;

        std::cout << "Winners are:" << std::endl;
        this->log_buffer << "Winners are:" << std::endl;
        for (auto winner_str : winners)
        {
            boost::dynamic_bitset<> bitset(winner_str);
            boost::dynamic_bitset<> species_hit_by_this_guide = this->coversets[bitset].second;

            std::string buffer;
            boost::to_string(species_hit_by_this_guide, buffer);

            std::string decoded_bitset = decode_bitset(winner_str);
            decoded_winners.push_back(std::pair<std::string, std::string>(decoded_bitset, buffer));

            std::cout << decoded_bitset << std::endl;
            this->log_buffer << decoded_bitset << std::endl;
        }

        return decoded_winners;
    }

    std::vector<std::pair<std::string, std::string>> CoversetCPP::ortools_solver(std::size_t monophonic_threshold, std::size_t beta)
    {
        std::unordered_map<boost::dynamic_bitset<>, std::pair<boost::dynamic_bitset<>, char>> species_already_hit_by_unique_guide;
        std::unordered_map<boost::dynamic_bitset<>, std::unordered_set<boost::dynamic_bitset<>>> hit_species;
        // Create the linear solver with the GLOP backend.
        std::unique_ptr<operations_research::MPSolver> solver(operations_research::MPSolver::CreateSolver("GLOP"));
        const double infinity = solver->infinity(); // Used for constraints to denote >= 1 and <= 1


        // --------------------------------------------------
        // --------------  MP THRESHOLD ---------------------
        // --------------------------------------------------
        this->log_buffer << "Monophonic threshold: " << monophonic_threshold << std::endl;

        if (monophonic_threshold > 0)
        {
            auto it = this->coversets.begin();
            while (it != this->coversets.end())
            {
                unsigned char new_score = it->second.first;
                boost::dynamic_bitset<> new_guide = it->first;
                boost::dynamic_bitset<> species_bitset = it->second.second;

                // Below, we want to keep only one guide per species where that guide hits
                //  only this species and none other.
                // If a species is already hit by a one-hitting-guide and we encounter
                //  another one, mark it for deletion from this->coversets and
                //   skip adding it to hit_species.
                if (species_bitset.count() <= monophonic_threshold)
                {
                    // and if this species already has a representative guide that hits it...
                    if ((species_already_hit_by_unique_guide.find(species_bitset) != species_already_hit_by_unique_guide.end()))
                    {
                        // Compare scores here
                        // if a guide we saw earlier is worse, flag its score.
                        // if current guide is worse, delete it and continue.
                        boost::dynamic_bitset<> old_guide = species_already_hit_by_unique_guide[species_bitset].first;
                        char old_score = species_already_hit_by_unique_guide[species_bitset].second;

                        if (new_score > old_score)
                        {
                            auto it = this->coversets.find(old_guide);
                            it->second.first = 0;  // if a guide we saw earlier is worse, flag its score.
                        }
                        else
                        {
                            it = this->coversets.erase(it);  // if current guide is not better, delete it and continue.
                            continue;  // Do not update the iterator below. The line above does that.
                        }
                    }
                    // If this species still needs a representative guide...
                    else
                    {
                        // Indicate that this species has a representative guide now and does not need another one later.
                        species_already_hit_by_unique_guide[species_bitset] = std::pair<boost::dynamic_bitset<>, char>(new_guide, new_score);
                    }
                }

                it++;
            }

            species_already_hit_by_unique_guide.clear(); // Mark memory as free
        }

        // --------------------------------------------------
        // -------------- VARIABLE CREATION -----------------
        // --------------------------------------------------
        operations_research::MPObjective *const objective = solver->MutableObjective();
        operations_research::MPConstraint *const beta_constraint = solver->MakeRowConstraint(-infinity, beta);

        std::unordered_map<boost::dynamic_bitset<>, operations_research::MPVariable *> map_seq_to_vars;

        auto it = this->coversets.begin();
        while (it != this->coversets.end())
        {
            unsigned char score = it->second.first;

            // Remove redundant guides. Either predicted inefficient by the scorer, 
            //  or marked as not needed above.
            if (score <= 0)
            {
                it = this->coversets.erase(it);
                continue;
            }

            boost::dynamic_bitset<> guide_seq_bitset = it->first;
            boost::dynamic_bitset<> species_bitset = it->second.second;

            // Find the first species hit by this guide and while there are species left to process...
            size_t set_bit_index = species_bitset.find_first();
            while (set_bit_index != boost::dynamic_bitset<>::npos)
            {
                // Create a onehot bitvector for this one species specifically.
                // For three species, this would be:
                //  first iteration: bit vector 001 for the first species,
                //  second iteration: 010 for the second, and then third iteration 100 for the third.
                boost::dynamic_bitset<> species_onehot(species_bitset.size());
                species_onehot.set(set_bit_index);

                // Indicate that this species is hit by this guide.
                // For example, 001: 00110011... when species 1 is hit by this ATAT... guide
                // and on the next iteration, if ATAT hits species 2 as well:
                //  010: 00110011...
                hit_species[species_onehot].insert(guide_seq_bitset);

                // Find the next species hit by this guide for the next iteration.
                // Returns boost::dynamic_bitset<>::npos if no other bits are set.
                set_bit_index = species_bitset.find_next(set_bit_index);
            }

            std::string buffer;
            boost::to_string(guide_seq_bitset, buffer);
            operations_research::MPVariable *const var = solver->MakeNumVar(0.0, 1, buffer);

            map_seq_to_vars[guide_seq_bitset] = var;
            if (beta <= 0)
            {
                objective->SetCoefficient(var, 1);
            }
            else
            {
                objective->SetCoefficient(var, score);
                beta_constraint->SetCoefficient(var, 1);
            }

            it++;
        }

        LOG(INFO) << "Number of variables (guides) = " << solver->NumVariables();
        this->log_buffer << "Number of variables (guides) = " << solver->NumVariables() << std::endl;
        // --------------------------------------------------

        // --------------------------------------------------
        // ------------- CONSTRAINT CREATION ----------------
        // --------------------------------------------------
        for (auto i : hit_species)
        {
            std::vector<operations_research::MPVariable *> vars_for_this_species;
            std::unordered_set<boost::dynamic_bitset<>> seq_bitsets_set = i.second;

            for (auto j : seq_bitsets_set)
            {
                vars_for_this_species.push_back(map_seq_to_vars[j]);
            }

            // All species must be covered by at least 1 guide
            operations_research::MPConstraint *const constraint = solver->MakeRowConstraint(1.0, infinity);
            for (auto k : vars_for_this_species)
            {
                constraint->SetCoefficient(k, 1);
            }
        }

        hit_species.clear(); // Mark memory as free

        LOG(INFO) << "Number of constraints (species) + 1 (beta) = " << solver->NumConstraints();
        this->log_buffer << "Number of constraints (species) + 1 (beta) = " << solver->NumConstraints() << std::endl;
        // --------------------------------------------------

        // Set the objective and solve.
        if (beta > 0)
        {
            LOG(INFO) << "Beta: " << beta << " - Maximizing the the set size considering beta." << std::endl;
            this->log_buffer << "Beta: " << beta << " - Maximizing the the set size considering beta." << std::endl;

            objective->SetMaximization();
        }
        else
        {
            LOG(INFO) << "Beta: " << beta << " - Minimizing the the set size. Disregarding scores and beta." << std::endl;
            this->log_buffer << "Beta: " << beta << " - Minimizing the the set size. Disregarding scores and beta." << std::endl;

            objective->SetMinimization();
        }

        const operations_research::MPSolver::ResultStatus result_status = solver->Solve();

        // Check that the problem has an optimal solution.
        std::cout << "Status: " << result_status << std::endl;
        this->log_buffer << "Status: " << result_status << std::endl;
        if (result_status != operations_research::MPSolver::OPTIMAL)
        {
            LOG(FATAL) << "The problem does not have an optimal solution!";
            this->log_buffer << "The problem does not have an optimal solution!" << std::endl;
        }

        // Save the feasible variables.
        // A feasible variable is any variable with a solution value greater than 0.
        // It has a chance to be in the final solution.
        std::vector<operations_research::MPVariable *> feasible_solutions;
        for (auto i : map_seq_to_vars)
        {
            boost::dynamic_bitset<> seq_bitset = i.first;
            operations_research::MPVariable *var = i.second;

            if (var->solution_value() > 0.0)
            {
                std::cout << decode_bitset(seq_bitset) << " with solution value " << var->solution_value() << std::endl;
                this->log_buffer << decode_bitset(seq_bitset) << " with solution value " << var->solution_value() << std::endl;

                feasible_solutions.push_back(var);
            }
        }

        map_seq_to_vars.clear();

        std::size_t len_solutions = feasible_solutions.size();
        std::cout << "Number of feasible candidate guides: " << len_solutions << std::endl;
        this->log_buffer << "Number of feasible candidate guides: " << len_solutions << std::endl;
        // --------------------------------------------------
        // -------------- RANDOMIZED ROUND ------------------
        // --------------------------------------------------
        std::vector<std::pair<std::string, std::string>> solution_set;

        if (len_solutions > 0)
        {
            solution_set = randomized_rounding(feasible_solutions);
        }
        else
        {
            // Empty -- A problem with 0 feasible solutions (empty inputs or no guides in the fasta files)
            //  still returns an OPTIMAL status by GLOP. Return an empty vector in this edge case.
            // Why would you input no guides? :/
            solution_set = std::vector<std::pair<std::string, std::string>>();
        }

        log_info(this->log_buffer, this->output_directory);
        return solution_set;
    }
}