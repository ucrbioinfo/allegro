import os
import multiprocessing


def count_records_in_file(filename):
    return len([1 for line in open(filename) if line.startswith('>')])


def process_file(filename):
    return filename, count_records_in_file(filename)


def process_files(files):
    return [process_file(file) for file in files]


# directory: Path to the directory containing the FASTA files
def get_max(directory: str) -> int:
    # Get the list of files in the directory
    files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.fna')]

    # Set the number of processes
    num_processes = multiprocessing.cpu_count()

    # Split the files into chunks for each process
    chunks = [files[i:i + num_processes] for i in range(0, len(files), num_processes)]

    # Create a pool of processes
    pool = multiprocessing.Pool(processes=num_processes)

    # Map the process_files function to each chunk and get the results
    results = pool.map(process_files, chunks)

    # Flatten the results list
    results = [item for sublist in results for item in sublist]

    # Find the file with the maximum record count
    max_file, max_count = max(results, key=lambda x: x[1])

    # print(f'The file with the most records is {max_file} with {max_count} records.')

    return max_count


# directory: Path to the directory containing the FASTA files
def count_records(directory: str) -> int:
    # Get the list of files in the directory
    files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.fna')]

    # Set the number of processes
    num_processes = multiprocessing.cpu_count()

    # Split the files into chunks for each process
    chunks = [files[i:i + num_processes] for i in range(0, len(files), num_processes)]

    # Create a pool of processes
    pool = multiprocessing.Pool(processes=num_processes)

    # Map the process_files function to each chunk and get the results
    results = pool.map(process_files, chunks)

    # Flatten the results list
    results = [item for sublist in results for item in sublist]

    # Find the sum of the records count
    return sum(t[1] for t in results)