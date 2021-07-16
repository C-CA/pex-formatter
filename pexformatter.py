# -*- coding: utf-8 -*-
"""
Created on Wed Jun 30 09:57:06 2021

@author: tfahry

PEX formatter

Call the formatpex() function to format a PEX file.

Requires Python 3.8.8 or later.
Last built on Python 3.8.8.

Python versions above 3.9 will not work on Windows 7.
"""
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
from collections import Counter

class keydict(dict):
    def __missing__(self, key):
        return key

#prefixes = ['PEX', 'THD', 'TDT', 'TSP', 'TMV', 'TRF', 'NTE', 'PIT']

default_time_format = '%H:%M:%S'
pathing_time_format = '%M\'%S'

#wrapper for strptime() with add_days parameter
def st(time_string, time_format = default_time_format, add_days = 0):
   return dt.strptime(time_string, time_format) + timedelta(days=add_days)

#parse pathing time
def ppt(pathing_time_string):
    sign = 1 if pathing_time_string[0] == '+' else -1
    return sign*(st(pathing_time_string[1:], pathing_time_format) - dt(1900,1,1)).total_seconds()/60
    
#split a tab-delimited raw line
def s(raw_line):
    return raw_line.split('\t')

#get prefix
def gp(line):
    return s(line[1])[0]

'''
A line is a tuple of (lineno, unformatted_string). The file object is a list of these lines.
'''

def make_template_from_header(timetable_name,thd_line,tdt_lines):
    '''
    Takes a timetable name, a raw TDT line, and a list of raw THD lines.
    Makes a template dict and fills the fields that are constant for a single train run.
    
    :param timetable_name: a string containing the name of the timetable (usually file name) that will go in the Timetable field of the output dict.
    :param thd: a line containing the THD entry.
    :param tdt: a line containing the TDT entry.
    :param lineno: the current line number. Used for raising more informative exceptions.
    
    :returns: a template - a single dict that will be used in get_entries_from_run().
    '''
    
    columns = ['Line in file', 'Timetable','TSC','Train Headcode','Operator (Code)','Operator (Name)','Train Class',
    'Train Speed/Load','Run Start (Code)','Run End (Code)','Run Start (Name)','Run End (Name)','Run Overview',
    'Run Start (Time)','Run End (Time)','Run Time Range','Operating Day','From (Time)','To (Time)','From (Code)',
    'To (Code)','From (Name)','To (Name)','Route','Running Line','Platform','Run Type','Sectional Running Time',
    'Runtime','Dwell','Movement Type','Engineering Allowance','Pathing Allowance','Performance Allowance',
    'Adjustment Allowance','Train Description']
    
    empty_entry = dict([(column, '') for column in columns])
    template = empty_entry.copy()    
    template['Timetable'] = timetable_name
    
    thd_lineno = thd_line[0]
    thd = s(thd_line[1])
    assert gp(thd_line) == 'THD' and len(thd) == 15, f'Invalid THD entry {thd_line[1]} at line {thd_lineno}'
    
    template['Operator (Code)']  = thd[2]
    try:
        template['Operator (Name)'] = tocdict[template['Operator (Code)']]
    except KeyError:
        template['Operator (Name)'] = 'Unknown operator code'
        
    template['Train Headcode']   = thd[3]
    template['Train Class']      = thd[3][0]
    template['Run Start (Code)'] = thd[10]
    template['Run Start (Time)'] = thd[11]
    template['Run End (Code)']   = thd[12]
    template['Run End (Time)']   = thd[13]
    
    template['Run Start (Name)'] = tiplocdict[template['Run Start (Code)']]
    template['Run End (Name)'] = tiplocdict[template['Run End (Code)']]
    
    template['Run Overview'] = template['Run Start (Name)'] +' to '+ template['Run End (Name)']
    
    template['Train Description']   = template['Train Headcode']+' - '+template['Run Start (Name)']+' ('+template['Run Start (Time)']+') to '\
        +template['Run End (Name)']+' ('+template['Run End (Time)']+') ' 
        

    for tdt_line in tdt_lines:
        tdt = s(tdt_line[1])
        assert gp(tdt_line) == 'TDT' and len(tdt) == 13, f'Invalid TDT entry {tdt_line[1]} at line {tdt_line[0]}'
    
    #most common tuple
    mct = Counter([(s(x[1])[4],s(x[1])[6], s(x[1])[8]) for x in tdt_lines]).most_common()[0][0]
    
    template['TSC'] = mct[0]
    template['Train Speed/Load'] = mct[2] + '/' + mct[1]
    
    return template

