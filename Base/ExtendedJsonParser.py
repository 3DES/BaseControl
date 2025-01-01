#!/usr/bin/env python3
from ply import lex
import ply.yacc as yacc
import re
import copy
import json

class ExtendedJsonParser(object):
    HIDE_STRING = "##########"
    LEXER_STAGE = "SCANNER"
    PARSER_STAGE = "PARSER"
    protectRegex = None      # values their keys matching this regex or values that match it will be replaced by HIDE_STRING

    def errorHandler(self, lexer : lex, stage : str = None):
        currentLine = lexer.lexer.lexdata[self._lastLineEnd:].split("\n")[0]

        if self.fileName:
            errorPosition = f"{self.fileName}:{lexer.lineno}"
        else:
            errorPosition = f"{lexer.lineno}"

        if stage is None:
            stage = "Syntax"
            token = ""
        elif stage == self.PARSER_STAGE:
            token = f", token \"{lexer.type}\", character \"{lexer.value[0]}\""
        else:
            token = f", character \"{lexer.value[0]}\""

        # throw exception, further scanning/parsing usually doesn't make sense!
        raise Exception(f"{stage} error at {errorPosition}, character position {lexer.lexpos - self._lastLineEnd}{token}\n" +
                               f"{currentLine}\n" +
                               f"{' ' * (lexer.lexpos - self._lastLineEnd) + '^'}")


    tokens = (
        'OBJECT_BEGIN',
        'OBJECT_END',
        'LIST_BEGIN',
        'LIST_END',
        'COMMA',
        'COLON',

        'NULL',
        'TRUE',
        'FALSE',
        'FLOAT',
        'INTEGER',
        'STRING',
    )

    t_ignore = ' \t'

    def t_OBJECT_BEGIN(self, t):
        r'\{'
        return t

    def t_OBJECT_END(self, t):
        r'\}'
        return t

    def t_LIST_BEGIN(self, t):
        r'\['
        return t

    def t_LIST_END(self, t):
        r'\]'
        return t

    def t_COMMA(self, t):
        r','
        return t

    def t_COLON(self, t):
        r':'
        return t

    def t_FLOAT(self, t):
        # [0-9]+\.[0-9]+
        # [0-9]+\.
        # \.[0-9]+
        #
        # [0-9]+\.[0-9]+([eE][+-]?[0-9]+)
        # [0-9]+\.([eE][+-]?[0-9]+)
        # \.[0-9]+([eE][+-]?[0-9]+)
        #
        # [0-9]+([eE][+-]?[0-9]+)
        r'-?(([0-9]+\.[0-9]+|[0-9]+\.|\.[0-9]+)([eE][+-]?[0-9]+)?)|([0-9]+([eE][+-]?[0-9]+))'
        return t

    def t_INTEGER(self, t):
        r'-?[0-9]+'
        return t

    def t_STRING(self, t):
        r'"((?:\\"|[^"])*)"'
        t.value = t.value[1:-1].encode().decode('unicode_escape')       # remove leading and trailing quotation marks, un-escape escaped characters
        return t

    def t_NULL(self, t):
        r'(null|Null|none|None)'
        return t

    def t_TRUE(self, t):
        r'(true|True)'
        return t

    def t_FALSE(self, t):
        r'(false|False)'
        return t

    def t_newline(self, t):
        r'(\#.*)?\n'         # line end characters inclusive optionally leading comment
        t.lexer.lineno += 1
        self._lastLineEnd = t.lexpos + len(t.value)

    def t_error(self, t):
        self.errorHandler(t, stage = self.LEXER_STAGE)
        t.lexer.skip( 1 )



    #precedence = (
    #    ( 'left', 'COMMA' ),
    #    ( 'left', 'TIMES', 'DIV' ),
    #    ( 'nonassoc', 'UMINUS' )
    #)


    def dictMerge(self, targetDict : dict, sourceDict : dict):
        '''
        Merges two dicts by adding elements from one into the other.
        If elements in source and in target dict are also dicts it will recursively merge them.
        If one or both elements aren't dicts the element in the target dict will be replaced by the one in the source dict, this means that e.g. lists will be replaced and list elements from target list will get lost.
        '''
        for sourceElement in sourceDict:
            if self.combineDicts and sourceElement in targetDict and (type(targetDict[sourceElement]) is dict) and (type(sourceDict[sourceElement]) is dict):
                self.dictMerge(targetDict[sourceElement], sourceDict[sourceElement])
            else:
                targetDict[sourceElement] = sourceDict[sourceElement]


    #    object : OBJECT_BEGIN OBJECT_END
    #           | OBJECT_BEGIN tuples OBJECT_END

    def p_object_empty(self, p):
        '''
        object : OBJECT_BEGIN OBJECT_END
        '''
        p[0] = {}

    def p_object(self, p):
        '''
        object : OBJECT_BEGIN tuples OBJECT_END
        '''
        p[0] = p[2]

    #    tuples : tuple COMMA tuples
    #           | tuple COMMA
    #           | tuple

    def p_tuples_tuple_comma_tuples(self, p):
        '''
        tuples : tuple COMMA tuples
        '''
        p[0] = p[1]
        self.dictMerge(p[0], p[3])   # p[3] must be the second parameter here, otherwise the file is handled inverse

    def p_tuples_tuple_comma_or_tuple(self, p):
        '''
        tuples : tuple COMMA
               | tuple
        '''
        p[0] = p[1]

    def p_tuple(self, p) :
        '''
        tuple : STRING COLON element
        '''
        if self.protectRegex is not None:
            if self.protectRegex.match(p[1]):
                # independent what type the right side is, replace it by self.HIDE_STRING
                p[3] = self.HIDE_STRING
            elif type(p[3]) is str:
                if self.protectRegex.match(p[3]):
                    p[3] = self.HIDE_STRING
        p[0] = { p[1] : p[3] }

    def p_list(self, p) :
        '''
        list : LIST_BEGIN commalist LIST_END
        '''
        p[0] = p[2]

    #    commalist : element COMMA commalist
    #              | element COMMA
    #              | element

    def p_commalist_element_comma_commalist(self, p) :
        '''
        commalist : element COMMA commalist
        '''
        if (self.protectRegex is not None) and (type(p[1]) is str):
            if self.protectRegex.match(p[1]):
                p[1] = self.HIDE_STRING
        p[0] = p[3]
        p[0].insert(0, p[1])

    def p_commalist_element_comma_or_element(self, p) :
        '''
        commalist : element COMMA
                  | element
        '''
        if (self.protectRegex is not None) and (type(p[1]) is str):
            if self.protectRegex.match(p[1]):
                p[1] = self.HIDE_STRING
        p[0] = [ p[1] ]

    #    element : object
    #            | list
    #            | NULL
    #            | TRUE
    #            | FALSE
    #            | FLOAT
    #            | INTEGER
    #            | STRING
    #

    def p_element_object_or_list(self, p) :
        '''
        element : object
                | list
        '''
        p[0] = p[1]

    def p_element_NULL(self, p) :
        '''
        element : NULL
        '''
        p[0] = None

    def p_element_TRUE(self, p) :
        '''
        element : TRUE
        '''
        p[0] = True

    def p_element_FALSE(self, p) :
        '''
        element : FALSE
        '''
        p[0] = False

    def p_element_FLOAT(self, p) :
        '''
        element : FLOAT
        '''
        p[0] = float(p[1])

    def p_element_INTEGER(self, p) :
        '''
        element : INTEGER
        '''
        p[0] = int(p[1])

    def p_element_STRING(self, p) :
        '''
        element : STRING
        '''
        p[0] = p[1]

    def p_error(self, p):
        self.errorHandler(p, stage = self.PARSER_STAGE)

    def __init__(self):
        self.lexer  = lex.lex(module = self)
        self.parser = yacc.yacc(module = self)
        self.fileName = ""

    def _readExtendedJsonFile(self, fileName):
        with open(fileName) as file:
            fileContent = file.readlines()
        return fileContent

    def parse(self, extendedJsonString : str, combineDicts : bool = True, protectRegex : str = None) -> dict:
        self.combineDicts = combineDicts
        self.protectRegex = re.compile("{0}".format(protectRegex))
        return copy.deepcopy(self.parser.parse(extendedJsonString, lexer = self.lexer, tracking = True))

    def parseFile(self, fileName : str, combineDicts : bool = True, protectRegex : str = None) -> dict:
        self.fileName = fileName
        fileContent = self._readExtendedJsonFile(fileName)
        return self.parse("\n".join(fileContent), combineDicts = combineDicts, protectRegex = protectRegex)


