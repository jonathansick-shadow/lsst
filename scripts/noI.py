#!/usr/bin/env python
#
# Original filename: noI.py
#
# Author: Steve Bickerton
# Email:
# Date: Mon 2009-12-21 09:41:24
#
# Summary:
#
"""
%prog [options]
"""

import sys
import re
import optparse
import os
import glob


##########################
# A function which prints the terminal code to set color/style of text
##########################
def color(col):
    c = {"red": 31, "green": 32, "yellow": 33, "blue": 34, "magenta": 35, "cyan": 36, "reset": 0}
    s = {"bold": 1}

    base = "\033["
    out = 0  # default to 'reset'
    if col in c:
        out = c[col]
    elif col in s:
        out = s[col]
    return base + str(out) + "m"

############################
# A function which searches for a pattern and colors/styles a captured portion of it.
# ##########################


def regexColorReplace(regex, clrs, line):
    m = re.search(regex, line)
    out = line
    found = False
    if (m):
        found = True
        pattern = m.group(1)
        colorPattern = ""
        # note clrs is a list, this way colors and styles can be included together (ie. ["red", "bold"]
        for clr in clrs:
            colorPattern += color(clr)
        colorPattern += pattern + color("reset")
        # if it's just digits, it must be line numbers
        # it'll match all digits, so we'll put the colon (g++ output) in the match expression
        if re.search("^\d+$", pattern):
            out = re.sub(":"+pattern, ":"+colorPattern, line)
        else:
            out = re.sub(pattern, colorPattern, line)

    return out, found