def get_entries_from_run(template, run): 
    '''
    Takes a template dict and a list of raw movement lines that are either TSP or TMV.
    Formats the lines and returns them as a list of dicts.
    
    :param template: the dict generated by the make_template_from_header() function.
    :param run: a list of lines from the file object from start TSP to end TSP, containing a single train run.
    
    :returns: entries - a list of dicts containing formatted output.    
    '''
    entries = []
    assert s(run[0][1])[0] == 'TSP', f'Run starting at line {run[0][0]} does not start with a TSP'

    for index, (lineno, raw_line) in enumerate(run):
        line = s(raw_line)
        
        entry = template.copy()
        entry['Line in file']  = lineno
        
        #if this is the first TSP line in the run, make the Origin row from it
        if index == 0:
            prev_dwell = 1
            
            entry['Run Type'] = 'Origin'
            entry['Platform'] = line[6]
            
            entry['To (Time)']= line[5]
            entry['From (Code)']  = line[3]
            entry['To (Code)']    = line[3]
            
            entry['Run Time Range'] = st(str(st(entry['To (Time)']).hour), '%H').strftime('%H:%M')+'-'+(st(str(st(entry['To (Time)']).hour), '%H')+ timedelta(minutes=59)).strftime('%H:%M')
            
            entry['From (Name)']  = tiplocdict[entry['From (Code)']]
            entry['To (Name)']    = tiplocdict[entry['To (Code)']]
            entry['Route'] = entry['From (Name)']+' to '+entry['To (Name)']
            
            
            entries.append(entry)

        #or if it's the last, make the Terminate row from it            
        elif index == len(run) -1:
            entry['Run Type'] = 'Destination'
            entry['Platform'] = line[6]

            entry['From (Time)']= line[4]
            entry['From (Code)']  = line[3]
            entry['To (Code)']    = line[3]
            
            entry['Run Time Range'] = st(str(st(entry['From (Time)']).hour), '%H').strftime('%H:%M')+'-'+(st(str(st(entry['From (Time)']).hour), '%H')+ timedelta(minutes=59)).strftime('%H:%M')
            
            entry['From (Name)']  = tiplocdict[entry['From (Code)']]
            entry['To (Name)']    = tiplocdict[entry['To (Code)']]
            entry['Route'] = entry['From (Name)']+' to '+entry['To (Name)']
            
            entries.append(entry)
        
        #otherwise, it is a normal line - make an entry from it
        else:
            #check if the line is a TSP or a TMV
            if line[0] == 'TSP':
                
                #f the dwell is across midnight, this particular dwell needs to have only its To (time) incremented by a day
                if st(line[5]) < st(line[4]):
                    entry['Dwell'] = prev_dwell = (st(line[5], add_days=1) - st(line[4])).total_seconds()/60
                
                #else, a normal not-across-midnight dwell calculation
                else:
                    entry['Dwell'] = prev_dwell = (st(line[5]) - st(line[4])).total_seconds()/60
                    
                #if this TSP is not a mandatory timing point, i.e. non-zero dwell
                if entry['Dwell'] > 0:
                    entry['Run Type'] = 'Dwell'
                    entry['Platform'] = line[6]
                    
                    entry['From (Time)']  = line[4]
                    entry['To (Time)']    = line[5]        
                    entry['From (Code)']  = line[3]
                    entry['To (Code)']    = line[3]      
                    
                    entry['Run Time Range'] = st(str(st(entry['From (Time)']).hour), '%H').strftime('%H:%M')+'-'+(st(str(st(entry['From (Time)']).hour), '%H')+ timedelta(minutes=59)).strftime('%H:%M')
                    
                    entry['From (Name)']  = tiplocdict[entry['From (Code)']]
                    entry['To (Name)']    = tiplocdict[entry['To (Code)']]
                    entry['Route'] = entry['From (Name)']+' to '+entry['To (Name)']
                    
                    entries.append(entry)

            elif line[0] == 'TMV':
                
                entry['From (Code)']  = line[3]
                entry['To (Code)']    = line[4]
                entry['Running Line'] = line[5]
                entry['From (Time)']  = line[6]
                entry['To (Time)']    = line[7]
                
                entry['Run Time Range'] = st(str(st(entry['From (Time)']).hour), '%H').strftime('%H:%M')+'-'+(st(str(st(entry['From (Time)']).hour), '%H')+ timedelta(minutes=59)).strftime('%H:%M')
                
                entry['From (Name)']  = tiplocdict[entry['From (Code)']]
                entry['To (Name)']    = tiplocdict[entry['To (Code)']]
                entry['Route'] = entry['From (Name)']+' to '+entry['To (Name)']
                
                entry['Run Type'] = 'Movement'

                if prev_dwell > 0:
                    prev_movement = 'Stop'
                else:
                    prev_movement = 'Pass'                    

                #if we are at the next-to-last TMV in the run, the next line is always a TSP and therefore a stop. 
                #we can't just treat that next TSP as a regular TSP since it has a blank [5] field and will cause a TypeError.
                if index == len(run) - 2:
                    next_movement = 'Stop'

                #if we are at any other line, we have to look at the next movement and determine if it is a Stop or Pass
                else:
                    next = s(run[index+1][1])
                    #if the next movement is a TMV, it is always a pass
                    if next[0] == 'TMV':
                        next_movement = 'Pass'   

                    elif next[0] == 'TSP':
                        #if the next movement is a TSP with zero dwell, it is a mandatory timing point and therefore a Pass
                        if (st(next[5]) - st(next[4])).total_seconds() == 0:
                            next_movement = 'Pass'

                        #if the TSP has a nonzero dwell, it is a Stop
                        else:
                            next_movement = 'Stop'
                
                entry['Movement Type'] = prev_movement+' to '+next_movement                            

                entry['Engineering Allowance'] = ppt(line[10])
                entry['Pathing Allowance']     = ppt(line[11])
                entry['Performance Allowance'] = ppt(line[12])
                entry['Adjustment Allowance']  = ppt(line[13])
                
                #if there is a movement across midnight, this particular runtime needs to have only its To (time) incremented by a day
                if st(line[7]) < st(line[6]):
                    entry['Runtime'] = (st(entry['To (Time)'], add_days=1) - st(entry['From (Time)'])).total_seconds()/60
                
                #else, a normal not-across-midnight runtime calculation
                else:
                    entry['Runtime'] = (st(entry['To (Time)']) - st(entry['From (Time)'])).total_seconds()/60
                    
                entry['Sectional Running Time'] = entry['Runtime'] - sum([ppt(line[n]) for n in range(10,14)])
                
                entry['Dwell'] = prev_dwell = 0
                
                entries.append(entry)

            else:
                raise ValueError(f'Unknown movement prefix {line[0]} inside run at line {lineno}')
                    
    return entries

