#!/usr/bin/env python3

'''
   Utilities for Disks
'''

from ..base import octetview as ov

class Sector(ov.Octets):
    ''' A sector '''
    def __init__(self,
        tree,
        cyl=None,
        head=None,
        sect=None,
        lo=None,
        unread_note=None,
        **kwargs,
    ):
        if lo is None:
            lo = tree.seclo[(cyl, head, sect)]
        else:
            cyl, head, sect = tree.losec[lo]
        super().__init__(
            tree,
            lo,
            width=tree.width[(cyl, head, sect)],
            **kwargs,
        )
        self.cyl = cyl
        self.head = head
        self.sect = sect
        self.is_unread = self.this[self.lo:self.hi] == tree.unread_pattern
        if self.is_unread and unread_note:
            self.tree.this.add_note(unread_note)
        self.terse = False

    def picture(self, what):
        self.tree.picture[(self.cyl, self.head, self.sect)] = what

    def render(self):
        ''' Render respecting byte ordering '''
        if self.terse:
            yield self.ident
            return
        if self.is_unread:
            octets = self.octets()
        else:
            octets = self.iter_bytes()
        yield self.ident + " ┆" + self.this.type_case.decode(octets) + "┆"

    ident = "Sector"

class DataSector(Sector):
    ''' A data sector '''
    def __init__(self, tree, *args, namespace=None, **kwargs):
        super().__init__(
            tree,
            *args,
            unread_note="UNREAD_DATA_SECTOR",
            **kwargs
        )
        if namespace:
            self.ident = "DataSector[»" + namespace.ns_name + "«]"
        self.picture('·')
    ident = "DataSector"

    def render(self):
        yield self.ident

class UnusedSector(Sector):
    ''' An unused sector '''
    def __init__(self, tree, *args, **kwargs):
        super().__init__(
            tree,
            *args,
            unread_note="UNREAD_UNUSED_SECT",
            **kwargs
        )
        i = set(self.tree.this[self.lo:self.hi])
        if len(i) == 1:
            self.fill = " 0x%02x[%d]" % (self.tree.this[self.lo], self.hi - self.lo)
        else:
            self.fill = None

    ident = "UnusedSector"

    def render(self):
        if self.fill is not None:
            yield self.ident + self.fill
        else:
            yield from super().render()

class Disk(ov.OctetView):
    ''' ... '''

    SECTOR_OFFSET = 1

    def __init__(self, this, geometry, physsect=None, unread_pattern=None):
        self.geometry = geometry	# [ [C, H, S, B], ...]
        self.seclo = {}
        self.losec = {}
        self.width = {}
        self.picture = {}
        self.picture_legend = {
            "·": "Data",
            "?": "Unclaimed",
        }
        lo = 0
        for cyl, head, sec, nbyte in self.iter_chsb():
            chs = (cyl, head, sec)
            self.seclo[chs] = lo
            self.width[chs] = nbyte
            self.picture[chs] = "?"
            self.losec[lo] = chs
            lo += nbyte
        if physsect is None:
            physsect = 128
        self.physsect = physsect
        if unread_pattern is None:
            unread_pattern = b'_UNREAD_' * (physsect // 8)
        self.unread_pattern = unread_pattern
        super().__init__(this, default_width=physsect)

    def iter_chsb(self):
        ''' Iterate all CHSB '''
        for ncyl, nhd, nsec, nbyte in self.geometry:
            for cyl in range(ncyl):
                for head in range(nhd):
                    for sec in range(self.SECTOR_OFFSET, nsec + self.SECTOR_OFFSET):
                        yield cyl,head,sec,nbyte

    def prefix(self, lo, hi):
        ''' Line prefix is hex off set + CHS '''
        i = super().prefix(lo, hi)
        j = self.losec.get(lo)
        if j:
            j = " %d,%d,%d" % j
            return i + j.ljust(9)
        return i + " " * 9

    def fill_gaps(self, cls=UnusedSector):
        ''' Fill the gaps with UnusedSector '''
        for lo, hi in list(self.gaps()):
            for i, adr in self.losec.items():
                j = i + self.width[adr]
                if i >= lo and j <= hi:
                    cls(self, lo=i, hi=j).insert()

    def set_picture(self, what, cyl=None, head=None, sect=None, lo=None):
        if lo is not None:
            cyl, head, sect = self.losec[lo]
        self.picture[(cyl, head, sect)] = what

    def disk_picture(self, file, _this):
        ''' Draw a UTF-8-art picture of the disk '''
        file.write("<H3>Disk picture</H3>\n")
        file.write("<pre>\n")
        ncyl = max(chsb[0] for chsb in self.iter_chsb()) + 1
        file.write("   c ")
        for i in range(0, ncyl, 10):
            file.write(("%d" % (i//10)).ljust(10))
        file.write("\n     ")
        for i in range(ncyl):
            file.write("%d" % (i % 10))
        file.write('\nh, s┌' + '─' * ncyl)
        lhead = 0
        lsec = None
        for head, sec, cyl in sorted(
            (chsb[1],chsb[2],chsb[0]) for chsb in self.iter_chsb()
        ):
            if head != lhead or sec != lsec:
                if head != lhead:
                    file.write("\n")
                    lhead = head
                    lsec = None
                if sec != lsec:
                    file.write("\n%d,%2d│" % (head, sec))
                    lsec = sec

            file.write(self.picture[(cyl, head, sec)])

        got = set(self.picture.values())

        file.write("\n\nLegend:\n")
        for i, j in sorted(self.picture_legend.items()):
            if i in got:
                file.write('    ' + i + '  ' + j + '\n')
        file.write("\n<pre>\n")
