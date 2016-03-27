#!/usr/bin/env python
#
# Original filename: style.py
#
# Author: Steven Bickerton
# Email: bick@astro.princeton.edu
# Date: Mon 2009-10-05 18:17:57
#
# === Summary: =======================================
#
# This program is used to identify violations of the LSST coding style guidelines
# for C++ source code and headers, and (to a lesser extent) for python scripts.
#
# === Basic Design: ==================================
#
# Each line of the input file is read-in as a Line object, and the file
#   is stored as a python list of Lines.
# Each line contains attributes for:
#    - the actual line read-in: 'line.raw'
#    - the line with comments and strings removed: 'line.stripped' (the most used)
#    - the context of the line (in a class definition, in a private/public block, etc)
# The tests are coded as classes, and all inherit from a 'Test' base class.
# If a test can be defined in a simple RegEx, the class declaration need only
#    call the constructor for the parent 'Test'.
# The Test method 'apply' performs the test.  The 'Test' base class version of 'apply'
#    can handle the simple RegEx case, but more complicated tests must overload 'apply'.
# Test failures are stored as a list of Violation objects.
#    - Each Test 'apply' method returns a python list of Violation objects
#
# In the 'main' body of code:
#   - The list of Lines is passed to each Test and 'apply' is executed.
#   - Any Violations returns are appended to a running list.
#   - Violations with no entry in the '.ignore-style' file are output to the terminal
#
#
# === How to Add a Test: =============================
#
# (There are approximately 50 TestFoo classes defined below which can be used as template/examples.)
# - Look for 'class TestDefault(Test)' and adapt it to perform your test.
# - The list of Tests is created in the function 'initializeTestList()'
#   - In that function, make an entry appending an instantiation of your Test to the list.
#
#
# === How to Add a Sample Violation for Testing =======
#
# Create a sample file (prefixed 'test') containing an example
#    violation of your test and put it in tests/  ... ie. tests/testFoo.cc
#    I haven't gone so far as to require that these actually build,
#    they just contain a few lines, some of which have known failures.
# Idenfity the known failures in the header of your example:
#    - In the header of testFoo.cc put a comment line listing the test code (eg. 3-1), the line
#       that is expected to fail, and a brief explanation of what that rule is ...eg:
#
#    // 3-1 7  It's bad luck to use the word 'superstitious' as a variable name
#
#
#
#
# classes:
#    Test
#    TestXXXX(Test)  # many tests of this form, all inherit from 'Test'
#    Line
#    Violation
#
# functions:
#    flagLines(lines):
#    parseLines(lines, filetype):
#    getPrimitives():
#    getPrimitivesOr():
#    getVariableNames(line, stypes = getPrimitivesOr()):
#    getFunctionNames(line):
#    getTemplateNames(line):
#    getDefinitionLength(lines, iLine):
#    initializeTestList(filetype, infile):
#
# Todo:
# -- set the priorities to correspond to lsst 'severity'
# -- Still need better comments
# -- Recognise parasoft ignore statements


"""
%prog [options] infile
"""

import sys
import re
import optparse
import os
import datetime
import copy


###################################################################
# class Test
# - The Base Class for each test
# - simple regex tests can be created with the constructor alone.
# - more complicated tests overload apply()
# - the getXX() methods need never be overloaded.
#
###################################################################
class Test():

    def __init__(self, severity, regex, id, comment, filetype, typeList = ["c", "cc", "h", "py"]):
        self.severity = severity
        self.regex = regex
        self.id = id
        self.comment = comment
        self.filetype = filetype
        self.typeList = typeList

    def getSeverity(self): return self.severity

    def getRegex(self): return self.regex

    def getId(self): return self.id

    def getComment(self): return self.comment

    def getFiletype(self): return self.filetype  # suffix of the input file

    def getTypeList(self): return self.typeList  # suffixes to apply this test to

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search(self.regex, line.stripped)):
                    vList.append(Violation(self, line))
        return vList