def formatpex(pex_file, toc_code_lookup_file, tiploc_lookup_file):
    '''
    Top-level function.
    Takes a .pex file path and the Operator (Code) -> Operator (Name) lookup file path.
    Formats a .pex file and returns a DataFrame.
    
    :param pex_file: Absolute path to .pex file
    :param toc_code_lookup_file: Absolute path to a CSV containing 'Business Code' and 'Company Name' columns.
    :param tiploc_lookup_file: Absolute path to a CSV containing 'TIPLOC' and 'Geography Description' columns.
    
    :returns: a DataFrame containing the formatted .pex file.
    '''
    global tocdict, tiplocdict
    
    with open(pex_file, 'r') as f:
        file = f.read().splitlines()
        
    timetable_name = pex_file.split('/')[-1]
    
    tocdf = pd.read_csv(toc_code_lookup_file)
    tocdict = dict(tocdf[['Business Code', 'Company Name']].to_records(index=False))
    
    tiplocdf = pd.read_csv(tiploc_lookup_file)
    tiplocdict = keydict(tiplocdf[['TIPLOC','Geography Description']].to_records(index=False))
    
    #add a dummy line so that the indexes begin at 1,2,3.. instead of 0,1,2..
    file.insert(0,'DMY')
    
    #annotate each file line with line numbers so that, if the list is 
    #sliced later, we still retain the original line numbers
    for lineno, line in enumerate(file):
        file[lineno] = (lineno, line)
    
    #do the formatting
    output = []
    for line in file:
        lineno = line[0]
        raw_line = line[1]
        split_line = s(raw_line)
        prefix = gp(line)
        
        if prefix == 'THD':
            tdt_lines, i = [], 1
            
            while gp(file[lineno+i]) =='TDT':
                tdt_lines.append(file[lineno+i])
                i+=1    
            template = make_template_from_header(timetable_name, thd_line = line, tdt_lines = tdt_lines)
            
            run = []        
            while gp(file[lineno+i]) in ['TSP', 'TMV']:
                run.append(file[lineno+i])
                i+=1
            entries = get_entries_from_run(template, run)  
            output.extend(entries)
        
    return pd.DataFrame(output).set_index('Line in file')
        
def write_csv(formatted_df, output_file_name):
    formatted_df.to_csv(output_file_name)
    
#%%
if __name__ == '__main__':
    pass
    #df = formatpex('file.pex', 'lookup_tables/operator-lookup.csv','lookup_tables/tiploc-lookup.csv' )
    #print(df)
    #write_csv(df, 'output.csv')
      