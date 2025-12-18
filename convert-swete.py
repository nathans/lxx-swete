#! /usr/bin/env python3
# -*- coding: utf-8 -*
#
# Convert OGL Swete TEI files to one token per line, with verses.
#
# Copyright 2025 Nathan D. Smith <nathan@smithfam.info>
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import koinenlp
import re
import unicodedata
import xml.sax

FILTER_CHARS = ["¶", "[", "]", "§"]
OUTLINE = "{0}.{1}.{2} {3}\n"
DEST = "data/{0:02d}.{1}.txt"
TITLES = {
    "01": "Genesis",
    "02": "Exodus",
    "03": "Leviticus",
    "04": "Numeri",
    "05": "Deuteronomium",
    "06": "Josue",
    "08": "Judices",
    "10": "Ruth",
    "11": "Regnorum_I",
    "12": "Regnorum_II",
    "13": "Regnorum_III",
    "14": "Regnorum_IV",
    "15": "Paralipomenon_I",
    "16": "Paralipomenon_II",
    "17": "Esdras_A",
    "18": "Esdras_B",
    "19": "Esther",
    "20": "Judith",
    "21": "Tobias",
    "23": "Machabaeorum_i",
    "24": "Machabaeorum_ii",
    "25": "Machabaeorum_iii",
    "26": "Machabaeorum_iv",
    "27": "Psalmi",
    "28": "Odae",
    "29": "Proverbia",
    "31": "Canticum",
    "32": "Job",
    "33": "Sapientia_Salomonis",
    "34": "Ecclesiasticus",
    "35": "Psalmi_Salomonis",
    "36": "Osee",
    "37": "Amos",
    "38": "Michaeas",
    "39": "Joel",
    "40": "Abdias",
    "41": "Jonas",
    "42": "Nahum",
    "43": "Habacuc",
    "44": "Sophonias",
    "45": "Aggaeus",
    "46": "Zacharias",
    "47": "Malachias",
    "48": "Isaias",
    "49": "Jeremias",
    "50": "Baruch",
    "51": "Threni_seu_Lamentationes",
    "52": "Epistula_Jeremiae",
    "53": "Ezechiel",
    "54": "Susanna_translatio_Graeca",
    "55": "Susanna_Theodotionis_versio",
    "56": "Daniel_translatio_Graeca",
    "57": "Daniel_Theodotionis_versio",
    "58": "Bel_et_Draco_translatio_Graeca",
    "59": "Bel_et_Draco_Theodotionis_versio"
}

def get_filename(number):
    "Return a nice filename from the given book ID"

    title = TITLES["{0:02d}".format(number)]
    return DEST.format(number, title.strip())


class SweteLXX(xml.sax.handler.ContentHandler):
    "Parser for Swete LXX XML"

    def __init__(self, task, outfile):
        "Initialize varibales"

        self.out_lines = []

        self.in_book = False
        self.in_header = False
        self.in_idno = False
        self.in_note = False
        self.in_title = False
        self.in_titlestmt = False
        self.note_depth = 0

        self.task = task
        self.outfile = outfile

        self.lb_token = None
        self.current_chapter = 0
        self.current_verse = 0
        self.current_book = 0
        self.book_title = None

    def unicode_normalize(self, text):
        """Return the given text normalized to Unicode NFC."""

        normalized_text = unicodedata.normalize('NFC', text)
        return normalized_text

    def startElement(self, name, attrs):
        "Actions for encountering open tags"

        if (name == "div" and "subtype" in attrs.getNames()
            and attrs.getValue("subtype") == "chapter"):
            self.current_chapter = attrs.getValue("n")

        elif (name == "div" and "subtype" in attrs.getNames()
            and attrs.getValue("subtype") == "verse"):
            self.current_verse = attrs.getValue("n")

        elif name == "text":
            self.in_book = True
            
        elif name == "head":
            self.in_header = True

        elif name == "idno":
            self.in_idno = True

        elif name == "titleStmt":
            self.in_titlestmt = True

        elif name == "title":
            self.in_title = True

        elif name == "note":
            self.note_depth += 1
            self.in_note = True

    def characters(self, data):
        "Handle text"

        # Obtain the numerical book ID.
        # TODO This is done based on the position within the filename
        # Probably fragile, this should be done more programmatically
        if self.in_idno:
            self.current_book = int(data[11:14])

        # Obtain the book name
        if self.in_titlestmt and self.in_title:
            self.book_title = data

        # If in the book not in a header, and not in a note
        if self.in_book and not self.in_note and not self.in_header:
            tokens = data.split()
            for token in tokens:

                # If the given token ends with a hyphen, assume a
                # token split by a linebreak.  Store it in
                # self.lb_token and continue to the next iteration
                if token[-1] == "-":
                    self.lb_token = token[:-1]
                    continue

                # If there is a lb_token (from a line-break) waiting,
                # prepend it to the current token before processing
                if self.lb_token:
                    token = self.lb_token + token
                    self.lb_token = None

                # Filter metacharacters
                for char in FILTER_CHARS:
                    token = token.replace(char, "")
                if len(token) < 1:
                    continue

                # shim for GREEK ANO TELEIA
                token = token.replace("·", "·")

                # Handle punctuation
                punct_token = None
                if koinenlp.remove_punctuation(token) == token[:-1]:
                    punct_token = token[-1]
                    end_token = token[:-1]
                else:
                    end_token = token

                # Output only the normalized form
                if self.task == "compare":
                    self.out_lines.append(self.unicode_normalize(end_token))
                    if punct_token:
                        self.out_lines.append(punct_token)
                elif self.task == "convert":
                    out_line = OUTLINE.format(self.current_book,
                                              self.current_chapter,
                                              self.current_verse,
                                              self.unicode_normalize(token))
                    self.out_lines.append(out_line)

    def endElement(self, name):
        "Actions for encountering closed tags"

        if name == "text":
            self.in_book = False
            
        elif name == "head":
            self.in_header = False

        elif name == "idno":
            self.in_idno = False

        elif name == "titleStmt":
            self.in_titlestmt = False

        elif name == "title":
            self.in_title = False

        elif name == "note":
            self.note_depth -= 1
            if self.note_depth < 1:
                self.in_note = False

    def endDocument(self):
        "Finish up"

        # Write output to file
        if self.outfile:
            dest = get_filename(self.current_book)
            f = open(dest, 'w')
            f.writelines(self.out_lines)
            f.close()
        else:
            for out_line in self.out_lines:
                print(out_line)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description='Convert Swete TEI to one line per token..')
    subs = argparser.add_subparsers(dest='command')
    argparser_diff = subs.add_parser("compare",
                                     help="Print normalized comparison text")
    argparser_convert = subs.add_parser("convert", help="Print converted text")
    argparser.add_argument('--file', metavar='<file.xml>', type=str,
                           help='Volume to process.')
    argparser.add_argument('--outfile', action='store_true',
                           help='Output to file.')

    args = argparser.parse_args()
    vol = open(args.file, 'r')
    parser = xml.sax.make_parser()
    parser.setContentHandler(SweteLXX(task=args.command, outfile=args.outfile))
    parser.parse(vol)
