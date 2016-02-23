#!/usr/bin/env python
# encoding: utf-8
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from jawa import ClassFile
from jawa.attributes.source_file import SourceFileAttribute


def test_sourcefile_read():
    """
    Ensure we can read a SourceFileAttribute generated by javac.
    """
    sample_path = os.path.join(
        os.path.dirname(__file__),
        'data',
        'HelloWorldDebug.class'
    )

    with open(sample_path, 'rb') as fin:
        cf = ClassFile(fin)

        source_file = cf.attributes.find_one(name='SourceFile')

        assert(source_file.sourcefile.value == 'HelloWorldDebug.java')


def test_sourcefile_write():
    """
    Ensure SourceFileAttribute can be written and read back.
    """
    cf_one = ClassFile.create('SourceFileTest')

    cf_one.attributes.create(
        SourceFileAttribute,
        sourcefile=cf_one.constants.create_utf8('SourceFileTest.java')
    )

    fout = StringIO()
    cf_one.save(fout)

    fin = StringIO(fout.getvalue())
    cf_two = ClassFile(fin)

    source_file = cf_two.attributes.find_one(name='SourceFile')
    assert(source_file.sourcefile.value == 'SourceFileTest.java')
