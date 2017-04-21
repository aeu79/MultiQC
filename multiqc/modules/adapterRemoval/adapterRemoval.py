#!/usr/bin/env python

""" MultiQC module to parse output from Adapter Removal """

from __future__ import print_function
from collections import OrderedDict
import logging

from multiqc import config
from multiqc.plots import bargraph, linegraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Adapter Removal',
        anchor='adapterRemoval', target='Adapter Removal',
        href='https://github.com/MikkelSchubert/adapterremoval',
        info=" rapid adapter trimming, identification, and read merging ")

        self.__read_type = None
        self.__collapsed = None
        self.s_name = None
        self.adapter_removal_data = {}

        self.len_dist_plot_data = {
            'mate1': dict(),
            'mate2': dict(),
            'singleton': dict(),
            'collapsed': dict(),
            'collapsed_truncated': dict(),
            'discarged': dict(),
            'all': dict(),
        }

        parsed_data = None
        for f in self.find_log_files('adapterRemoval', filehandles=True):
            self.s_name = f['s_name']
            try:
                parsed_data = self.parse_settings_file(f)
            except UserWarning:
                continue
            if parsed_data is not None:
                self.adapter_removal_data[self.s_name] = parsed_data

        if len(self.adapter_removal_data) == 0:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.adapter_removal_data)))

        # Write parsed report data to a file
        self.write_data_file(self.adapter_removal_data, 'multiqc_adapter_removal')

        # add data to Basic Stats Table
        self.adapter_removal_stats_table()

        # Start the sections
        #self.sections = list()

        self.adapter_removal_retained_chart()
        self.adapter_removal_length_dist_plot()

    def parse_settings_file(self, f):

        self.result_data = {
            'total': None,
            'unaligned': None,
            'aligned': None,
            'reads_total': None,
            'retained': None,
            'percent_aligned': None,
        }

        settings_data = {'header': []}

        block_title = None
        for i, line in enumerate(f['f']):

            line = line.rstrip('\n')
            if line == '':
                continue

            if not block_title:
                block_title = 'header'
                settings_data[block_title].append(str(line))
                continue

            if line.startswith('['):
                block_title = str(line.strip('[]'))
                settings_data[block_title] = []
                continue

            settings_data[block_title].append(str(line))

        # set data for further working
        self.set_result_data(settings_data)

        return self.result_data

    def set_result_data(self, settings_data):
        # set read and collapsed type
        self.set_ar_type(settings_data['Length distribution'])

        # set result_data
        self.set_trim_stat(settings_data['Trimming statistics'])
        self.set_len_dist(settings_data['Length distribution'])

    def set_ar_type(self, len_dist_data):
        head_line = len_dist_data[0].rstrip('\n').split('\t')
        self.__read_type = 'paired' if head_line[2] == 'Mate2' else 'single'
        self.__collapsed = True if head_line[-3] == 'CollapsedTruncated' else False

        # biological/technical relevance is not clear -> skip
        if self.__read_type == 'single' and self.__collapsed:
            log.warning("Case single-end and collapse is not " \
                        "implemented -> File %s skipped" % self.s_name)
            raise UserWarning

    def set_trim_stat(self, trim_data):
        required = ['total', 'unaligned', 'aligned', 'discarded_m1', 'singleton_m1', 'retained', 'discarded_m2', 'singleton_m2',
                    'full-length_cp', 'truncated_cp']
        data_pattern = {'total': 0,
                        'unaligned': 1,
                        'aligned': 2,
                        'discarded_m1': 3,
                        'singleton_m1': 4,
                        'retained': 6}

        if self.__read_type == 'paired':
            data_pattern['discarded_m2'] = 5
            data_pattern['singleton_m2'] = 6
            if not self.__collapsed:
                data_pattern['retained'] = 8
            else:
                data_pattern['full-length_cp'] = 8
                data_pattern['truncated_cp'] = 9
                data_pattern['retained'] = 10

        for field in required:
            if field in data_pattern:
                tmp = trim_data[data_pattern[field]]
                value = tmp.split(': ')[1]
                self.result_data[field] = int(value)
            else:
                self.result_data[field] = 0

        reads_total = self.result_data['total']
        aligned_total = self.result_data['aligned']
        unaligned_total = self.result_data['unaligned']
        if self.__read_type == 'paired':
            reads_total = self.result_data['total'] * 2
            aligned_total = self.result_data['aligned'] * 2
            unaligned_total = self.result_data['unaligned'] * 2

        self.result_data['aligned_total'] = aligned_total
        self.result_data['unaligned_total'] = unaligned_total
        self.result_data['reads_total'] = reads_total
        self.result_data['discarded_total'] = reads_total - self.result_data['retained']

        self.result_data['retained_reads'] = self.result_data['retained'] - self.result_data['singleton_m1'] - self.result_data['singleton_m2']
        self.result_data['percent_aligned'] = round((float(self.result_data['aligned']) * 100.0) / float(self.result_data['total']), 2)

    def set_len_dist(self, len_dist_data):

        for line in len_dist_data[1:]:
            l_data = line.rstrip('\n').split('\t')
            l_data = list(map(int, l_data))

            # initialize file name
            if self.s_name not in self.len_dist_plot_data['mate1']:
                self.len_dist_plot_data['mate1'][self.s_name] = dict()
                self.len_dist_plot_data['mate2'][self.s_name] = dict()
                self.len_dist_plot_data['singleton'][self.s_name] = dict()
                self.len_dist_plot_data['collapsed'][self.s_name] = dict()
                self.len_dist_plot_data['collapsed_truncated'][self.s_name] = dict()
                self.len_dist_plot_data['discarged'][self.s_name] = dict()
                self.len_dist_plot_data['all'][self.s_name] = dict()

            if self.__read_type == 'single':
                if not self.__collapsed:
                    self.len_dist_plot_data['mate1'][self.s_name][l_data[0]] = l_data[1]
                    self.len_dist_plot_data['mate2'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['singleton'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['collapsed'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['collapsed_truncated'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['discarged'][self.s_name][l_data[0]] = l_data[2]
                    self.len_dist_plot_data['all'][self.s_name][l_data[0]] = l_data[3]
                else:
                    # this case should not be reached (see case at method set_ar_type())
                    pass
            else:
                if not self.__collapsed:
                    self.len_dist_plot_data['mate1'][self.s_name][l_data[0]] = l_data[1]
                    self.len_dist_plot_data['mate2'][self.s_name][l_data[0]] = l_data[2]
                    self.len_dist_plot_data['singleton'][self.s_name][l_data[0]] = l_data[3]
                    self.len_dist_plot_data['collapsed'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['collapsed_truncated'][self.s_name][l_data[0]] = 0
                    self.len_dist_plot_data['discarged'][self.s_name][l_data[0]] = l_data[4]
                    self.len_dist_plot_data['all'][self.s_name][l_data[0]] = l_data[5]
                else:
                    self.len_dist_plot_data['mate1'][self.s_name][l_data[0]] = l_data[1]
                    self.len_dist_plot_data['mate2'][self.s_name][l_data[0]] = l_data[2]
                    self.len_dist_plot_data['singleton'][self.s_name][l_data[0]] = l_data[3]
                    self.len_dist_plot_data['collapsed'][self.s_name][l_data[0]] = l_data[4]
                    self.len_dist_plot_data['collapsed_truncated'][self.s_name][l_data[0]] = l_data[5]
                    self.len_dist_plot_data['discarged'][self.s_name][l_data[0]] = l_data[6]
                    self.len_dist_plot_data['all'][self.s_name][l_data[0]] = l_data[7]

    def adapter_removal_stats_table(self):

        headers = OrderedDict()
        headers['percent_aligned'] = {
                'title': '% Trimmed',
                'description': '% trimmed reads',
                'max': 100,
                'min': 0,
                'suffix': '%',
                'scale': 'RdYlGn',
                'format': '{:.1f}%',
                'shared_key': 'percent_aligned',
        }
        headers['aligned_total'] = {
                'title': 'Total Trimmed',
                'description': 'total trimmed reads',
                'min': 0,
                'scale': 'PuBu',
                'shared_key': 'aligned_total'
        }
        self.general_stats_addcols(self.adapter_removal_data, headers)

    def adapter_removal_retained_chart(self):

        pconfig = {
            'title': 'retained and discarded',
            'id': 'ar_retained_plot',
            'ylab': '# Reads',
            'hide_zero_cats': False,
            'cpswitch_counts_label': 'Number of Reads'
        }

        cats_pec = OrderedDict()
        cats_pec['singleton_m1'] = {'name': 'singleton mate1'}
        cats_pec['singleton_m2'] = {'name': 'singleton mate2'}
        cats_pec['retained_reads'] = {'name': 'retained read pairs'}
        cats_pec['full-length_cp'] = {'name': 'full-length collapsed pairs'}
        cats_pec['truncated_cp'] = {'name': 'truncated collapsed pairs'}
        cats_pec['discarded_m1'] = {'name': 'discarded mate1'}
        cats_pec['discarded_m2'] = {'name': 'discarded mate2'}

        #self.sections.append({
        #    'name': 'Retained and Discarded Paired-End Collapsed',
        #    'anchor': 'adapter_removal_retained_plot',
        #    'content': '<p>The proportions of retained and discarded reads.</p>' +
        #               bargraph.plot(self.adapter_removal_data, cats_pec, pconfig)
        #})

        self.add_section(
            name='Retained and Discarded Paired-End Collapsed',
            anchor='adapter_removal_retained_plot',
            description='The proportions of retained and discarded reads.',
            plot=bargraph.plot(self.adapter_removal_data, cats_pec, pconfig)
        )

    def adapter_removal_length_dist_plot(self):
        pconfig = {
            'title': 'Length Distribution',
            'id': 'ar_lenght_count_plot',
            'ylab': 'Counts',
            'xlab': 'read length',
            'xDecimals': False,
            'ymin': 0,
            'tt_label': '<b>{point.x} bp trimmed</b>: {point.y:.0f}',
            'data_labels': [
                {'name': 'Mate1', 'ylab': 'Count'},
                {'name': 'Mate2', 'ylab': 'Count'},
                {'name': 'Singleton', 'ylab': 'Count'},
                {'name': 'Collapsed', 'ylab': 'Count'},
                {'name': 'Collapsed Truncated', 'ylab': 'Count'},
                {'name': 'Discarded', 'ylab': 'Count'},
                {'name': 'All', 'ylab': 'Count'}
            ]
        }

        lineplot_data = [
            self.len_dist_plot_data['mate1'],
            self.len_dist_plot_data['mate2'],
            self.len_dist_plot_data['singleton'],
            self.len_dist_plot_data['collapsed'],
            self.len_dist_plot_data['collapsed_truncated'],
            self.len_dist_plot_data['discarged'],
            self.len_dist_plot_data['all']
        ]
        #self.sections.append({
        #    'name': 'Lenght Distribution Paired End Collapsed',
        #    'anchor': 'ar_lenght_count',
        #    'content': '<p>The lenght distribution of reads after processing adapter alignment.</p>' +
        #               linegraph.plot(lineplot_data, pconfig)
        #})

        self.add_section(
            name='Lenght Distribution Paired End Collapsed',
            anchor='ar_lenght_count',
            description='The lenght distribution of reads after processing adapter alignment.',
            plot=linegraph.plot(lineplot_data, pconfig)
        )