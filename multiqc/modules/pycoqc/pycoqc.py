#!/usr/bin/env python

""" MultiQC module to parse output from pycoQC """

from multiqc.modules.base_module import BaseMultiqcModule
from multiqc.plots import bargraph, table, linegraph
from collections import OrderedDict
import yaml
import logging

log = logging.getLogger(__name__)




class MultiqcModule(BaseMultiqcModule):
    def __init__(self):
        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='pycoQC', anchor='pycoqc',
        href="https://a-slide.github.io/pycoQC/",
        info="computes metrics and generates interactive QC plots for Oxford Nanopore technologies sequencing data")
        self.pycoqc_data = {}
        for f in  self.find_log_files('pycoqc'):
            if f['s_name'] in self.pycoqc_data:
                log.debug("Duplicate sample name found in {}! Overwriting: {}".format(f['fn'], f['s_name']))
            self.pycoqc_data[f['s_name']] = self.parse_logs(f['f'])

        if len(self.pycoqc_data) == 0:
            raise UserWarning

        self.table_data, self.reads_data, self.bases_data, self.read_lenght_plot_data, self.quality_plot_data = self.setup_data()

        headers = OrderedDict()
        headers['all_median_read_length'] = {
            'title': 'Median Read Length (All)',
            'description': 'Median Read Length all',
            'scale': 'BuPu',
            'shared_key': 'median_read_len',
        }
        headers['passed_median_read_length'] = {
            'title': 'Median Read Length (Pass)',
            'description': 'Median Read Length pass',
            'scale': 'BuPu',
            'shared_key': 'median_read_len',
        }
        headers['all_reads'] = {
            'title': 'Number of Reads (All)',
            'description': 'Number of Reads all',
            'scale': 'BuGn',
            'shared_key': 'long_read_count',
        }
        headers['passed_reads'] = {
            'title': 'Number of Reads (Pass)',
            'description': 'Number of Reads pass',
            'scale': 'BuGn',
            'shared_key': 'long_read_count',
        }
        headers['all_bases'] = {
            'title': 'Number of Bases (All)',
            'description': 'Number of Bases all',
            'scale': 'OrRd',
            'shared_key': 'bases_count',
        }
        headers['passed_bases'] = {
            'title': 'Number of Bases (Pass)',
            'description': 'Number of Bases pass',
            'scale': 'OrRd',
            'shared_key': 'bases_count',
        }

        self.general_stats_addcols(self.table_data, headers)
        self.write_data_file(self.table_data, 'multiqc_pycoqc')

        pycoqc_table_headers = OrderedDict()
        pycoqc_table_headers['all_n50'] = {
            'namespace': 'pycoQC',
            'title': 'N50 (All)',
            'description': 'N50',
            'scale': 'Greys',
            'shared_key': 'n50',
        }
        pycoqc_table_headers['passed_n50'] = {
            'namespace': 'pycoQC',
            'title': 'N50 (Pass)',
            'description': 'N50',
            'scale': 'Greys',
            'shared_key': 'n50',
        }
        pycoqc_table_headers['all_median_phred_score'] = {
            'namespace': 'pycoQC',
            'title': 'Median PHRED score (All)',
            'description': 'Median PHRED score',
            'scale': 'BuGn',
            'shared_key': 'phred',
        }
        pycoqc_table_headers['passed_median_phred_score'] = {
            'namespace': 'pycoQC',
            'title': 'Median PHRED score (Pass)',
            'description': 'Median PHRED score',
            'scale': 'BuGn',
            'shared_key': 'phred',
        }
        pycoqc_table_headers['all_channels'] = {
            'namespace': 'pycoQC',
            'title': 'Active Channels (All)',
            'description': 'Number of active channels',
            'scale': 'PuBuGn',
            'shared_key': 'channels',
        }
        pycoqc_table_headers['passed_channels'] = {
            'namespace': 'pycoQC',
            'title': 'Active Channels (Pass)',
            'description': 'Number of active channels',
            'scale': 'PuBuGn',
            'shared_key': 'channels',
        }

        self.add_section (
            name = 'pycoQC Statistics table',
            anchor = 'pycoqc_stats',
            description = 'Statistics from pycoQC',
            plot = table.plot(self.table_data, pycoqc_table_headers)
        )

        run_duration_headers = OrderedDict()
        run_duration_headers['all_run_duration'] = {
            'namespace': 'pycoQC',
            'title': 'Run duration',
            'description': 'Run duration',
            'scale': 'PuBuGn'
        }
        self.add_section(
            name = 'Run Duration',
            anchor = 'pycoqc_run_duration',
            description = 'Run Duration',
            plot = table.plot(self.table_data, run_duration_headers)
        )

        self.add_section(
            name = 'pycoQC Reads',
            anchor = 'pycoqc_reads',
            description = 'Reads',
            plot = bargraph.plot(self.reads_data)
        )

        self.add_section(
            name = 'pycoQC Bases',
            anchor = 'pycoqc_bases',
            description = 'Bases',
            plot = bargraph.plot(self.bases_data)
        )

        read_length_config = {
            'data_labels': [
                {'name': 'All', 'ylab': 'Read Density', 'xlab': 'Basecalled Length'},
                {'name': 'Pass', 'ylab': 'Read Density', 'xlab': 'Basecalled Length'}
            ]
        }
        self.add_section(
            name = 'pycoQC read length distribution',
            anchor = 'pycoqc_read_len',
            description = 'pycoQC read length distribution',
            plot = linegraph.plot(self.read_lenght_plot_data, read_length_config)
        )

        qual_config = {
            'data_labels': [
                {'name': 'All', 'ylab': 'Read Density', 'xlab': 'Read Quality Score'},
                {'name': 'Pass', 'ylab': 'Read Density', 'xlab': 'Read Quality Score'}
            ]
        }
        self.add_section(
            name = 'pycoQC PHRED quality score distribution',
            anchor = 'pycoqc_read_qual',
            description = 'pycoQC PHRED quality score distribution',
            plot = linegraph.plot(self.quality_plot_data, qual_config)
        )

    def setup_data(self):
        data_for_table = {}
        reads_data = {}
        bases_data = {}
        length_plot_all = {}
        length_plot_pass = {}
        qual_plot_all = {}
        qual_plot_pass = {}
        for sample, sample_data in self.pycoqc_data.items():
            data_for_table[sample] = {
                'all_median_read_length': sample_data['All Reads']['basecall']['len_percentiles'][50],
                'all_median_phred_score': sample_data['All Reads']['basecall']['qual_score_percentiles'][50],
                'all_n50': sample_data['All Reads']['basecall']['N50'],
                'all_run_duration': sample_data['All Reads']['run']['run_duration'],
                'all_channels': sample_data['All Reads']['run']['active_channels'],
                'all_reads': sample_data['All Reads']['basecall']['reads_number'],
                'all_bases': sample_data['All Reads']['basecall']['bases_number'],
                'passed_median_read_length': sample_data['Pass Reads']['basecall']['len_percentiles'][50],
                'passed_median_phred_score': sample_data['Pass Reads']['basecall']['qual_score_percentiles'][50],
                'passed_n50': sample_data['Pass Reads']['basecall']['N50'],
                'passed_channels': sample_data['Pass Reads']['run']['active_channels'],
                'passed_reads': sample_data['Pass Reads']['basecall']['reads_number'],
                'passed_bases': sample_data['Pass Reads']['basecall']['bases_number'],
                }
            reads_data[sample] = {
                'passed_reads': sample_data['Pass Reads']['basecall']['reads_number'],
                'non_passed_reads': sample_data['All Reads']['basecall']['reads_number'] - sample_data['Pass Reads']['basecall']['reads_number'],
            }
            bases_data[sample] = {
                'passed_bases': sample_data['Pass Reads']['basecall']['bases_number'],
                'non_passed_bases': sample_data['All Reads']['basecall']['bases_number'] - sample_data['Pass Reads']['basecall']['bases_number'],
            }
            length_x_vals_all = sample_data['All Reads']['basecall']['len_hist']['x']
            length_y_vals_all = sample_data['All Reads']['basecall']['len_hist']['y']
            length_plot_all[sample] = dict(zip(length_x_vals_all,length_y_vals_all))
            length_x_vals_pass = sample_data['Pass Reads']['basecall']['len_hist']['x']
            length_y_vals_pass = sample_data['Pass Reads']['basecall']['len_hist']['y']
            length_plot_pass[sample] = dict(zip(length_x_vals_pass,length_y_vals_pass))

            qual_x_vals_all = sample_data['All Reads']['basecall']['qual_score_hist']['x']
            qual_y_vals_all = sample_data['All Reads']['basecall']['qual_score_hist']['y']
            qual_plot_all[sample] = dict(zip(qual_x_vals_all,qual_y_vals_all))
            qual_x_vals_pass = sample_data['Pass Reads']['basecall']['qual_score_hist']['x']
            qual_y_vals_pass = sample_data['Pass Reads']['basecall']['qual_score_hist']['y']
            qual_plot_pass[sample] = dict(zip(qual_x_vals_pass,qual_y_vals_pass))

        return data_for_table, reads_data, bases_data, [length_plot_all, length_plot_pass], [qual_plot_all, qual_plot_pass]

    def parse_logs(self, f):
        data = yaml.load(f, Loader=yaml.FullLoader)
        return data
