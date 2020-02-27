def get_id_and_seq(fasta):
    """
    Parses fasta file and get sequence ID and corresponding sequence.

    Input:
        - fasta: path to fasta file

    Output:
        generator: tuples of id and seq; (id, seq)
    """
    header = ">"
    seq = ""
    _id = ""

    with open(fasta, 'r') as fh:
        for line in fh:
            # Strip leading and trailing whitespaces
            line = line.strip()

            # Skip if empty line
            if not(line): continue

            # If header line
            if(header in line):
                # Return if both ID and seq not empty
                if(_id and seq):
                    yield (_id, seq)

                # re-initialize seq to be empty string
                seq = ""
                _id = line.strip(header)
            # Non header lines
            else:
                seq = seq + line

        # Last entry
        yield (_id, seq)
