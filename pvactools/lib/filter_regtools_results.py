import os
import pandas as pd

class FilterRegtoolsResults():
    def __init__(self, **kwargs):
        self.input_file  = kwargs['input_file']
        self.output_file = kwargs['output_file']
        self.gtf_df      = kwargs['gtf_df']
        self.score       = kwargs['score']
        self.distance    = kwargs['distance']

    def split_string(self, df, col, delimiter):
        df[col] = df[col].str.split(delimiter)

    def filter_junction_rows(self, junctions):
        # filter on score, strand, and anchor
        filter_junctions = junctions[(junctions['score'] > self.score) & (junctions['strand'] != '?') & (junctions['anchor'].isin(['D', 'A', 'NDA']))].dropna()
        
        # create variant_start col
        filter_junctions['variant_start'] = filter_junctions['variant_info'].str.split(':|-|,', expand=True)[[1]]
        # filter by distance: variant_start > start-distance and variant_start < end+distance
        # does strand matter here - no
        final_filter = filter_junctions[
           (filter_junctions['variant_start'].astype(int) > filter_junctions['junction_start'].astype(int) - self.distance) & 
           (filter_junctions['variant_start'].astype(int) < filter_junctions['junction_stop'].astype(int) + self.distance)
        ].reset_index()

        return final_filter

    def pc_junction_rows(self, filter_junctions):
        # example entry: 0: {'gene_ids': 'ENSG00000122483', 'transcripts': 'ENST00000343253,ENST00000370276,ENST00000401026,ENST00000421014,ENST00000455267'}
        tscript_dict = {i:{'gene_ids': x, 'transcripts': y} for i,(x,y) in enumerate(zip(filter_junctions['gene_ids'], filter_junctions['transcripts']))}
        
        # filter transcripts by protein_coding and transcript_id
        pc_junctions = pd.DataFrame()

        for k,v in tscript_dict.items():

            # subset df by transcript_id
            gtf_transcripts = self.gtf_df[(self.gtf_df['feature'] == 'transcript') & (self.gtf_df['transcript_id'].isin(v['transcripts'].split(',')))]

            if not gtf_transcripts.empty:
                # add to df
                pc_junctions = pd.concat([pc_junctions, gtf_transcripts])

        # subset of self.gtf_df
        return pc_junctions

    def explode_junction_rows(self, filter_junctions):
        # make transcripts/variants from str to transcript list
        self.split_string(filter_junctions, 'transcripts', ',')
        self.split_string(filter_junctions, 'variant_info', ',')

        # explode the transcript list and variant list
        explode_junctions = filter_junctions.explode('transcripts', ignore_index=True).explode('variant_info', ignore_index=True).drop('index', axis=1)
        
        explode_junctions = explode_junctions.rename(columns={'transcripts': 'transcript_id'})

        return explode_junctions

    def merge_and_write(self, pc_junctions, explode_junctions):
        # merge dfs
        merged_df = explode_junctions.merge(pc_junctions, on='transcript_id').drop_duplicates()
        # drop repetitive or unneeded cols
        merged_df = merged_df.drop(columns=['gene_names', 'gene_ids', 'variant_start'])
        # remove spaces from col names
        #merged_df.columns = merged_df.columns.str.replace(r'\s+', '_', regex=True)
        # switch strand to numeral
        merged_df['strand'] = merged_df['strand'].replace(['+','-'], [1,-1])
        # create filtered tsv file
        merged_df.to_csv(self.output_file, sep='\t', index=False)

        return merged_df
    
    def execute(self):
        # open file, rename junction cols for clarity
        junctions = pd.read_csv(self.input_file, sep='\t')
        junctions = junctions.rename(columns={'chrom':'junction_chrom', 'start':'junction_start', 'end':'junction_stop'})

        # filter on score, strand, anchor, and distance; add variant_start column
        filter_junctions = self.filter_junction_rows(junctions)

        # filter transcripts by protein_coding and transcript_id
        pc_junctions = self.pc_junction_rows(filter_junctions)

        # explode the transcript list and variant list
        explode_junctions = self.explode_junction_rows(filter_junctions)

        # merge dfs and create associated filtered tsv file
        filtered_df = self.merge_and_write(pc_junctions, explode_junctions)
        return filtered_df