#############################################################
#
# Main body of code
#
#############################################################
def main(filedesc, log, retryscript):

    if log:
        fp_log = open("noI.log", 'w')
        fp_warn = open("noI.warn", 'w')

    ####################################
    # loop over stdin lines
    ####################################

    # have the retry script echo a message if there are no errors
    no_op_mesg = "No errors were found in the most recent scons compile."
    s = "#!/usr/bin/env bash\n"
    s += "echo \"" + no_op_mesg + "\"\n"
    fp = open(retryscript, 'w')
    fp.write(s)
    fp.close()

    i = 0
    nWarning = 0
    compile_lines = {}  # store the compile statement by path of the .cc file
    srcFileLookup = {}  # need to lookup the .cc file to build if the error is in a .h file
    prev_line = ""
    s = ""
    srcFileList = []
    already_compiling = {}  # avoid putting the same build line in the rebuild script multiple times
    raw_lines = []
    iLine = 0
    while(True):
        line = filedesc.readline()

        raw_line = line
        if log:
            fp_log.write(raw_line)

        raw_lines.append(raw_line)
        iLine += 1

        if not line:
            break

        # trim the g++ options (-I -L etc.)
        line = re.sub("\s+-([DILl]|Wl,)\S+", "", line)

        # stash the line if it's a compile statement (starts with 'g++')
        # POSSIBLE BUG if another compiler is used.
        if re.search("^g\+\+", raw_line):
            srcFile = (line.split())[-1]
            srcFileList.append(srcFile)
            compile_lines[srcFile] = raw_line.strip()
            srcFileLookup[srcFile] = srcFile

        ### warnings ###
        line, foundwarn = regexColorReplace("([Ww]arning):", ["yellow"], line)

        ### errors ###

        # write a script to re-execute the compile statement which failed
        # ... no sense redoing the whole configure/build
        m = re.search("^([^:]+):(\d+): error:", line)
        if m:
            errFile = m.groups()[0]

            # if a .h file, need to get the corresponding .cc file
            if re.search("\.h$", errFile):

                ##########
                # need to check two possibilities

                # - .h file included directly in a .cc (it'll be listed on the previous line)
                mm = re.search("^In file included from ([^:]+.cc):(\d+):", raw_lines[iLine-2])

                # - .h file included from a chain of .h
                # (.cc which includes the first in the chain will be on a recent line ... different regex)
                mm2 = False
                maxLines = 2
                iL = 0
                while (not mm2 and iL < maxLines):
                    mm2 = re.search("^\s+from ([^:]+.cc):(\d+):", raw_lines[iLine-2-iL])
                    iL += 1

                ##########
                # now get the appropriate src file for this header error
                if mm:
                    srcFileLookup[errFile] = mm.groups()[0]
                elif mm2:
                    srcFileLookup[errFile] = mm2.groups()[0]

                # last ditch effort ... check the last few g++ statements and see if the outputs are there
                else:
                    maxCheck = 8
                    iCheck = 0
                    while (iCheck < maxCheck):
                        if len(srcFileList) < iCheck:
                            break

                        srcFile = srcFileList[-iCheck]
                        srcPattern = re.sub(".cc$", "", srcFile)
                        possibleObjFiles = glob.glob(srcPattern+".*")  # {o,os,so}")
                        possibleObjFiles = filter(lambda x: re.search(".(o|os|so)$", x), possibleObjFiles)

                        # if it built
                        if len(possibleObjFiles) == 0:
                            srcFileLookup[errFile] = srcFile
                            break

                        iCheck += 1

            if not srcFileLookup.has_key(errFile):
                mesg, found = regexColorReplace("(.*)", ["red"],
                                                "Can't associate "+errFile +
                                                " with a .cc file build.  No entry in build script.")
                print mesg

            else:
                srcFile = srcFileLookup[errFile]
                if not already_compiling.has_key(srcFile):
                    compile_line = compile_lines[srcFile]
                    already_compiling[srcFile] = 1

                    # write the #! line on the first pass
                    if len(s) == 0:
                        s += "#!/usr/bin/env bash\n"

                    # the rebuild script should echo what it's doing and do it.
                    s += "echo \"" + compile_line + "\"\n"
                    s += compile_line + "\n"  # " 2>&1 | " + sys.argv[0] + "\n"

        # highlight the text after searching for 'error' in the line
        # (highlighting inserts extra characters)
        line, found = regexColorReplace("([Ee]rror):", ["red", "bold"], line)

        ### filenames ###
        line, found = regexColorReplace(r'\/?(\w+\.(?:cc|h|i|hpp)):\d+[,:]', ["cyan"], line)

        ### file linenumbers ###
        # don't try to match the filename too, it's now wrapped in \esc for cyan
        line, found = regexColorReplace(':(\d+)[,:]', ["magenta"], line)

        ### tests ###
        line, found = regexColorReplace("(passed)", ["green"], line)
        line, found = regexColorReplace("(failed)", ["red", "bold"], line)

        ### yes/no ###
        line, found = regexColorReplace("(?:\.\.\. ?|\(cached\) ?)(yes)\n", ["green"], line)
        line, found = regexColorReplace("(?:\.\.\. ?|\(cached\) ?)(no)\n", ["red", "bold"], line)

        # add a line number to the output and make it bold
        line = "==" + str(i) + "== " + line

        # log the warning here, so we get the color markup and line number
        if foundwarn:
            nWarning += 1
            if log:
                fp_warn.write(line)

        prev_line = raw_line

        sys.stdout.write(line)
        sys.stdout.flush()

        i += 1

    warnyellow = color("yellow") + "warnings" + color("reset")
    print "There were %d %s (run with -l and see noI.warn)." % (nWarning, warnyellow)

    if len(s) > 0:
        fp = open(retryscript, 'w')
        fp.write(s)
        fp.close()
        os.chmod(retryscript, 0744)

    if log:
        fp_log.close()
        fp_warn.close()

#############################################################
# end
#############################################################

if __name__ == '__main__':

    ########################################################################
    # command line arguments and options
    ########################################################################
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option("-l", "--log", dest="log", action="store_true", default=False,
                      help="Log all messages in noI.log? (default=%default)")
    parser.add_option("-r", "--retryscript", default="b",
                      help="Name of script to retry the most recent compile statment. (default=%default)")
    opts, args = parser.parse_args()

    if len(args) > 0:
        parser.print_help()
        sys.exit(1)

    main(sys.stdin, opts.log, opts.retryscript)