##################################################################
# 3-1 (user types mixed-case, start upper)
class TestUserType(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-1",
                      "User defined types must be mixed-case, starting with uppercase.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                isTypedef = re.search("typedef.*\s+([a-z]\w*);\s*$", line.stripped)
                # we'll let the typedef'd iterators slide through
                isIterator = re.search("iterator;\s*$", line.stripped)
                if isTypedef and not isIterator:
                    vList.append(Violation(self, line))

        return vList


##################################################################
# 3-2 (variables mixed-case, start lower)
class TestVariableName(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-2",
                      "Variable names must be mixed-case, starting with lowercase.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        for line in lines:
            iLine = line

            if (self.getFiletype() in self.getTypeList()):
                for variable in line.variableNames:

                    # strip any pointer/ref characters
                    variable = re.sub("\s*[\*\&]\s*", "", variable)

                    # check for upper case start
                    if (line.inPrivate or line.inProtected):
                        if re.search("^_[A-Z]", variable):
                            vList.append(Violation(self, iLine, "\"" + variable + "\" starts uppercase"))
                        # check for underscores
                        if re.search("^.+_", variable):
                            vList.append(Violation(self, iLine, "\"" + variable +
                                                   "\" constains non-leading underscore"))
                    else:
                        if re.search("^[A-Z]", variable):
                            vList.append(Violation(self, iLine, "\"" + variable + "\" starts uppercase"))
                        # check for underscores
                        if re.search("_", variable):
                            vList.append(Violation(self, iLine, "\"" + variable + "\" constains underscore"))

        return vList


##################################################################
# 3-4 (functions/methods mixed-case, start lower)
class TestFunctionName(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-4",
                      "Function/Method names must be mixed-case, starting with lowercase.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        for line in lines:
            if (self.getFiletype() in self.getTypeList()):
                for functionName in line.functionNames:
                    # check of upper case start
                    if re.search("^[A-Z]", functionName):
                        vList.append(Violation(self, line, "Starts uppercase"))
                    # check for underscores
                    hasUnderscore = re.search("_", functionName)
                    hasNonLeadingUnderscore = re.search("[^_]_", functionName)
                    hasLeadingUnderscore = re.search("^_", functionName)
                    if (not line.inPrivate and hasUnderscore):
                        vList.append(Violation(self, line, "Contains underscore"))
                    if (line.inPrivate and hasNonLeadingUnderscore):
                        vList.append(Violation(self, line, "Contains non-leading underscore"))

        return vList

###################################################################
# 3-5 (typedefs start upper, no 'T' suffix)


class TestTypedef(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "typedef.*(T|_t|Type|TYPE|type);\s*$", "3-5",
                      "typedef ends in T, _t, Type, etc", filetype, ["c", "cc", "h"])


###################################################################
# 3-6  (namespaces all lower)
class TestNamespaceLower(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "namespace\s+[a-z]*[A-Z]+[a-z]*\s*\{", "3-6",
                      "namespace names must be lower case", filetype, ["c", "cc", "h"])


###################################################################
# 3-7  (templates mixed case, start upper, 1 letter ok)
class TestTemplateStartsUpper(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-7",
                      "template names must start upper case.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                templateNameList = getTemplateNames(line.stripped)
                for name in templateNameList:
                    if re.search("^[a-z]", name):
                        vList.append(Violation(self, line, name))
        return vList


###################################################################
# 3-8 (abbrev/acron not all upper in names)
class TestAllCapAbbreviation(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-8",
                      "Possible all-cap abbreviation.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                for variable in line.variableNames:
                    if (re.search("[A-Z]{2}", variable)):
                        vList.append(Violation(self, line, "\"" + variable + "\""))
        return vList


###################################################################
# 3.10 (private variables and functions have '_' prefix)
# - what to do with 'protected' ?
class TestLeadingUnderscore(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-10",
                      "Private variables must be prefixed with leading underscore.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        if (self.getFiletype() in self.getTypeList()):
            vList = []
            for line in lines:
                if line.inPrivate:
                    for variable in line.variableNames:
                        # strip pointer/ref characters
                        tmp = re.sub("\s*[\*\&]\s*", "", variable)
                        # in parens
                        inParens0 = re.search("\([^\)]*" + tmp + "[^\)]*\)$", line.stripped)
                        # has leading paren
                        inParens1 = re.search("\([^\)]*" + tmp + "[^\)]*$", line.stripped)
                        # has trailing paren
                        inParens2 = re.search("^[^\)]*" + tmp + "[^\)]*\)", line.stripped)
                        # is comma separated
                        inCommas = re.search(tmp + ".*,\s*$", line.stripped)
                        isArg = inParens0 or inParens1 or inParens2 or inCommas
                        if (re.search("^[^_]", tmp) and not isArg):
                            vList.append(Violation(self, line, variable))
                    for functionName in line.functionNames:
                        # check for underscores
                        hasLeadingUnderscore = re.search("^_", functionName)
                        if (not hasLeadingUnderscore):
                            vList.append(Violation(self, line, "Missing leading underscore"))

            return vList
        else:
            return []


###################################################################
# 3-14 (avoid object name within method name)
class TestObjectNameInMethod(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-14",
                      "Object name should not appear in a method name.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if line.inClass:
                    for method in line.functionNames:
                        if (re.search(line.className.lower(), method.lower())):
                            vList.append(Violation(self, line))
        return vList


##################################################################
# 3-24  (use prefix 'is' for booleans)
class TestBooleanIs(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-24",
                      "Boolean variables must begin with 'is' or 'has'.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                variableList = getVariableNames(line.stripped, "bool")
                for variable in variableList:
                    if (line.inPrivate or line.inProtected):
                        if (not re.search("^(_is|_has)", variable)):
                            vList.append(Violation(self, line, variable))
                    else:
                        if (not re.search("^(is|has)", variable)):
                            vList.append(Violation(self, line, variable))
        return vList


###################################################################
# 3-28 (avoid negated booleans)
class TestNegativeBoolean(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "3-28", "Avoid negative booleans.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                variableList = getVariableNames(line.stripped, "bool")
                for variable in variableList:
                    if (re.search("[nN]ot?", variable)):
                        vList.append(Violation(self, line, variable))
        return vList


###################################################################
# 4-1.a (use // -*- LSST-C++ -*- as first line)
class TestEmacsHeader(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-1a", "use // -*- LSST-C++ -*- as first line",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            if (not re.search("^//\s+-\*- (?:LSST-C|lsst-c)\+\+ -\*-", lines[0].raw)):
                vList.append(Violation(self, lines[0]))
        return vList

###################################################################
# 4-2 (1-class files named after class)


class TestOneClassFiles(Test):

    def __init__(self, filetype, filename):
        Test.__init__(self, 1, "", "4-2", "Name .h files with one class after that class.", filetype, ["h"])
        self.filename = filename

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            classNames = []
            for line in lines:
                if (line.inClass and (not line.className in classNames)):
                    classNames.append(line.className)

            filenameBase = re.sub(".h$", "", os.path.basename(self.filename))
            if (len(classNames) == 1 and not re.search("^" + classNames[0] + "$", filenameBase)):
                vList.append(Violation(self, line))

        return vList


###################################################################
# 4-4a (All non-template functions in src)
class TestNonTemplateInH(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-4a", "Define all non-templated functions in .cc file", filetype, ["h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                definitionLength = getDefinitionLength(lines, line.number)
                isTooLong = (definitionLength > 1)

                isTemplatized = re.search("^\s*template", lines[line.number - 2].stripped)
                if (len(line.functionNames) > 0 and not isTemplatized and isTooLong):
                    vList.append(Violation(self, line))

        return vList


###################################################################
# 4-5 (inline functions prohibited except for get/set)
class TestInlineProhibited(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-5", "Inline functions prohibited except for get/set.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            for line in lines:

                if (re.search("inline", line.stripped)):
                    definitionLength = getDefinitionLength(lines, line.number)
                    isTooLong = (definitionLength > 1)

                    if (len(line.functionNames) > 0 and isTooLong):
                        vList.append(Violation(self, line))

        return vList


###################################################################
# 4-6 (use < 110 columns)
class TestLength(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-6", "Line more than 110 characters.",
                      filetype, ["c", "cc", "h", "py"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("^.{111,}$", line.raw)):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 4-7 (avoid special characters eg. \t\r\f)
class TestAvoidSpecialChars(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-7", "Avoid special characters.", filetype, ["c", "cc", "h", "py"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("\t", line.stripped)):
                    vList.append(Violation(self, line, "contains \\t"))
                if (re.search("\r", line.stripped)):
                    vList.append(Violation(self, line, "contains \\r"))
                if (re.search("\f", line.stripped)):
                    vList.append(Violation(self, line, "contains \\f"))
        return vList


###################################################################
# 4-9 (prevent multiple header inclusion)
class TestPreventMultipleHeader(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-9", "Prevent multiple header inclusion.", filetype, ["h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            m1 = re.search("^\#if !defined\((LSST_[A-Z_]+_H)\)\s*$", lines[1].stripped)
            m2 = re.search("^\#ifndef (LSST_[A-Z_]+_H)\s*$", lines[1].stripped)
            if (not m1 and not m2):
                vList.append(Violation(self, lines[1]))

            # check the second line too, but only if the first is good
            if m1 or m2:
                if m1:
                    tag = m1.group(1)
                if m2:
                    tag = m2.group(1)
                if (not re.search("^\#define " + tag + "(?:\s+1)?\s*$", lines[2].stripped)):
                    vList.append(Violation(self, lines[2]))

        return vList


####################################################################
# 4-10 (sort and group #includes)
class TestSortGroupIncludes(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-10", "Sort and group #include statments.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            # angle bracket style #include<foo> should preceed quote style #include "foo.h"
            foundQuoteStyle = False
            for line in lines:
                if (re.search("^\#include\s+\"\w+\.h(pp)?\"\s*$", line.stripped)):
                    foundQuoteStyle = True
                if (foundQuoteStyle and re.search("^\#include\s*\<\w+(\.h|\.hpp)?\>\s*$", line.stripped)):
                    vList.append(Violation(self, line))
        return vList


####################################################################
# 4-11 (#includes should preceed all other statements)
class TestIncludesFirst(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "4-11", "#includes should preceed all other statments.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            foundNonIncludeStatement = False
            for line in lines:

                lineTmp = line.stripped

                # strip other preprocessor lines
                lineTmp = re.sub("^#(define|if).*$", "", lineTmp)

                # strip 'extern' statements as they may contain #include
                lineTmp = re.sub("^extern.*$", "", lineTmp)

                if (not re.search("^\#include", lineTmp) and len(lineTmp.strip()) > 0):
                    foundNonIncludeStatement = True
                if (foundNonIncludeStatement and (re.search("^\#include", lineTmp))):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 4-13  ('using' must not appear in header)
class TestUsingInHeader(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\s*using", "4-13",
                      "'using' declaration appears in header file", filetype, ["h"])


####################################################################
# 4-15 (only use <> for system #includes)
class TestAngleBracketInclude(Test):
    # I'll interpret this to mean that if you needed a path to the .h file, it's not system

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\#include\s*\<.*\/.*\>\s*$",
                      "4-15", "Use '#include<>' style for system libraries only.",
                      filetype, ["c", "cc", "h"])


###################################################################
# 5-2 (public/protect/private in order)
class TestPubProPriv(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-2",
                      "Class declaration order public/protected/private:", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        if (self.getFiletype() in self.getTypeList()):
            vList = []
            order = [0, 0, 0]
            nSeg = 0
            for line in lines:

                if (re.search("^\s*public:", line.stripped) and line.inClass and not line.inNestedClass):
                    if order[0]:
                        vList.append(Violation(self, line, "'public' repeated"))
                    nSeg += 1
                    order[0] = nSeg
                if (re.search("^\s*protected:", line.stripped) and line.inClass and not line.inNestedClass):
                    if order[1]:
                        vList.append(Violation(self, line, "'protected' repeated"))
                    nSeg += 1
                    order[1] = nSeg
                if (re.search("^\s*private:", line.stripped) and line.inClass and not line.inNestedClass):
                    if order[2]:
                        vList.append(Violation(self, line, "'private' repeated"))
                    nSeg += 1
                    order[2] = nSeg
                if (re.search("^\s*};\s*", line.stripped) and lines[line.number - 2].inClass and
                        not lines[line.number - 2].inNestedClass):
                    if (
                        (order[0] and order[1] and order[0] > order[1]) or  # pub>pro
                        (order[1] and order[2] and order[1] > order[2]) or  # pro>pri
                        (order[0] and order[2] and order[0] > order[2])  # pub>pri
                    ):
                        msg = "'" + lines[line.number - 2].className + "' out of order"
                        vList.append(Violation(self, line, msg))
                    order, seg = [0, 0, 0], 0
            return vList
        else:
            return []


###################################################################
# 5-3 (no C-style casts)
class TestCCast(Test):

    def __init__(self, filetype):
        ctypes = getPrimitivesOr()
        Test.__init__(self, 1, "\((" + ctypes + ")\s*[\*]?\s*\)\s*[\w\d]+", "5-3", "C-style cast.",
                      filetype, ["c", "cc", "h"])


###################################################################
# 5-8 (public variables must be const or static
class TestPublicConstStatic(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-8", "Public variables must const or static.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                # nNested counts how many blocks are nested ... greater than 1 is a variable in a function
                if (line.inPublic and line.nNested == 1):
                    if (len(line.variableNames) > 0):
                        isArgument = re.search("\([^\)]+" + ".*".join(line.variableNames) + "[^\(]+\)",
                                               line.stripped)
                        isConstStatic = re.search("(const|static)", line.stripped)

                    if (len(line.variableNames) > 0 and not isConstStatic and not isArgument):
                        vList.append(Violation(self, line, "variables: " + ", ".join(line.variableNames)))
        return vList


###################################################################
# 5-10 (put 'const' *after* type name)
class TestConstAfterType(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-10", "Put 'const' after type in declarations.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            stypes = getPrimitivesOr() + "|[A-Z]\w+"
            for line in lines:
                for variable in line.variableNames:
                    variable = re.sub("\*", "\\*", variable)  # pointers
                    variable = re.sub("\&", "\\&", variable)  # refs
                    regex = "const\s+(" + stypes + ")\s+" + variable
                    if (re.search(regex, line.stripped)):
                        vList.append(Violation(self, line))
        return vList


###################################################################
# 5-14 (only loop control in for() )
class TestForLoopControl(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-14", "Put only loop control in parentheses of for() statement",
                      filetype, ["c", "cc", "h"])

    # Note: this only catches one-liners ... hopefully that's most of them
    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("^\s*for\s*\(([^;]+);([^;]+);([^;]+)\)", line.stripped) and
                        re.search(",", line.stripped)):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 5-16 (avoid 'do-while')
class TestDoWhile(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\s*do\s*\{", "5-16", "Avoid 'do-while' loops",
                      filetype, ["c", "cc", "h"])


###################################################################
# 5-17 (avoid 'break', 'continue')
class TestBreakContinue(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-17", "Avoid using 'break' and 'continue'.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            inSwitch = False
            nNested = 0
            for line in lines:

                if (re.search("^\s*switch", line.stripped)):
                    inSwitch = True
                    nNested = 0
                if (re.search("\{", line.stripped)):
                    nNested += 1
                if (re.search("\}", line.stripped)):
                    nNested -= 1
                if (re.search("\}", line.stripped) and inSwitch and nNested == 0):
                    inSwitch = False

                if (re.search("^\s*break;", line.stripped) and not inSwitch):
                    vList.append(Violation(self, line, "used 'break'"))

                if (re.search("^\s*continue;", line.stripped)):
                    vList.append(Violation(self, line, "used 'continue'"))

        return vList

###################################################################
# 5-21 (put conditional on separate line)


class TestNoOneLinerIf(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\s*if\s*\([^\)]+\)\s*\{[^\}]+\}", "5-21",
                      "Put conditional statements on separate line.", filetype, ["c", "cc", "h"])


###################################################################
# 5-22 (no executibles in conditional)
class TestExecutibleConditional(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\s*(if|while)\s*\([^\)]+[^\=\!\>\<]\=[^\=][^\)]+\)", "5-22",
                      "No executible (assignments) in conditional statments.",
                      filetype, ["c", "cc", "h"])


###################################################################
# 5-24 (pass non-primitives by const ref)
class TestConstRefForNonPrimitives(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-24",
                      "Pass non-primitives as 'const &'.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            primitives = getPrimitives()
            inParentheses = False
            for line in lines:

                declarations = []

                if (line.functionNames):
                    inParentheses = True
                if (inParentheses):

                    # if the declaration is all on one line
                    # if it contains no white space it's a variable being instantiated, not an arg list
                    m = re.search("^[^\(]+\(([^\)]+\s[^\)]+)\)\s*[\{;]?\s*$", line.stripped)
                    if m:
                        declarations = m.group(1).split(",")
                        inParentheses = False

                    # if the declaration is spread over a few lines
                    m = re.search("^[^\(]+\(([^\)]+)$", line.stripped)               # first line
                    if m:
                        declarations = m.group(1).split(",")
                    m = re.search("^\s*([^\(\)]+)$", line.stripped)                  # any middle line
                    if m:
                        declarations = m.group(1).split(",")
                    m = re.search("^\s*([^\(\)]+)\s*\)(?:\s*const)?\s*[\{;:]?\s*$",
                                  line.stripped)  # last line
                    if m:
                        declarations = m.group(1).split(",")
                        inParentheses = False

                if (inParentheses and re.search("\)(?:\s*const)?\s*[\{;:]", line.stripped)):
                    inParentheses = False

                for declaration in declarations:
                    # if it contains no white space, it's just a function being called.
                    # --> strip out any misleading whitespace before checking (ie. around operators)
                    tmp = re.sub("\s*([\,\=\+\-\*\/;\(\)])\s*", r'\1', declaration.strip())
                    if (declaration == '\n' or not re.search("\s", tmp)):
                        continue
                    isPrimitive = False
                    for primitive in primitives:
                        if (re.search(primitive, declaration)):
                            isPrimitive = True
                    if (not isPrimitive and
                            not re.search("(const\s*\&|Ptr)", declaration)):
                        vList.append(Violation(self, line))
        return vList


###################################################################
# 5-27 (1-arg constructors must be 'explicit')
class TestOneArgConstructors(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-27",
                      "One-argument constructors must be declared explicit.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if line.inPublic:
                    # if it's only 1 arg, it should fit on one line ... there will be exceptions
                    m = re.search("^\s*([^\(]+)\s*\([^\),]+\s[^\),]+\)", line.stripped)
                    if m:
                        name = re.sub(r"([\&\[\]])", r'\\\1', m.group(1))
                        if (re.search(name, line.className) and
                                not re.search("^\s*explicit", line.stripped)):
                            vList.append(Violation(self, line))
        return vList


###################################################################
# 5-28 (no exceptions in desctructors)
class TestDestructorExceptions(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-28",
                      "Do not throw exceptions in a destructor.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            inDestructor = False
            nNested = 0
            for line in lines:

                if (re.search("^\s*((?:\s*virtual\s*)\~|\w+::\~)", line.stripped)):
                    inDestructor = True
                    nNested = 0
                if (re.search("\{", line.stripped)):
                    nNested += 1
                if (re.search("\}", line.stripped)):
                    nNested -= 1
                if (re.search("\}", line.stripped) and inDestructor and nNested == 0):
                    inDestructor = False
                if (inDestructor and re.search("^\s*throw", line.stripped)):
                    vList.append(Violation(self, line))

        return vList


##################################################################
# 5-29 (destructors should be virtual)
class TestVirtualDestructor(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-29", "Polym. base class destructors should be virtual",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                # virtual declaration is only in the class definition
                isDestructor = re.search("^\s*\~", line.stripped)
                isBaseClass = line.inClass and re.search("Base$", line.className)
                isVirtual = re.search("^\s*virtual", line.stripped)
                if (isDestructor and isBaseClass and not isVirtual):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 5-31 (show 1 dec point for float/double)
class TestShowOneDecimal(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "\d+\.[\s\*\+\-\/\=\;\)]", "5-31",
                      "Show one decimal point for float/double.", filetype, ["c", "cc", "h", "py"])

###################################################################
# 5-32 (show digit before dec for float/double)


class TestShowDigitBefore(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "[^\d]\.\d+", "5-32",
                      "Show one digit before the decimal for float/double.",
                      filetype, ["c", "cc", "h", "py"])

###################################################################
# 5-33 (no 'goto')


class TestNoGoto(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "\s*goto\s", "5-33", "Do not use 'goto'.", filetype, ["c", "cc", "h"])


###################################################################
# 5-39 (use std::string instead of char*)
class TestCharStar(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-39", "Use std::string instead of char*.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                # allow char * for argv[]
                if (re.search("char\s*(const\s*)?\*", line.stripped) and
                        not re.search("^int main", line.stripped)):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 5-40 (use std::vector<> instead of x[]
class TestCArray(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-40", "use std::vector<> instead of x[]", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                for variable in line.variableNames:
                    if (re.search("\[[^\]]+\]", variable)):
                        vList.append(Violation(self, line))
        return vList


###################################################################
# 5-41 ('using' only for std)
class TestUsingOnlyStd(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "5-41", "'using' only for namespace std", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("^\s*using", line.stripped) and
                        not re.search("\s*std\s*;\s*$", line.stripped)):
                    vList.append(Violation(self, line))
        return vList

###################################################################
# 6-1 (no multiple statements per line)


class TestMultipleStatement(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, ";.*;\s*$", "6-1", "Only one statement per line.",
                      filetype, ["c", "cc", "h"])


###################################################################
# 6-2 (use 4-space indentation)
class TestFourSpaceIndent(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-2", "Use 4-space indentation", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []

        # don't enforce this for line continuation of argument lists or other parenthesized statements
        inParentheses = False
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:

                if (re.search("\([^\)]+$", line.stripped)):
                    inParentheses = True
                m = re.search("^(\s*)[^\s]", line.stripped)
                if (m and not (inParentheses or re.search("^\s*(case|default)", line.stripped))):
                    leadingSpace = m.group(1)
                    nLead = len(leadingSpace)

                    # check and see if we're aligned to a '('
                    # ... the inParentheses test above will fail if an arg is x = func(y)
                    isBracketAligned = False
                    jLine = line.number - 2   # the previous line

                    while (line.number - jLine < 8 and jLine > 0):
                        if len(lines[jLine].stripped) < (nLead + 1) or nLead == 0:
                            jLine -= 1
                            continue
                        # if we're a ');', look for a '('
                        # OR look for a '(' one space earlier
                        if ((re.search("[\)\]]", line.stripped[nLead]) and
                             re.search("[\(\[]", lines[jLine].stripped[nLead])) or
                                re.search("\(", lines[jLine].stripped[nLead - 1])):
                            isBracketAligned = True
                            break

                        jLine -= 1

                    # check if the last char on the prev line was ','
                    # -- this catches argument lists that stretch over one line
                    #   - tempting to check ';' to catch for() loops, but ';' terminates all lines
                    m = re.search("([^\s])\s*$", lines[line.number - 2].stripped)
                    isContinuation = False
                    if (m and (m.group(1) == ",")):
                        isContinuation = True

                    if (nLead % 4 != 0 and not (isContinuation or isBracketAligned)):
                        vList.append(Violation(self, line))
                if (inParentheses and re.search("[^\(]+\)", line.stripped)):
                    inParentheses = False
        return vList


####################################################################
# 6-4 (use K&R block style)
class TestKR(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-4", "Use K&R block style.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                # a lone '{' is non-KR style, unless the previous line is blank
                #  ... then it's ok as it denotes a block-scope
                if (re.search("^\s*\{", line.stripped) and
                        re.search("[^\s]+", lines[line.number - 2].stripped)):
                    vList.append(Violation(self, line))
        return vList


####################################################################
# 6-5 (public/protected/private left justified)
class TestClassBlocksLeft(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-5", "class/public/protected/private should be left justified.",
                      filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("^.+(class|private|protected|public):", line.stripped) and
                        not line.inNestedClass):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# 6-9 (put empty loops on one line)
class TestEmptyLoopOneLine(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-9", "Empty loops should be on one line.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("\{\s*$", line.stripped) and
                        re.search("^\s*\}\s*$", lines[line.number].stripped)):
                    vList.append(Violation(self, line))
        return vList


####################################################################
# 6-14 (omit brackets only for one-liners)
# - could just look for a closing ')' as the last char ... ?
class TestBracketsMissing(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "^\s*(if|for|while)\s*\([^\)]+\)\s*$", "6-14",
                      "Brackets may be omitted only for one line statements.", filetype, ["c", "cc", "h"])


###################################################################
# 6-16a (use whitespace around +/-)
# - this test should check *,/,>,<,= ... but all of these are tricky ... eventually.
class TestOperatorSpacing(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-16a", "Operator spacing: ", filetype, ["c", "cc", "h", "py"])

    def apply(self, lines):
        vList = []

        if (self.getFiletype() in self.getTypeList()):
            for line in lines:

                mequal = re.search("(.?[\w\d]\=[^\=]|.?[^\!\&\|\+\-\*\/\=]\=[\w\d])", line.stripped)
                mplus = re.search("(.?[\w\d]\+[^\+\=]|.?[^\+]\+[\w\d])", line.stripped)
                mminus = re.search("(.?[\w\d]\-[^\-\=]|.?[^\-]\-[\w\d])", line.stripped)

                if mequal:
                    isDefault = False
                    if line.variableNames > 0:
                        isDefaultSameLine = re.search("\([^\)]*([^=]=[^=])+[^\(]*\)", line.stripped)
                        isDefaultDiffLine = re.search("[\d\w]=[\d\w]+(?:\<\w+\>)?(?:\(.*\))?,", line.stripped)
                        mOvr = re.search("operator=\(", line.stripped)
                        isDefault = isDefaultSameLine or isDefaultDiffLine or mOvr
                    if not isDefault:
                        vList.append(Violation(self, line, "failed '='"))

                # plus and minus appear in the other contexts ... check those!
                if mplus:
                    match = mplus.group(1)
                    mSciP = re.search("[\d\.][eE]\+\d", match)  # sci.not
                    mPosP = re.search("[\:\=\+\-\*\/\(\,\<\>\?]\s*\+", match)  # +ve num
                    mOvrP = re.search("operator\+\(", line.stripped)  # operator+ overload
                    mRetP = re.search("return\s+\+", line.stripped)  # returning +ve
                    mEolP = re.search("\+$", line.stripped)             # end of line
                    mBolP = re.search("^\s*\+", line.stripped)             # beginning of line
                    if (not (mSciP or mPosP or mOvrP or mEolP or mBolP)):
                        vList.append(Violation(self, line, "failed '+'"))
                if mminus:
                    match = mminus.group(1)
                    mSciN = re.search("[\d\.][eE]\-\d", match)  # sci.not
                    mNegN = re.search("[\:\=\+\-\*\/\(\,\<\>\?]\s*\-", match)  # -ve num
                    mRetN = re.search("return\s+\-", line.stripped)     # returning -ve
                    mOvrN = re.search("operator\-\(", line.stripped)    # operator- overload
                    mEolN = re.search("\-$", line.stripped)             # end of line
                    mBolN = re.search("^\s*\-", line.stripped)             # beginning of line
                    pointDeref = re.search("\->", match)
                    if (not (mSciN or mNegN or mRetN or mOvrN or mEolN or mBolN or pointDeref)):
                        vList.append(Violation(self, line, "failed '-'"))

                if (re.search("([^\s][\!\&\|\+\-\*\/]\=|[\!\&\|\+\-\*\/]\=[^\s])", line.stripped)):
                    mOvr = re.search("operator[\&\|\*\+\-\/]?=\(", line.stripped)
                    if not mOvr:
                        vList.append(Violation(self, line, "failed '[&|+-*/]='"))

        return vList


###################################################################
# 6-16b (use space after comma)
class TestCommaSpace(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-16b", "Missing whitespace.", filetype, ["c", "cc", "h", "py"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                # careful, comma followed by \n is ok.
                if (re.search(",[^\s]", line.stripped) and not re.search(",\s*$", line.stripped)):
                    vList.append(Violation(self, line, "after comma"))
                m = re.search("^\s*(for|if|while|else|switch)[^\s\w]", line.stripped)
                if (m and re.search("^(cc|c|h)$", self.getFiletype())):
                    rword = m.group(1)
                    vList.append(Violation(self, line, "after reserved word '" + rword + "'"))
                # semi as last character is ok
                if (re.search(";[^\s]", line.stripped) and not re.search(";$", line.stripped)):
                    vList.append(Violation(self, line, "after semi-colon"))

        return vList


###################################################################
# 6-21b (left-align nested namespaces)
class TestNestedNamespacesLeft(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "6-21b", "Left-align nested namespaces.", filetype, ["c", "cc", "h"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search("namespace.*namespace", line.stripped)):
                    vList.append(Violation(self, line))
                if (re.search("^\s+namespace", line.stripped)):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# default (a template for new tests)
class TestDefault(Test):

    def __init__(self, filetype):
        Test.__init__(self, 1, "", "", "", filetype, ["c", "cc", "h", "py"])

    def apply(self, lines):
        vList = []
        if (self.getFiletype() in self.getTypeList()):
            for line in lines:
                if (re.search(Test.getRegex(self), line.stripped)):
                    vList.append(Violation(self, line))
        return vList


###################################################################
# class Violation
# - Each violation is stored as an instance of this class
#
###################################################################
class Violation():

    def __init__(self, test, line, extraComment = ""):
        self.test = test
        self.line = line
        self.lineNumber = line.number
        self.extraComment = extraComment

    def getComment(self):
        extraComment = ""
        if (len(self.extraComment) > 0):
            extraComment = " (" + self.extraComment + ")"
        return self.test.getComment() + extraComment

    def getId(self): return self.test.getId()

    def getSeverity(self): return self.test.getSeverity()

    def getLineNumber(self): return self.lineNumber


###################################################################
# class Line
# - Information about each line is stored in this structure
#
###################################################################
class Line():

    def __init__(self, raw, stripped):
        self.stripped = stripped
        self.raw = raw
        self.number = 0
        self.variableNames = []
        self.functionNames = []
        self.templateNames = []
        self.inClass = False
        self.inStruct = False
        self.inPublic = False
        self.inProtected = False
        self.inPrivate = False
        self.inNestedClass = False
        self.inNestedStruct = False
        self.className = ""
        self.structName = ""
        self.suppress = []

###################################################################
# Function flagLines
# - annotate each line with information about what it contains:
#   ... is it in a private: block? etc
#
###################################################################


def flagLines(lines):

    inClass = False
    inStruct = False
    inPublic = False
    inProtected = False
    inPrivate = False
    inNestedClass = False
    inNestedStruct = False

    nNested = 0
    className = ""
    structName = ""

    for line in lines:

        # class information
        m = re.search("^\s*class\s+(\w+)\s*:?\s+", line.stripped)
        if m:
            className = m.group(1)
            if inClass or inStruct:
                inNestedClass = True
            inClass, inStruct, inPublic, inProtected, inPrivate = True, False, False, False, False

        # struct information
        m = re.search("^\s*struct\s+(\w+)\s*:?\s+", line.stripped)
        if m:
            structName = m.group(1)
            if (inClass or inStruct):
                inNestedStruct = True
            inClass, inStruct, inPublic, inProtected, inPrivate = False, True, False, False, False

        justInClassStruct = (inClass or inStruct) and not (inNestedClass or inNestedStruct)
        if ((justInClassStruct) and re.search("^\s*public:", line.stripped)):
            inPublic, inProtected, inPrivate = True, False, False
        if ((justInClassStruct) and re.search("^\s*protected:", line.stripped)):
            inPublic, inProtected, inPrivate = False, True, False
        if ((justInClassStruct) and re.search("^\s*private:", line.stripped)):
            inPublic, inProtected, inPrivate = False, False, True
        if ((justInClassStruct) and re.search("^};\s*", line.stripped)):
            inClass, inStruct, inPublic, inProtected, inPrivate = False, False, False, False, False

        if (inNestedClass and re.search("^};\s*", line.stripped)):
            inNestedClass = False
        if (inNestedStruct and re.search("^\};\s*", line.stripped)):
            inNestedStruct = False

        line.inClass = inClass
        line.inStruct = inStruct
        line.inPublic = inPublic
        line.inProtected = inProtected
        line.inPrivate = inPrivate
        line.inNestedClass = inNestedClass
        line.inNestedStruct = inNestedStruct

        if inClass:
            line.className = className
        if inStruct:
            line.structName = structName

        if (re.search("\{", line.stripped)):
            nNested += 1
        if (re.search("\}", line.stripped)):
            nNested -= 1

        line.nNested = nNested

        #char = ""
        #if inClass: char += "C"
        #if inPrivate: char += "V"
        #if inProtected: char += "T"
        #if inPublic: char += "B"
        # print char + " " + line.stripped,

        # variables, functions, templates
        line.variableNames = getVariableNames(line.stripped)
        line.functionNames = getFunctionNames(line.stripped)
        line.templateNames = getTemplateNames(line.stripped)

    return lines


###################################################################
# Function parseLines
# - removes all non-code strings (comments and quoted strings)
# - be careful not to delete lines! that will break the line number count
#
###################################################################
def parseLines(lines, filetype):

    inComment = False
    inPyDoc = False
    newLines = []
    iLine = 0
    for raw in lines:

        iLine += 1
        stripped = raw

        #################################################
        # C/C++ comments
        if (filetype in ["c", "cc", "h"]):
            # /* */ style
            if (re.search("\/\*", stripped) and not inComment):
                if (re.search("\*\/", stripped)):
                    stripped = re.sub("\/\*.+?\*\/", "", stripped)
                else:
                    stripped = re.sub("\/\*.*$", "", stripped)
                    inComment = True
            if (re.search("\*\/", stripped) and inComment):
                stripped = re.sub("^.*\*\/", "", stripped)
                inComment = False
            if (inComment):
                stripped = ""
            stripped = re.sub("\/\/\/<.*$", "", stripped)  # C doxygen style comments
            stripped = re.sub("\/\/+.*$", "", stripped)   # C // style comments

            # kill normal strings, but leave #included filenames alone
            if (not re.search("^\#include", stripped)):
                stripped = re.sub("\"[^\"]*\"", "\"\"", stripped)

        ################################################
        # Python comments
        if (filetype in ["py"]):
            # handle """  """ python strings
            if (re.search("\"\"\"", stripped) and not inPyDoc):
                if (re.search("\"\"\".*?\"\"\"", stripped)):
                    stripped = re.sub("\"\"\".*?\"\"\"", "", stripped)
                else:
                    stripped = re.sub("\"\"\".*$", "", stripped)
                    inPyDoc = True
            if (re.search(".*\"\"\"", stripped) and inPyDoc):
                stripped = re.sub("^.*\"\"\"", "", stripped)
                inPyDoc = False
            if (inPyDoc):
                stripped = ""

            stripped = re.sub("\\\\\"", "", stripped)         # kill escaped \" characters
            stripped = re.sub("\"[^\"]*\"", "\"\"", stripped)  # kill normal strings
            stripped = re.sub("#.*$", "", stripped)           # kill python comments

        ####################################################
        # create the line structure
        line = Line(raw, stripped)
        line.number = iLine
        newLines.append(line)

        ####################################################
        # note if what's being suppressed
        m = re.search("parasoft-suppress\s+([^\"]+)", raw)
        if m:
            line.suppress += m.group(1).split()

    flaggedLines = flagLines(newLines)
    return flaggedLines


###################################################################
# function getPrimitives
# - returns a list of primitive types
###################################################################
def getPrimitives():
    primitives = ["int", "float", "double", "unsigned int", "char",
                  "long", "long long", "unsigned short", "unsigned short int", "bool"]
    return primitives

###################################################################
# function getPrimitivesOr
# - returns an or'd string of primitive types
###################################################################


def getPrimitivesOr():
    return "|".join(getPrimitives())


def getUserTypeRegex():
    return "[A-Z]\w+(?:\<\w+\>)?"

###################################################################
# function getVariableNames
# - returns a list of variable Names defined on the given line
# - can specify the type of the variable
###################################################################


def getVariableNames(line, stypes = getPrimitivesOr() + "|" + getUserTypeRegex()):

    # clear out 'const', 'static', and some whitespace ... makes the regex matching easier
    # kill possible 'const = 0' as that denote a virtual function
    originalLine = line
    line = re.sub("const(\s*=\s*0)?", "", line)
    line = re.sub("static", "", line)
    line = re.sub("typename", "", line)

    line = re.sub("^\s+", "", line)
    line = re.sub("\s+", " ", line)
    line = re.sub("\s*([\,\=\+\-\/;\(\)\?\:\>\<])\s*", r'\1', line)

    #######################################################################
    # if it's a function declaration, extract the argument list

    # match comma in () ... must be a function  ... not true, could be instantiation
    #  ... yikes: could be assigned to a function
    rawList = [line]
    if (re.search("[^\=]+\([^\)]+\,[^\)]+\)", line)):
        line = re.sub("^[^\(]+\(", "", line)
        line = re.sub("\)[^\)]*$", "", line)
        rawList = line.split(",")

    # or else ... if there's whitespace between the parens and it's not a 'new' something
    # ... that's a function too
    elif (re.search("\([^\)]+\s[^\)]+\)", line) and
          not re.search("\(new\s[^\)]+\)", line) and
          not re.search("\([^\)]+\)\s*\?\s*", line)):  # don't strip a ternary conditional
        line = re.sub("[^\(]+\(", "", line)
        line = re.sub("\)[^\)]*$", "", line)
        rawList = [line]

    # if there are "::" before '(', it's probably a function ... grab any arguments
    elif (re.search("[^\(]+::[^\(]+\(", line)):
        line = re.sub("[^\(]+::[^\(]+\(", "", line)
        if (re.search("\)[^\)]*", line)):
            line = re.sub("\)[^\)]*", "", line)
        rawList = [line]

    # if there's an unmatched ')' at the end of the line, it's a continuation of an arg list
    elif (re.search("^[^\(]+\)\s*[;\{]?\s*$", line)):
        line = re.sub("\)\s*[;\{]?\s*$", "", line)
        rawList = [line]

    #############################################################################
    # eliminate other possible confusing parts

    # if we see a single colon, we want nothing after it (probably setting private vars from arg list)
    m = re.search("[^:]:([^:].*)$", line)
    if m:
        s = re.sub("([\(\)])", r'\\\1', m.group(1))
        line = re.sub(":" + s + "$", "", line)
        rawList = [line]

    ###########################################################################
    # try to match each candidate variable declaration
    variableList = []
    # if re.search("four", line):
    #    print rawList
    for raw in rawList:

        # don't get fooled by return statements
        if re.search("^\s*return\s", raw):
            continue

        base = "^(?:" + stypes + ")"
        pointRef = "(?:\s+[\&\*]\s*|[\&\*]\s+|\s+)"
        plainVar = "\w[\w\d]*"         # plain variable ... no assignment

        # do a triage step to see if the line looks like a variable declaration
        if (not re.search(base + pointRef + plainVar, raw)):
            continue

        # catch generic declaration: double const Foo = 5;
        assignedVar = "\=[^\s\,]+"
        # catch instantiation:       double const Foo(5);
        instantVar = "\s?\([^\)]+\)"
        # catch arrays
        arrayVar = "\s?\[[^\]]+\]"

        # if there are commas, look for multiple variables
        if (re.search("[^\s]\s*\,\s*[^\s]", raw)):
            rawSplitList = raw.split(",")
        else:
            rawSplitList = [raw]

        variables = []
        for rawSplit in rawSplitList:
            rawSplit = re.sub(base, "", rawSplit)    # strip off the type
            rawSplit = re.sub(";\s*$", "", rawSplit)  # remove the ';'
            regex = ("(" + plainVar + "(?:" +
                     assignedVar + "|" + instantVar + "|" + arrayVar + ")?)$")
            m = re.search(regex, rawSplit)
            if m:
                variables.append(m.group(1))

        for variable in variables:
            if variable != '\n':
                variable = re.sub("=.*$", "", variable)  # strip '=' assignment
                variable = re.sub("\([^\)]*\)", "", variable)  # strip '()' assignment
                regex = "\<[^\>]*" + variable + "[^\<]*\>"  # ignore it if it's in a template list
                mm = re.search(regex, originalLine)
                if not mm:
                    variableList.append(variable.strip())

    return variableList


###################################################################
# function getFunctionNames
# - returns a list of function Names defined on the given line
###################################################################
def getFunctionNames(line):

    # regex 'or' of standard types ... and try to pick up user-defined ones with [A-Z]\w+
    stypes = getPrimitivesOr() + "|[A-Z]\w+"

    functionNameList = []

    # several ways a function decl line could terminate:
    possLineEnd = "\)\s*\{|\,|\)\s*\{\s*\};|"
    regex = ("^\s*(?:inline\s+)?(?:" + stypes +
             ")(?:\s+const)?(?:\s+[\&\*]\s*|\s*[\&\*]\s+|\s+)(\w[\w\d]*)\(.*(?:" +
             possLineEnd + ")\s*$")
    m = re.search(regex, line)
    if m:
        functionNameList.append(m.group(1))

    return functionNameList


###################################################################
# function getTemplateNames
# - returns a list of template names defined on the given line
###################################################################
def getTemplateNames(line):
    templateNameList = []
    m = re.search("^\s*template<(.*?)>\s*$", line)
    if m:
        templateString = m.group(1)
        templateNames = re.sub(",?\s*(typename|class|bool|float|double|int|unsigned int)",
                               "", templateString)
        templateNameList += templateNames.split()
    return templateNameList


###################################################################
# function getDefinitionLength
# - needed a way to distinguish between declaration (ending in ';')
#   and a definition (with a block of code in {})
# - either could be on multiple lines, so
#   --> if we see a line ending in ';' before we see
#       a line ending in '{' ... it's a declaration, otherwise, definition.
# - if it's a definition ... return the number of lines
###################################################################
def getDefinitionLength(lines, iLine):

    isDefinition = None
    jLine = iLine - 1
    while (jLine < len(lines)):
        if (re.search(";\s*$", lines[jLine].stripped)):
            isDefinition = False
            break
        if (re.search("\{", lines[jLine].stripped)):
            isDefinition = True
            break
        jLine += 1

    # if it's a definition ... count the lines
    definitionLength = -1
    if (isDefinition):
        jLine = iLine - 1
        while (not re.search("\}", lines[jLine].stripped)):
            jLine += 1
        definitionLength = jLine - iLine

    return definitionLength


##########################################################################
# Function initializeTestList()
# - build the list of test objects
#
##########################################################################
def initializeTestList(filetype, infile):
    testList = []

    # total tests currently implemented = 50

    # 2-1 (write good code)                                   --> can't detect
    # 2-2 =deleted=                                           --> NA
    # 2-3 (rules can be bent/broken)                          --> NA
    # 2-4 (use object oriented design)                        --> can't detect

    # total 11
    testList.append(TestUserType(filetype))                 # 3-1 (user types mixed-case, start upper)
    testList.append(TestVariableName(filetype))             # 3-2 (variables mixed-case, start lower)
    # 3-3 (named constants all upper case)                    --> not required
    testList.append(TestFunctionName(filetype))             # 3-4 (meth/func names verbs, mixed, start low)
    testList.append(TestTypedef(filetype))                  # 3-5 (typedefs start upper, no 'T' suffix)
    testList.append(TestNamespaceLower(filetype))           # 3-6 (namespaces all lower)
    testList.append(TestTemplateStartsUpper(filetype))      # 3-7 (templates start upper, 1 letter ok)
    testList.append(TestAllCapAbbreviation(filetype))       # 3-8 (abbrev/acron not all upper in names)
    # 3-9 (globals prefixed with '::')                        --> tricky
    testList.append(TestLeadingUnderscore(filetype))        # 3-10 (private variables have '_' prefix)
    # 3-11 (generic vars can have same name as type)          --> can't detect
    # 3-12 (all names in American English)                    --> can't detect
    # 3-13 (variable name length goes as scope size)          --> can't detect
    testList.append(TestObjectNameInMethod(filetype))       # 3-14 (avoid object name within method name)
    # 3-15 (use get/set to access attributes)                 --> can't detect
    # 3-16 (use 'compute' in names that compute)              --> can't detect
    # 3-17 (use 'find' in names that look-up)                 --> can't detect
    # 3-18 (use 'initialize' in names that estab)             --> can't detect
    # 3-19 (use name as suffix for GUI components)            --> can't detect
    # 3-20 (use 'List' as suffix for lists)                   --> can't detect
    # 3-21 (use prefix 'n' for number variables)              --> can't detect
    # 3-22 (use prefix 'i' for entity number)                 --> can't detect
    # 3-23 (use i,j,k for iterators)                          --> not a strict requirement
    testList.append(TestBooleanIs(filetype))                # 3-24 (use prefix 'is' for booleans)
    # 3-25 (complement names for complement ops)              --> can't detect
    # 3-26 (avoid abbreviations in names)                     --> can't detect
    # 3-27 =deleted=                                          --> NA
    testList.append(TestNegativeBoolean(filetype))          # 3-28 (avoid negated booleans)
    # 3-29 (prefix enums with a common type)                  --> can't detect
    # 3-30 (except classes suffix 'Exception')                --> can't detect
    # 3-31 (name funcs after return, procs after do)          --> can't detect
    # 3-32 (func params in order: out, in, dflt-in)           --> can't detect

    # total 11
    # 4-1 (use .h for headers, .cc for src)                   --> implied
    testList.append(TestEmacsHeader(filetype))              # 4-1.a (use // -*- LSST-C++ -*-)
    testList.append(TestOneClassFiles(filetype, infile))    # 4-2 (1-class files named after class)
    # 4-3 (member funcs and data listed logically)            --> can't detect
    testList.append(TestNonTemplateInH(filetype))           # 4-4a (all non-template funcs in src)
    # 4-4b (instantiate all templates in src)                 --> not sure how to test
    testList.append(TestInlineProhibited(filetype))         # 4-5 (inline funcs prohibited except get/set)
    testList.append(TestLength(filetype))                   # 4-6 (use < 110 columns)
    testList.append(TestAvoidSpecialChars(filetype))        # 4-7 (avoid special chars eg \t\r\f)
    # 4-8 (indent continuation lines)                         --> not sure how to test
    testList.append(TestPreventMultipleHeader(filetype))    # 4-9 (prevent multiple header inclusion)
    testList.append(TestSortGroupIncludes(filetype))        # 4-10 (sort and group #includes)
    testList.append(TestIncludesFirst(filetype))            # 4-11 (#includes at top of file)
    # 4-12 (no unused #includes in src)                       --> can't detect
    testList.append(TestUsingInHeader(filetype))            # 4-13 ('using' must not appear in header)
    # 4-14 (header for each library)                          --> can't detect
    testList.append(TestAngleBracketInclude(filetype))      # 4-15 (use '<>' only for system #includes)

    # total 19
    # 5-1 (declare local types in cc file)                    # --> can't detect
    testList.append(TestPubProPriv(filetype))               # 5-2 (public/protect/private in order)
    testList.append(TestCCast(filetype))                    # 5-3 (no C-style casts)
    # 5-4 (init variables when declared)                      # --> too many exceptions
    # 5-5 (multiple assign with const scope)                  # --> too tricky
    # 5-6 (no 'dual-meaning' variables)                       # --> can't detect
    # 5-7 (avoid globals)                                     # --> too tricky
    testList.append(TestPublicConstStatic(filetype))        # 5-8 (public vars must be const/static)
    # 5-9 (declare related vars in same statement)            # --> can't detect
    testList.append(TestConstAfterType(filetype))           # 5-10 (put 'const' *after* type name)
    # 5-11 (test == 0 explicitly)                             # --> can't detect
    # 5-12 (no equality tests for float/double)               # --> can't detect
    # 5-13 (declare vars in smallest scope possible)          # --> can't detect
    testList.append(TestForLoopControl(filetype))           # 5-14 (only loop control in for() )
    # 5-15 (init loop vars just before loop)                  # --> can't detect
    testList.append(TestDoWhile(filetype))                  # 5-16 (avoid 'do-while')
    testList.append(TestBreakContinue(filetype))            # 5-17 (avoid 'break', 'continue')
    # 5-18 (use while(true) for infinite loops)               # --> can't detect
    # 5-19 (avoid complex 'if' exprs)                         # --> could count &&/||
    # 5-20 (nominal in 'if', exception in 'else'              # --> can't detect
    testList.append(TestNoOneLinerIf(filetype))             # 5-21 (put conditional on separate line)
    testList.append(TestExecutibleConditional(filetype))    # 5-22 (no executibles in conditional)
    # 5-23 (explicitly state function return type)            # --> not sure how to detect
    testList.append(TestConstRefForNonPrimitives(filetype))  # 5-24 (pass non-primitives by const ref)
    # 5-25 (use 'const' for methods when possible)            # --> can't detect
    # 5-26 (provide const and non-const to ret *p/&x)         # --> don't know how to check1
    testList.append(TestOneArgConstructors(filetype))       # 5-27 (1-arg constructors must be 'explicit')
    testList.append(TestDestructorExceptions(filetype))     # 5-28 (no exceptions in desctructors)
    testList.append(TestVirtualDestructor(filetype))        # 5-29 (destructors should be virtual)
    # 5-30 (avoid magic numbers)                              # --> can't detect
    testList.append(TestShowOneDecimal(filetype))           # 5-31 (show 1 dec point for float/double)
    testList.append(TestShowDigitBefore(filetype))          # 5-32 (show digit before dec for float/double)
    testList.append(TestNoGoto(filetype))                   # 5-33 (no 'goto')
    # 5-34 (use '0' instead of NULL)                          # --> not strictly required
    # 5-35 (use 'int' for indices)                            # --> don't know how to detect
    # 5-36 (no exceptions in method signatures)               # --> I don't understand
    # 5-37 (minimize #define)                                 # --> too vague
    # 5-38 (do not comment out code)                          # --> difficult to detect
    testList.append(TestCharStar(filetype))                 # 5-39 (use std::string instead of char*)
    testList.append(TestCArray(filetype))                   # 5-40 (use std::vector<> instead of x[]
    testList.append(TestUsingOnlyStd(filetype))             # 5-41 ('using' only for std)
    # 5-42 (abbreviate namespaces with 'using')               # how to detect?

    # total 9
    testList.append(TestMultipleStatement(filetype))        # 6-1 (no multiple statements per line)
    testList.append(TestFourSpaceIndent(filetype))          # 6-2 (use 4-space indentation)
    # 6-3 (avoid deep nesting)                                # --> how deep?
    testList.append(TestKR(filetype))                       # 6-4 (use K&R block style)
    testList.append(TestClassBlocksLeft(filetype))          # 6-5 (public/protected/private left justified)
    # 6-6 (use standard func declaration form)                # --> no template to test failure
    # 6-7 (use standard conditional form)                     # --> no template to test failure
    # 6-8 (use standard for loop form)                        # --> no template to test failure
    testList.append(TestEmptyLoopOneLine(filetype))         # 6-9 (put empty loops on one line)
    # 6-10 (use standard while loop form)                     # --> no template to test failure
    # 6-11 (use standard do-while form)                       # --> no template to test failure
    # 6-12 (use standard switch form)                         # --> no template to test failure
    # 6-13 (use try/catch form)                               # --> no template to test failure
    testList.append(TestBracketsMissing(filetype))          # 6-14 (omit brackets only for one-liners)
    # 6-15 (return type on same line as func name)            # --> tricky to check
    testList.append(TestOperatorSpacing(filetype))          # 6-16 (use whitespace around operators)
    testList.append(TestCommaSpace(filetype))               # 6-16 (use space after comma)
    # 6-17 (missing??)                                        # NA
    # 6-18 (separate logic units by 1 blank line)             # --> can't detect
    # 6-19 (method sep lines = 1 (.h), 2 (.cc) )              # --> tricky to detect
    # 6-20 (align variables in declarations)                  # --> too vague
    # 6-21a (use alignment to enhance readability)            # --> too vague
    testList.append(TestNestedNamespacesLeft(filetype))     # 6-21b (left-align nested namespaces)
    # 6-22 (rewrite tricky code, don't over-comment)          # --> can't detect
    # 6-23 (all comments in English)                          # --> can't detect
    # 6-24 (don't mix block comments with code)               # --> tricky
    # 6-25 (align comment with block)                         # --> tricky

    return testList


#############################################################
#
# Main body of code
#
#############################################################
def main():

    ########################################################################
    # command line arguments and options
    ########################################################################
    parser = optparse.OptionParser(usage = __doc__)
    parser.add_option("-i", "--ignore", dest = "ignore", default = ".ignore-style",
                      help = "Provide a file containing a list of " +
                      "'filename rule line' to ignore (default = %default)")
    parser.add_option("-l", "--showline", dest = "showline", action = "store_true",
                      default = False, help = "Show the offending line (same as -w) (default = %default)")
    parser.add_option("-p", "--showstripped", dest = "showstripped", action = "store_true",
                      default = False, help = "Show the stripped offending line (default = %default)")
    parser.add_option("-w", "--showraw", dest = "showraw", action = "store_true",
                      default = False, help = "Show the raw offending line (default = %default)")
    parser.add_option("-s", "--severity", dest = "severity", type = int,
                      default = 5, help = "Minimum severity (highest numerical value) " +
                      "to display (default = %default)")
    opts, args = parser.parse_args()

    if opts.showline:
        opts.showraw = True

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    infile, = args
    m = re.search(".*\.(cc|c|h|py)", infile)
    if m:
        filetype = m.group(1)
    else:
        filetype = ""

    ##########################################################################
    # build the list of tests
    testList = initializeTestList(filetype, infile)

    ##########################################################################
    # load the file and create the line info structures
    fp = open(infile, 'r')
    lines = parseLines(fp.readlines(), filetype)
    fp.close()

    ##########################################################################
    # run each test and accumulate violations
    violationList = []
    for test in testList:
        violationList += test.apply(lines)

    ##########################################################################
    # load the .ignore file to deal with known (and accepted) violations
    ignore = {}
    if (os.path.exists(opts.ignore)):
        fp = open(opts.ignore, 'r')
        for line in fp:
            line = re.sub("#.*$", "", line)            # remove any '#' comments
            if (re.search("^\s*$", line)):
                continue    # skip blank lines

            igFile, igRule, igLine = line.split()
            if (ignore.has_key(igFile) and ignore[igFile].has_key[igRule]):
                ignore[igFile][igRule].append(igLine)
            elif (ignore.has_key(igFile) and not ignore[igFile].has_key[igRule]):
                ignore[igFile][igRule] = [igLine]
            else:
                ignore[igFile] = {igRule: [igLine]}
        fp.close()

    ##########################################################################
    # print the results, sorted by line number
    violationFinal = []
    violationSort = sorted(violationList, key = lambda x: x.getLineNumber())

    # skip the ones with a suppression line
    for violation in violationSort:
        parasoftSuppress = "LsstDm-" + violation.getId() in violation.line.suppress
        if not parasoftSuppress:
            violationFinal.append(violation)

    if violationFinal:
        print "// -*- parasoft -*-"
        print infile
    for violation in violationFinal:
        lineNumber = str(violation.getLineNumber())
        rule = violation.getId()
        doIgnore = (ignore.has_key(infile) and ignore[infile].has_key(rule) and
                    (lineNumber in ignore[infile][rule]))

        severity = violation.getSeverity()
        if (not doIgnore and (severity <= opts.severity)):
            print "%-4s \t%-60s \t%10s" % (lineNumber + ":", violation.getComment(),
                                           "LsstDm-" + rule + "-" + str(severity))
            if (opts.showraw):
                print lines[int(lineNumber) - 1].raw,
            if (opts.showstripped):
                print lines[int(lineNumber) - 1].stripped,


#############################################################
# end
#############################################################

if __name__ == '__main__':
    main()
