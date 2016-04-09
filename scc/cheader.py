#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2015 Stany MARCEL <stanypub@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import ast
import os
import shlex
from collections import OrderedDict
import operator as op

OPERATORS = {
    ast.Add    : op.add,
    ast.Sub    : op.sub,
    ast.Mult   : op.mul,
    ast.Div    : op.floordiv,
    ast.Mod    : op.mod,
    ast.LShift : op.lshift,
    ast.RShift : op.rshift,
    ast.BitOr  : op.or_,
    ast.BitXor : op.xor,
    ast.BitAnd : op.and_,
    ast.Invert : op.invert,
    ast.Not    : op.not_,
    ast.UAdd   : op.pos,
    ast.USub   : op.neg,
    ast.And    : op.and_,
    ast.Or     : op.or_,
    ast.Eq     : op.eq,
    ast.NotEq  : op.ne,
    ast.Lt     : op.lt,
    ast.LtE    : op.le,
    ast.Gt     : op.gt,
    ast.GtE    : op.ge,
}

def eval_expr(expr):

    """ Eval and expression inside a #define using a suppart of python grammar """

    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return OPERATORS[type(node.op)](_eval(node.operand))
        elif isinstance(node, ast.BoolOp):
            values = [_eval(x) for x in node.values]
            return OPERATORS[type(node.op)](**values)
        else:
            raise TypeError(node)

    return _eval(ast.parse(expr, mode='eval').body)


def defines(base, include):

    """ Extract #define from base/include following #includes """

    parsed = set()
    fname = os.path.normpath(os.path.abspath(os.path.join(base, include)))
    parsed.add(fname)

    lexer = shlex.shlex(open(fname), posix=True)

    lexer.whitespace = ' \t\r'
    lexer.commenters = ''
    lexer.quotes = '"'

    out = OrderedDict()

    def parse_c_comments(lexer, tok, ntok):
        if tok != '/' or ntok != '*':
            return False
        quotes = lexer.quotes
        lexer.quotes = ''
        while True:
            tok = lexer.get_token()
            ntok = lexer.get_token()
            if tok == '*' and ntok == '/':
                lexer.quotes = quotes
                break
            else:
                lexer.push_token(ntok)
        return True

    def parse_cpp_comments(lexer, tok, ntok):
        if tok != '/' or ntok != '/':
            return False
        quotes = lexer.quotes
        lexer.quotes = ''
        while True:
            tok = lexer.get_token()
            if tok == '\n':
                lexer.quotes = quotes
                lexer.push_token(tok)
                break
        return True

    while True:
        tok = lexer.get_token()
        if not tok or tok == '':
            break
        ntok = lexer.get_token()

        if parse_c_comments(lexer, tok, ntok):
            continue
        if parse_cpp_comments(lexer, tok, ntok):
            continue

        if tok != '\n' or ntok != '#':
            lexer.push_token(ntok)
            continue

        tok = lexer.get_token()
        if tok == 'define':
            name = lexer.get_token()
            expr = ''
            while True:

                tok = lexer.get_token()
                ntok = lexer.get_token()

                if parse_c_comments(lexer, tok, ntok):
                    continue
                if parse_cpp_comments(lexer, tok, ntok):
                    continue
                lexer.push_token(ntok)

                if not tok or tok == '':
                    break
                if tok == '\n':
                    lexer.push_token(tok)
                    break

                if tok in out:
                    tok = str(out[tok])
                expr = expr + tok

            try:
                val = eval_expr(expr)
                out[name] = val
            except (SyntaxError, TypeError):
                pass
        elif tok == 'include':

            tok = lexer.get_token()
            if tok == '<':
                name = ''
                while True:
                    tok = lexer.get_token()
                    if tok == '>':
                        break
                    name = name + tok
            else:
                name = tok
            fname = os.path.normpath(os.path.abspath(os.path.join(base, name)))
            if os.path.isfile(fname) and not fname in parsed:
                parsed.add(fname)
                lexer.push_source(open(fname))
        else:
            lexer.push_token(tok)


    return out


if __name__ == '__main__':
    import sys
    definesDict = defines(sys.argv[1], sys.argv[2])
    for k, v in definesDict.items():
        print("{}:\t{}".format(k, v))
