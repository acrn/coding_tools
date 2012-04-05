#!/usr/bin/env python3

'''
Serches the log files from a GlassFish server for log entries contaning
regexes given by the user. Grep won't do since it operates on lines while we
need to search for patterns in multiline stacktraces.

Example: find_log_entries /SEVERE/ server.log

/.../glassfish/domains/domain1/logs/server.log_2012-03-27T10-14-20 (line 2102)
==============================================================================
[#|2012-03-22T10:48:38.218+0100|SEVERE|glassfish3.1.2| \
    javax.enterprise.system.tools.admin.org.glassfish.deployment.admin| \
    _ThreadID=81;_ThreadName=Thread-2;| \
    The log message is empty or null.  \
    Please log an issue against the component in the logger field.|#]

'''
import re

def aggregate_entries(lines):

    '''Creates a generator yielding tuples of:
      (line_number, log_entry)
    from the lines of a glassfish log. Turns:
      ('[#|2012-04-04...',
       'blablabla|#]',
       '[#|2012-04-04...',
       'blebleble|#]')
    into:
      ((1, [#|2012-04-04...\nblablabla|#]),
       (3, [#|2012-04-04...\nblebleble|#]))

    '''

    rx_end = re.compile(r'.*\|#\]')
    buffer = []
    for line_no, line in enumerate(lines, 1):
        # don't add blank lines at the start of a log entry
        if len(buffer) > 0 or not line.isspace():
            if len(buffer) == 0:
                entry_line_no = line_no
            assert len(buffer) < 5000
            buffer.append(line)
        if rx_end.match(line):
            yield (entry_line_no, buffer)
            buffer = []

def make_regex_filter(regexes):

    '''Creates a closure that matches the lines of an entry against a number
    of regexes. Returns True if a match is found for every regex

    '''

    def matches(entry):
        for regex in regexes:
            if not any(regex.search(l) for l in entry[1]):
                return False
        else:
            return True
    return matches

if __name__ == '__main__':

    import sys

    log_home = '/home/anders/src/java/gf311_domain/logs'
    if len(sys.argv) < 2 or '-h' in sys.argv or '-?' in sys.argv:
        print( 'Usage:', sys.argv[0], ' /[regex 1]/ ... /[regex n]/ '
                '[filename 1] ... [filename n]\n'
                'Example:', sys.argv[0], '/SEVERE/ /NullPointerException/ '
                '~/domain1/logs/server.log*\n\n'
                'If no filenames are given all the files in \n  "'
                + log_home + '"\nare searched')
        sys.exit()

    filenames = []
    regexes = []
    rx_regex_arg = re.compile(r'(^\s*/)(.*)(/\s*$)')
    for arg in sys.argv[1:]:
        match = rx_regex_arg.match(arg)
        if match:
            regex = match.groups()[1]
            regexes.append(re.compile(regex))
        else:
            filenames.append(arg)
    if len(filenames) == 0:
        import os
        filenames = [os.path.join(log_home, n)
                for n in next(os.walk(log_home))[2]]

    for filename in filenames:
        lines = (l for l in open(filename))
        entries = ((n,lines) for n,lines in aggregate_entries(lines))
        matches = filter(make_regex_filter(regexes), entries)
        for n, lines in matches:
            header = filename + ' (line ' + str(n) + ')'
            print(header)
            print(len(header) * '=')
            for line in lines:
                print(line, end='')
            print()
