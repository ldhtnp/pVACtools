import argparse
import sys
import csv

def main(args_input = sys.argv[1:]):
    parser = argparse.ArgumentParser('pvacseq combine_parsed_outputs', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'input_files',
        nargs="+",
        help="List of parsed epitope files for different allele-length combinations (same sample)."
    )
    parser.add_argument(
        'output_file', type=argparse.FileType('w'),
        help="Combined output .tsv file."
    )
    parser.add_argument(
        '--top-score-metric',
        choices=['lowest', 'median'],
        default='median',
        help="The ic50 scoring metric to use when filtering epitopes by binding-threshold or minimum fold change. "
             + "lowest: Use the best MT Score and Corresponding Fold Change (i.e. the lowest MT ic50 binding score and corresponding fold change of all chosen prediction methods). "
             + "median: Use the median MT Score and Median Fold Change (i.e. the median MT ic50 binding score and fold change of all chosen prediction methods).",
    )
    parser.add_argument(
        '--file-type',
        choices=['pVACseq', 'pVACfuse', 'pVACbind'],
        default='pVACseq',
        help="Pipeline that created files to be combined."
    )
    args = parser.parse_args(args_input)

    fieldnames = []
    for input_file in args.input_files:
        with open(input_file, 'r') as input_file_handle:
            reader = csv.DictReader(input_file_handle, delimiter='\t')
            if len(fieldnames) == 0:
                fieldnames = reader.fieldnames
            else:
                for fieldname in reader.fieldnames:
                    if fieldname not in fieldnames:
                        fieldnames.append(fieldname)

    rows = []
    for input_file in args.input_files:
        with open(input_file, 'r') as input_file_handle:
            reader = csv.DictReader(input_file_handle, delimiter='\t')
            for row in reader:
                for fieldname in fieldnames:
                    if fieldname not in row:
                        row[fieldname] = 'NA'
                rows.append(row)

    sorted_rows = sorted(rows, key=lambda row: (int(row['Sub-peptide Position'])))
    if args.file_type == 'pVACbind':
        if args.top_score_metric == 'median':
            sorted_rows = sorted(
                sorted_rows,
                key=lambda row: (
                    row['Mutation'],
                    float(row['Median Score']),
                )
            )
        elif args.top_score_metric == 'lowest':
            sorted_rows = sorted(
                sorted_rows,
                key=lambda row: (
                    row['Mutation'],
                    float(row['Best Score']),
                )
            )
    else:
        sorted_rows = sorted(sorted_rows, key=lambda row: (float(row['Corresponding Fold Change']) if row['Corresponding Fold Change'].isdigit() else float('inf')), reverse=True)
        if args.top_score_metric == 'median':
            sorted_rows = sorted(
                sorted_rows,
                key=lambda row: (
                    row['Gene Name'],
                    row['Mutation'],
                    float(row['Median MT Score']),
                )
            )
        elif args.top_score_metric == 'lowest':
            sorted_rows = sorted(
                sorted_rows,
                key=lambda row: (
                    row['Gene Name'],
                    row['Mutation'],
                    float(row['Best MT Score']),
                )
            )


    tsv_writer = csv.DictWriter(args.output_file, list(fieldnames), delimiter = '\t', lineterminator = '\n')
    tsv_writer.writeheader()
    tsv_writer.writerows(sorted_rows)

    args.output_file.close()

if __name__ == "__main__":
    main()
