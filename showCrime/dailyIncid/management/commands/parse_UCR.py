# coding=utf8

''' parse_ucr_pdfquery

parse OPD weekly UCR reports

leans heavily on pdfplumber, esp. its TABLE extraction
	https://github.com/jsvine/pdfplumber says:
    Works best on machine-generated, rather than scanned, PDFs. Built on pdfminer and pdfminer.six.

Created on Nov 3, 2017
	update 12 Feb 19

@author: rik
'''

import glob
import json
import os
import re
from collections import defaultdict, OrderedDict
from datetime import datetime

import pdfplumber

from ....dailyIncid.models import WeeklySummary

IGNORED_LABELS = ['Part 1 Crimes', 'THIS REPORT IS HIERARCHY BASED.',
                  '(homicide, aggravated assault, rape, robbery)']

LABEL_TO_FIELD_MAPPING = OrderedDict([(u'Violent Crime Index', 'violent_crime_index'),
                                      (u'Homicide – 187(a)PC', 'homicide_187'),
                                      (u'Homicide – All Other *', 'homicide_all'),
                                      (u'Aggravated Assault', 'aggravated_assault'),
                                      # u'Shooting with injury – 245(a)(2)PC',
                                      (u'Assault with a firearm – 245(a)(2)PC', 'assault_firearm'),
                                      # u'Subtotal - Homicides + Injury Shootings',
                                      (u'Subtotal - Homicides + Firearm Assault', ''),
                                      (u'Shooting occupied home or vehicle – 246PC', 'shooting_occupied_hov'),
                                      (u'Shooting unoccupied home or vehicle – 247PC', 'shooting_unoccupied_hov'),
                                      (u'Non-firearm aggravated assaults', 'assault_non_firearm'),
                                      (u'Rape', 'rape'),
                                      (u'Robbery', 'robbery'),
                                      (u'Firearm', 'firearm'),
                                      (u'Knife', 'knife'),
                                      (u'Strong-arm', 'strong_arm'),
                                      (u'Other dangerous weapon', 'other_weapon'),
                                      # u'Residential  robbery – 212.5(A)PC',
                                      (u'Residential  robbery – 212.5(a)PC', 'robbery_residential'),
                                      # u'Carjacking – 215(A) PC',
                                      (u'Carjacking – 215(a) PC', 'carjacking'),
                                      (u'Burglary', 'burglary'),
                                      (u'Auto', 'auto'),
                                      (u'Residential', 'residential'),
                                      (u'Commercial', 'commercial'),
                                      (u'Other (Includes boats, aircraft, and so on)', 'other'),
                                      (u'Unknown', 'unknown'),
                                      (u'Motor Vehicle Theft', 'motor_vehicle_theft'),
                                      (u'Larceny', 'larceny'),
                                      (u'Arson', 'arson'),
                                      (u'Total', 'total')])

FixFilePat = {
    re.compile(r'Area(\d)WeeklyCrimeReport11Jun17Jun18.pdf'): '180619_Area %d Weekly Crime Report 11Jun - 17Jun18.pdf'}


def date_to_string(o):
    if isinstance(o, datetime):
        return o.strftime('%y%m%d')


def parse_ucr_pdf(file_path, report_date, from_date, to_date, file_name, verbose=False):
    """
    Parse the pdf file and extract information based on a pre-defined order of fields.

    :param file_path: File path where the PDF file resides
    :param report_date: Report date to be given to the dataset
    :param from_date: Start date of the particular record
    :param to_date: End date of the particular record
    :param file_name: File name of the PDF
    :param verbose: Flag to indicate if verbose logging is required.
    :return:
    """
    try:
        pdf = pdfplumber.open(file_path)
        docinfo = pdf.metadata

        pdf_page = pdf.pages[0]
        tables = pdf_page.extract_tables()
    except Exception as e:
        print('parse_ucr_pdf: cant load', file_path, e)
        return None

    # .extract_table returns a list of lists, with each inner list representing a row in the table.
    crime_table = tables[0]

    if verbose:
        print('parse_ucr_pdf: Table found %d x %d' % (len(crime_table), len(crime_table[0])))

    crime_data = {}

    for i in range(len(crime_table)):
        label = crime_table[i][0]
        if label is None or label in IGNORED_LABELS:
            continue
        vals = crime_table[i][1]
        vals = vals.replace(' ', '')  # multi-digit numbers have intermediate spaces

        if vals == '-':
            val = 0
        else:
            try:
                val = int(vals)
            except Exception as e:
                print(i, label, vals, e)
                continue

        if verbose:
            print(i, label, val)
        crime_data[label] = val

    crime_data['Author'] = docinfo['Author']
    crime_data['CreateDate'] = docinfo['CreationDate']
    crime_data['ModDate'] = docinfo['ModDate']
    crime_data['FileName'] = file_name
    crime_data['ReportDate'] = report_date
    crime_data['FromDate'] = from_date
    crime_data['ToDate'] = to_date

    if verbose:
        print('parse_ucr_pdf: NKey=%d %s' % (len(crime_data.keys()), file_path))
    return crime_data


