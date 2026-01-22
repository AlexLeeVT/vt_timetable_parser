import requests

import collections
collections.Callable = collections.abc.Callable
from bs4 import BeautifulSoup

from pathlib import Path

# referenced from https://github.com/VirginiaTech/pyvt
class Section:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @staticmethod
    def tuple_str(tup):
        return str(tup).replace("'", "")

    def __str__(self):
        return '%s (%s) on %s at %s' % (getattr(self, 'name'), getattr(self, 'crn'),
                                        getattr(self, 'days'),
                                        Section.tuple_str((getattr(self, 'start_time'), getattr(self, 'end_time'))))

    def __eq__(self, other):
        if isinstance(other, Section):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return int(getattr(self, 'crn'))

data_keys = ['crn', 'course', 'title', 'schedule_type', 'modality',
             'credits', 'capacity', 'instructor', 
             'days', 'begin', 'end', 
             'location', 'exam',]

comment_keys = ['comment']

additional_time_keys = ['ad_days', 'ad_begin', 'ad_end', 'ad_location']

def parse_row(row, additional_time=None, comment=None): 
    """
    input:
        row: list(str)
        additional_time: list(str) 
        comment: list(str)

    return:
        dictionary of courses with the additional time and comment if provided.
    """
    entries = [entry.text.replace('\n', '').replace('-', ' ').strip() for entry in row.find_all('td')]

    if len(entries) <= 1:
        return None

    return dict(zip(data_keys, entries))

# in-between there are many 
VTTOC_COURSETABLE_ROW_START = 12

# POST request
params = {
    "CAMPUS":0,
    "TERMYEAR":202601,
    "CORE_CODE":"AR%",
    "subj_code":"ECE",
    "SCHDTYPE":"%",
    "CRSE_NUMBER":5,
    "crn":"",
    "open_only":"",
    "disp_comments_in":"Y",
    "BTN_PRESSED":"FIND class sections",
    "inst_name":"",
}

def make_request():
    # update this as the service changes
    url = "https://selfservice.banner.vt.edu/ssb/HZSKVTSC.P_ProcRequest"

    # create post request, TODO: backoff exponential
    r = requests.post(url, data=params)
    return BeautifulSoup(r.content, 'html.parser')

def parse_row(row):
    return [entry.text.replace('\n', '').replace('-', ' ').strip() for entry in row.find_all('td')] 

def has_comment(entries):
    return "comments" in entries[0].lower()

def has_additionaltimes(entries):
    if len(entries) <= 4:
        return False
    
    return ("additional times" in entries[4].lower())

# parse table
def parse_table(table):
    table.find('table', attrs={'class':'dataentrytable'})

    old_row = None
    comment = None
    addit_times = None

    count = 0

    courses = list()
    # state machine
    for row in table.find_all('tr'):
        # filter for valid table rows
        if row.attrs != {}:
            continue

        # parse row
        entries = parse_row(row)

        # filter for valid entries
        if len(entries) <= 1:
            continue

        # check if current row is comment
        if has_comment(entries):
            comment = [entries[1]]

        # check if current row is additional times
        elif has_additionaltimes(entries):
            addit_times = entries[5:9]

            if "arr" in addit_times[1].lower():
                addit_times[3] = addit_times[2]
                addit_times[2] = '(ARR)'
            
        # submit old row, set old row to current row, reset comment and additional times  
        else:
            if old_row:
                if len(old_row) > 7:
                    if 'arr' in old_row[8].lower():
                        old_row.insert(9, old_row[8])

                additional_keys = [] 
                if comment:
                    old_row.extend(comment)
                    additional_keys += comment_keys 

                if addit_times:
                    old_row.extend(addit_times)
                    additional_keys += additional_time_keys

                keys = data_keys + additional_keys
                courses.append(dict(zip(keys, old_row)))

                comment = None
                addit_times = None

            # hold old row for potential extra notes
            if len(entries) >= 12:
                if 'arr' in entries[8].lower():
                    old_row = entries[:12]
                else:
                    old_row = entries[:13]
            else:
                old_row = entries

    return courses

def get_TOC_courses():
    html_table = make_request()
    table = parse_table(html_table)

    return table

courses = get_TOC_courses()
for course in courses:
    print(course)

# output to file
output = Path("output.txt")
if not output.exists:
    output.touch(exist_ok=True)
