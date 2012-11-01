# -*- coding: utf8 -*-
__all__ = ('ClassFile', 'ClassVersion')
from struct import pack, unpack
from collections import namedtuple


from jawa.cp import ConstantPool
from jawa.fields import FieldTable
from jawa.methods import MethodTable
from jawa.attribute import AttributeTable
from jawa.util.flags import Flags


# The format and size-on-disk of each type of constant
# in the constant pool.
_constant_fmts = (
    None, None, None,
    ('>i', 4),
    ('>f', 4),
    ('>q', 8),
    ('>d', 8),
    ('>H', 2),
    ('>H', 2),
    ('>HH', 4),
    ('>HH', 4),
    ('>HH', 4),
    ('>HH', 4)
)


class ClassVersion(namedtuple('ClassVersion', ['major', 'minor'])):
    __slots__ = ()

    @property
    def human(self):
        return {
            0x33: 'J2SE_7',
            0x32: 'J2SE_6',
            0x31: 'J2SE_5',
            0x30: 'JDK1_4',
            0x2F: 'JDK1_3',
            0x2E: 'JDK1_2',
            0x2D: 'JDK1_1',
        }.get(self.major, None)


class ClassFile(object):
    # The JVM .class magic number.
    MAGIC = 0xCAFEBABE

    def __init__(self, fio=None):
        # Default to J2SE_7
        self._version = ClassVersion(0x33, 0)
        self._constants = ConstantPool()
        self._access_flags = Flags('>H', {
            'acc_public': 0x0001,
            'acc_final': 0x0010,
            'acc_super': 0x0020,
            'acc_interface': 0x0200,
            'acc_abstract': 0x0400,
            'acc_synthetic': 0x1000,
            'acc_annotation': 0x2000,
            'acc_enum': 0x4000
        })
        self._this = 0
        self._super = 0
        self._interfaces = []
        self._fields = FieldTable(self)
        self._methods = MethodTable(self)
        self._attributes = AttributeTable(self)

        if fio:
            self._from_io(fio)

    def save(self, fout):
        """
        Saves the `ClassFile` to the file-like object `fout`.
        """
        write = fout.write

        write(pack('>IHHH',
            ClassFile.MAGIC,
            self.version.minor,
            self.version.major,
            self.constants.raw_count
        ))

        for constant in self.constants._pool:
            if constant is None:
                continue

            tag = constant[0]
            write(pack('>B', tag))

            if tag == 1:
                length = len(constant[1])
                write(pack('>H', length))
                write(constant[1])
            else:
                fmt, _ = _constant_fmts[tag]
                write(pack(fmt, *constant[1:]))

        write(self.access_flags.pack())
        write(pack('>HHH{0}H'.format(len(self._interfaces)),
            self._this,
            self._super,
            len(self._interfaces),
            *self._interfaces
        ))

        self._fields._to_io(fout)
        self._methods._to_io(fout)
        self._attributes._to_io(fout)

    # ------------
    # Internal
    # ------------

    def _from_io(self, fio):
        """
        Loads an existing JVM ClassFile from any file-like object.
        """
        if unpack('>I', fio.read(4))[0] != ClassFile.MAGIC:
            raise ValueError('invalid magic number')

        # The version is swapped on disk to (minor, major), so swap it back.
        self.version = unpack('>HH', fio.read(4))[::-1]

        # Reads in the ConstantPool (constant_pool in the JVM Spec)
        constant_pool_count = unpack('>H', fio.read(2))[0]

        # Pull this locally so CPython doesn't do a lookup each time.
        pool = self._constants
        read = fio.read

        while constant_pool_count > 1:
            constant_pool_count -= 1
            # The 1-byte prefix identifies the type of constant.
            tag = unpack('>B', read(1))[0]

            if tag == 1:
                # CONSTANT_Utf8_info, a length prefixed UTF-8-ish string.
                length = unpack('>H', read(2))[0]
                pool.append((tag, read(length)))
            else:
                # Every other constant type is trivial.
                fmt, size = _constant_fmts[tag]
                pool.append((tag,) + unpack(fmt, read(size)))
                if tag in (5, 6):
                    # LONG (5) and DOUBLE (6) count as two entries in the
                    # pool.
                    pool.append(None)
                    constant_pool_count -= 1

        # ClassFile access_flags, see section #4.1 of the JVM specs.
        self.access_flags.unpack(read(2))

        # The CONSTANT_Class indexes for "this" class and its superclass.
        # Interfaces are a simple list of CONSTANT_Class indexes.
        self._this, self._super, interfaces_count = unpack('>HHH', read(6))
        self._interfaces = unpack(
            '>{0}H'.format(interfaces_count),
            read(2 * interfaces_count)
        )

        self._fields._from_io(fio)
        self._methods._from_io(fio)
        self._attributes._from_io(fio)

    # -------------
    # Properties
    # -------------

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, (major, minor)):
        self._version = ClassVersion(major, minor)

    @property
    def constants(self):
        """
        The :class:~jawa.cp.ConstantPool for this `ClassFile`.
        """
        return self._constants

    @property
    def access_flags(self):
        return self._access_flags

    @property
    def this(self):
        return self.constants.get(self._this)

    @property
    def super_(self):
        return self.constants.get(self._super)

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def fields(self):
        return self._fields

    @property
    def methods(self):
        return self._method

    @property
    def attributes(self):
        return self._attributes