def consolidate_reports(raw_stats):
    """
    Given a dictionary of data representing all crime information, consolidate the
    data by crime type

    :param raw_stats: Dictionary containing crime data for each report where the keys
                     represent the report for a specific period and area
    :return: Dictionary containing crime data with keys representing a crime type
    """
    report_keys = list(raw_stats.keys())
    report_keys.sort()
    ignored_keys = ['Author', 'CreateDate', 'ModDate', 'FileName', 'FromDate', 'ReportDate', 'ToDate']
    # crime_data_by_type: lbl -> date -> div -> freq
    crime_data_by_type = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for report_key in report_keys:
        divs, report_date = report_key.split('_')
        div = int(divs)

        # NB: need to distinguish stat's lbl which may have \n from mlbl used in LABEL_TO_FIELD_MAPPING
        for crime_type in raw_stats[report_key]:
            crime_label = crime_type.split('\n')[0]
            if crime_label in LABEL_TO_FIELD_MAPPING.keys():
                crime_data_by_type[crime_label][report_date][div] = raw_stats[report_key][crime_type]
            elif crime_label not in ignored_keys:
                print("consolidate_reports: unknown label?! %s %s" % (crime_label, report_key))

    return crime_data_by_type


def persist_data(data, metadata):
    """
    Persist the given data dictionary into the database.

    :param data: Data dictionary containing counts of each crime type by report
    :param metadata: Metadata of the report containing date and area information
    """
    for value in metadata:
        stats = dict()
        report_date = value.split("_")[1]
        stats['report_date'] = datetime.strptime(report_date, '%y%m%d')
        stats['area'] = int(value.split("_")[0])
        for crime_type in data:
            if LABEL_TO_FIELD_MAPPING[crime_type] != '':
                stats[LABEL_TO_FIELD_MAPPING[crime_type]] = data[crime_type][report_date][1]
        WeeklySummary.objects.create(**stats)


# Police Area 3 Weekly Crime Reports
DivDirName_pat = re.compile(r'Police Area (\d) Weekly Crime Reports')

# fname = '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf'
FileName_pat = re.compile(r'(\d+)_Area (\d) Weekly Crime Report (\d+)(\D+) - (\d+)(\D+)(\d+).pdf')


def get_dates_from_file(file_name):
    """
    Given a filename of the format '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf',
    extract the report date, and start and dates of the report.

    :param file_name: Given a file name
    :return: Tuple containing the report date, start date, end date
    """

    match = FileName_pat.match(file_name)
    if match:
        # match.groups() = ('190114', '2', '07', 'Jan', '13', 'Jan', '19')
        (postDateStr, areaNum, from_day, from_month, to_day, to_month, year) = match.groups()
    else:
        print('fname2dates: cant parse', file_name)
        # import pdb; pdb.set_trace()
        return None, None, None

    # HACK: common exceptions (:
    if to_month == 'Sept':
        to_month = 'Sep'
    if year.startswith('20'):
        year = year[2:]

    report_date = datetime.strptime(postDateStr, '%y%m%d')
    try:
        from_date = datetime.strptime('%s%s%s' % (from_day, from_month, year), '%d%b%y')
        to_date = datetime.strptime('%s%s%s' % (to_day, to_month, year), '%d%b%y')
    except:
        print('fname2dates: bad dates?', file_name)
        # import pdb; pdb.set_trace()
        from_date = to_date = None

    return report_date, from_date, to_date


