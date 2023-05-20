#ifndef COVERSETCPP_H
#define COVERSETCPP_H

#include <string>
#include <vector>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>

#include <boost/dynamic_bitset.hpp>

#include "allegro/logger.h"
#include "allegro/definitions.h"
#include "allegro/decode_bitset.h"
#include "allegro/ilp_approximators.h"

#include "ortools/linear_solver/linear_solver.h"

namespace coversets
{
    class CoversetCPP
    {
    private:
        std::size_t num_trials;
        std::size_t num_containers;
        std::size_t guide_length;
        std::string output_directory;
        std::size_t bits_required_to_store_seq;
        boost::dynamic_bitset<> all_containers_bitset;
        std::ostringstream log_buffer;

        // guide bitvector --> (score, bitvector of species it hits)
        // The width of the guide bitvector is 2 * guide length AKA this->(std::size_t) bits_required_to_store_seq
        std::unordered_map<boost::dynamic_bitset<>, std::pair<char, boost::dynamic_bitset<>>> coversets;

    public:
        CoversetCPP(
            std::size_t num_containers,
            std::size_t guide_length,
            std::size_t num_trials,
            std::string output_directory);

        ~CoversetCPP();

        std::vector<std::pair<std::string, std::string>> ortools_solver(
            std::size_t container_cut_multiplicity,
            std::size_t mp_threshold,
            std::size_t beta);

        int encode_and_save_dna(
            std::string seq,
            std::size_t score,
            std::size_t container_id);
    };
}

#endif