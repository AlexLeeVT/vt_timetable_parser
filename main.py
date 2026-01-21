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

# parse table
def parse_table(table):
    table.find('table', attrs={'class':'dataentrytable'})
    rows = [row for row in table.find_all('tr') if row.attrs == {}] 

    return [parse_row(c) for c in rows[VTTOC_COURSETABLE_ROW_START : VTTOC_COURSETABLE_ROW_START+10] if parse_row(c) is not None]

def get_TOC_courses():
    html_table = make_request()
    table = parse_table(html_table)

    return table

courses = get_TOC_courses()
print(courses[0])
# output to file
output = Path("output.txt")
if not output.exists:
    output.touch(exist_ok=True)