if __name__ == '__main__':
    root_dir_path = '/Users/shawn.varghese/Desktop/OpenOakland/'

    start_time = datetime.now()
    date_str = start_time.strftime('%y%m%d')
    json_filepath = root_dir_path + 'UCR_WeeklyStats_%s.json' % date_str
    stats_only = False

    if stats_only:
        print('parse_ucr: loading data from JSON file', json_filepath)
        all_stats_data = json.load(open(json_filepath))
        print('parse_ucr: NStatFiles = %d' % (len(all_stats_data)))

    else:
        report_dirs = glob.glob(root_dir_path + 'Police Area *')

        pdf_file_list = []
        for report_dir_path in report_dirs:
            if not os.path.isdir(report_dir_path):
                continue

            ddpath, report_filename = os.path.split(report_dir_path)
            # Verify that file name is Police Area <area number> Weekly Crime Reports
            regex_match = DivDirName_pat.match(report_filename)
            if regex_match:
                # match.groups() = ('2')
                division_number_str = regex_match.groups()
                division_number = int(division_number_str[0])
            else:
                print('parse_ucr: cant parse divDir', report_filename)
                continue

            print('parse_ucr: NFiles=%d searching files for Div=%d : %s' % (len(pdf_file_list),
                                                                            division_number,
                                                                            report_filename))

            for divSubDir in glob.glob(report_dir_path + '/*'):

                # NB: pdfs are posted at top-level within division?!
                if os.path.isfile(divSubDir):
                    if divSubDir.endswith('.pdf'):
                        pdf_file_list.append((division_number, divSubDir))
                    else:
                        print('parse_ucr: skipping non-PDF file', divSubDir)
                        continue

                if os.path.isdir(divSubDir):
                    for f in glob.glob(divSubDir + '/*.pdf'):
                        pdf_file_list.append((division_number, f))

        print('parse_ucr: NFiles found=%d' % (len(pdf_file_list)))

        nbad = 0
        all_stats_data = {}
        for file_index, file_info in enumerate(pdf_file_list):
            # NB: checkpoint saved at top of loop,
            if file_index > 0:
                cpjson = root_dir_path + 'UCR_WeeklyStats_%s_cp-%d.json' % (date_str, file_index)
                json.dump(all_stats_data, open(cpjson, 'w'), indent=1, default=date_to_string)

            div_num, file_path = file_info
            dir_name, file_name = os.path.split(file_path)

            for fixPat in FixFilePat.keys():
                match = fixPat.match(file_name)
                if match:
                    # match.groups() = ('2')
                    div_num_str = match.groups()
                    div_num = int(div_num_str[0])
                    updated_filename = FixFilePat[fixPat] % div_num
                    print('parse_ucr: fixing bad fname: %s <- %s' % (updated_filename, file_name))
                    file_name = updated_filename

            # file_name = '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf'
            report_date, from_date, to_date = get_dates_from_file(file_name)

            try:
                parsed_stats = parse_ucr_pdf(file_path,
                                             report_date,
                                             from_date,
                                             to_date,
                                             file_name)
            except Exception as e:
                print('parse_ucr: cant process %d %s %s' % (file_index, file_name, e))
                nbad += 1
                continue
            if parsed_stats is None:
                print('parse_ucr: cant process (None) %d %s' % (file_index, file_name))
                nbad += 1
                continue

            if report_date is None:
                report_date_str = 'missDate-%d' % file_index
            else:
                report_date_str = report_date.strftime('%y%m%d')
            report_key = '%d_%s' % (division_number, report_date_str)
            if report_key in all_stats_data:
                print(f'parse_ucr_Pdf: duplicate keys?! '
                      f'{report_key}\n\t{parsed_stats}\n\t{all_stats_data[report_key]}')
                continue
            all_stats_data[report_key] = parsed_stats

            # NB: reporting at end of loop,
            if file_index > 0:
                elapsed_time = datetime.now() - start_time
                print('%d %s done (%s sec)' % (file_index, report_key, elapsed_time.total_seconds()))

        print('parse_ucr: NStatFiles = %d' % (len(all_stats_data)))
        json.dump(all_stats_data, open(json_filepath, 'w'), indent=1, default=date_to_string)

    consolidate_data = consolidate_reports(all_stats_data)
    persist_data(consolidate_data, all_stats_data.keys())