if __name__ == '__main__':
    #res = parser.parse("\n".join(lines)) # the input
    stuff = '''
    {
        "a" : {
            "b" : "c",        # first attribute
            "k" : ["m"]       # first attribute
        },
        "a" : {
            "k" : ["l"]       # second attribute
            , "b":true,
        },
        "d" : {
            "e" : -42,          # hello again "whats going on here?"
            "3" : [ "g", "h" , { "i" : "j" } ],  # foo
            "4" : False,
            "5" : false,
            "P" : "C:\\Program Files (x86)\\AVRDUDESS\\avrDude.exe",
        },
    }
    '''
    stuff = '{"name": "Debugger Interface", "command_topic": "AccuControl/Debugger/in", "command_template": "{ \"variable\" : \"{{ value }}\" }"}'
    stuff = '{"command_template": "{ \"variable\" : \"{{ value }}\" }"}'
    stuff = '{"X": "{ A : \"B\" }"}'
    stuff = json.dumps({"X" : "{ \"A\" : \"B\" }"}, indent = 4)
    stuff = '{\\"schaltschwelleAkkuSchlechtesWetter\\": 75 }'
    print(f"stuff is {stuff}")
    parser = ExtendedJsonParser()

    try:
        print(parser.parse(stuff)) # the input
    except Exception as exception:
        print(str(exception))

    try:
        print(parser.parseFile("init.json")) # the input
    except Exception as exception:
        print(str(exception))

