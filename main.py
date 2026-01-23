from enum import Enum, StrEnum, IntEnum
from pathlib import Path

import collections
collections.Callable = collections.abc.Callable
from bs4 import BeautifulSoup
import requests

import pandas as pd

class CampusType(IntEnum):
    BLACKSBURG = 0,
    NATIONAL_CAPITAL_REGION = 4,

class CourseType(StrEnum):
    ECE="ECE",
    CS="CS",

data_keys = ['crn', 'course', 'title', 'schedule_type', 'modality',
             'credits', 'capacity', 'instructor', 
             'days', 'begin', 'end', 
             'location', 'exam', 
             'comment',
             'ad_days', 'ad_begin', 'ad_end', 'ad_location',]

def make_request(campus: CampusType, term: int, subject: CourseType, coursenum_search: int):
    # update this as the service changes
    url = "https://selfservice.banner.vt.edu/ssb/HZSKVTSC.P_ProcRequest"

    # create POST request
    params = {
        "CAMPUS":campus,
        "TERMYEAR":term,                    # YYYYMM, YYYY year of courses, MM is the semester start month TODO: create enum for the 5 course terms
        "CORE_CODE":"AR%",                  # don't change
        "subj_code":subject,                # choose between ECE or CS
        "SCHDTYPE":"%",                     # don't change
        "CRSE_NUMBER":coursenum_search,     # course number search
        "crn":"",                           # don't need
        "open_only":"",                     # don't need
        "disp_comments_in":"Y",             # don't need
        "BTN_PRESSED":"FIND class sections",# don't need
        "inst_name":"",                     # don't need
    }

    # create post request, TODO: backoff exponential
    r = requests.post(url, data=params)
    return BeautifulSoup(r.content, 'html.parser')

def has_comment(entries):
    return "comments" in entries[0].lower()

def has_additionaltimes(entries):
    if len(entries) <= 4:
        return False
    
    return "additional times" in entries[4].lower()


def synthesize_data(row, comment=None, addit_times=None):
    """
    input:
        row: course entry to parse into a dictionary
        comment: comment to append to the entry
        addit_times: additional times to append to the entry

    return:
        dictionary of synthesized entry
    """
    if len(row) > 7:
        if 'arr' in row[8].lower():
            row.insert(9, row[8])

    if comment:
        row.extend(comment)
    else:
        row.extend([''])

    if addit_times:
        row.extend(addit_times)
    else:
        row.extend(['','','',''])


    return dict(zip(data_keys, row))

def parse_row(row):
    return [entry.text.replace('\n', '').replace('-', ' ').strip() for entry in row.find_all('td')] 

def parse_table(table):
    """
    Input
      - table: html table from VT registrar, must be beautifulsoup obj
    
    Return
      - list of dictionaries containing parsed course entries
    """

    """
    idea is to iteratively build a course listing
    by keeping track of a valid course and checking on
    sequential rows and if the row contains other
    information, it appends to the valid course.
    We only submit the row to the listing if the next 
    row is valid

    TODO: try recursive for loop-less approach
    """
    # find all tables
    table.find('table', attrs={'class':'dataentrytable'})

    old_row = None
    comment = None
    addit_times = None
    
    courses = list()
    for row in table.find_all('tr'): # finds all rows in located table
        # filter for valid table rows
        if row.attrs != {}:
            continue

        # parse row
        entries = parse_row(row)

        # filter for valid entries
        if len(entries) <= 1:
            continue

        # parse comment and store entry
        if has_comment(entries):
            comment = [f"{entries[0]} {entries[1]}"]

        # parse additional times and store entry
        elif has_additionaltimes(entries):
            addit_times = entries[5:9]

            if "arr" in addit_times[1].lower():
                addit_times[3] = addit_times[2]
                addit_times[2] = '(ARR)'
            
        # submit entry, set working row to current row, reset comment and additional times  
        else:
            if old_row:
                # check if CRN exists. otherwise its not a valid course entry
                if old_row[0].isdigit():
                    courses.append(synthesize_data(old_row, comment, addit_times))

                # reset for next iteration
                comment = None
                addit_times = None

            # store old row for potential extras
            if len(entries) >= 12:
                # for some unknown reason they really like to make the tables as inconsistent as possible
                if 'arr' in entries[8].lower():
                    old_row = entries[:12]
                else:
                    old_row = entries[:13]

            # must set old row regardless since the comment & addit_times desync otherwise
            else:
                old_row = entries

    # parse last valid item
    if old_row:
        courses.append(synthesize_data(old_row, comment, addit_times))

    return courses

# helper to convert timetable website to a readable spreadsheet
def get_TOC_courses(campus: CampusType, term: int, subject: CourseType, coursenum_search: int):
    html_table = make_request(campus, term, subject, coursenum_search)
    table = parse_table(html_table)

    return table

# helper to convert list to dataframe
def course_to_df_clean(d: list):
    return pd.DataFrame(d).drop(columns=['schedule_type', 'credits', 'capacity', 'instructor', 'exam'])

if __name__ == "__main__":
    # build course lists
    BB_courses = get_TOC_courses(CampusType.BLACKSBURG, 202601, CourseType.ECE, 5)
    print("obtained Blacksburg course catalog")
    NCR_courses = get_TOC_courses(CampusType.NATIONAL_CAPITAL_REGION, 202601, CourseType.ECE, 5)
    print("obtained NCR course catalog")

    # convert course list to dataframe
    BB_df = course_to_df_clean(BB_courses)
    NCR_df = course_to_df_clean(NCR_courses)

    # output to file
    all_courses = pd.concat([BB_df, NCR_df]).sort_values(by=['course'])
    all_courses.to_csv("courses.csv",index=False)

    print("done converting into readable spreadsheet.")

