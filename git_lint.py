#!/usr/bin/env python3

"""runs pylint and shows only the messages for the lines modified a
given commit or the unstaged changes in a repository. The only argument
is a commit hash, an alias such as "HEAD^" is also acceptable. If
no argument is given the unstaged changes (the output of 'git diff')
are checked

Example:

    anders@cadmium:~/src/python/define-4$ git lint 22046ff2

    dir/file1.py
    ========================================
    57: Unable to import 'some.module'
    129: Instance of 'SomeClass' has no 'env' member

    dir/dir/file2.py
    ========================================
    285: Line too long (94/80)
    288: Line too long (81/80)
    325: Unused variable 'something'
"""

import re, subprocess, sys

def commit_hash(ref):
    """Returns the full hash of a git object, 'HEAD^' for instance."""

    output = subprocess.check_output([
        'git',
        'show',
        '--format=%H',
        '--name-only',
        ref]).decode('utf-8')

    return next(re.finditer('\w*', output)).group()

def modified_uncommited_files():
    """Yields the names of all python files that have been modified locally
    and are not yet commited."""

    output = subprocess.check_output([
        'git',
        'status',
        '--porcelain']).decode('utf-8')

    for match in re.finditer(r'^\s*[AMCRU]+\s*(.*\.py)', output, re.M):
        yield match.group(1)

def modified_files_in_commit(commit_hash):
    """Yields the names of all python files that were modified in a given
    commit"""

    output = subprocess.check_output([
        'git',
        'diff-tree',
        '--name-only',
        '--no-commit-id',
        '--root',
        '-r',
        commit_hash]).decode('utf-8')

    for match in re.finditer(r'^.*\.py', output, re.M):
        yield match.group()

def modified_line_nums(filename, commit_hash = None):
    """Yields the line numbers that were modified in a given file in a given
    commit. If not commit_hash yield the line numbers that have been changed
    locally but not yet commited."""

    commit_hash = commit_hash or ('0' * 40) # <- bad
    output = subprocess.check_output([
        'git',
        'blame',
        '--porcelain',
        filename]).decode('utf-8')

    for match in re.finditer(
            r'^{} \d+ (\d+)'.format(commit_hash), output, re.M):
        yield int(match.group(1))


def lint_problems(filename):
    """Yields pylint complaints for a given file. The yielded values are dicts
    like:
       {'filename':    'path/file.py',
        'linenumber':  24,
        'flags':       'C',
        'message':     'bad indentation'}"""

    try:
        output = subprocess.check_output([
            'pylint',
            '--output-format', 'parseable',
            '--reports', 'n',
            filename]).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        # pylint failes with a complicated bit field even for a single
        # convention message. This will almost always happen.
        output = ex.output.decode('utf-8')

    # The lines printed by "pylint --output-format parseable" look like this:
    # define/define/data_default.py:25: [W, get_data] Unused argument 'db'
    pylint_regex = re.compile(r'''
            ^([^ :]+) #  Filename
            :         #
            (\d+)     #  Line number
            :\s*\[    #
            ([^\]]*)  #  Flags or whatever
            \]\s*     #
            (.*)      #  Message
            ''', re.MULTILINE | re.VERBOSE)

    for match in pylint_regex.finditer(output):
        filename, linenumber, flags, message = match.groups()
        yield {
                'filename':    filename,
                'linenumber':  int(linenumber),
                'flags':       flags,
                'message':     message}

if __name__ == '__main__':

    hash_ = commit_hash(sys.argv[1]) if len(sys.argv) > 1 else None

    if hash_:
        files = modified_files_in_commit(hash_)
    else:
        files = modified_uncommited_files()

    for filename in files:
        filename_printed = False
        line_nums = set(modified_line_nums(filename, hash_))
        for problem in lint_problems(filename):
            if problem['linenumber'] in line_nums:
                if not filename_printed:
                    print()
                    print(problem['filename'])
                    print('=' * 40)
                    filename_printed = True
                print('{0[linenumber]}: {0[message]}'.format(problem))
