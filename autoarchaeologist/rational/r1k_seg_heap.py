'''
   R1000 Segmented Heaps
   =====================

'''

import time
import os
import html

import autoarchaeologist.rational.r1k_linkpack as LinkPack
import autoarchaeologist.rational.r1k_bittools as bittools
import autoarchaeologist.rational.r1k_97seg as seg97

class TreeNode():
    ''' A binary tree of bits (literally) and pieces of an artifact '''

    def __init__(self, shift):
        self.shift = shift
        self.branches = [None] * 16

    def __iter__(self):
        for i in self.branches:
            if i is None:
                pass
            elif isinstance(i, TreeNode):
                yield from i
            else:
                yield i

    def insert(self, value, payload):
        ''' Recursively insert new foilage '''
        i = (value >> self.shift) & 0xf
        j = self.branches[i]
        if j is None:
            self.branches[i] = (value, payload)
        elif isinstance(j, TreeNode):
            j.insert(value, payload)
        else:
            self.branches[i] = TreeNode(self.shift - 4)
            self.branches[i].insert(*j)
            self.branches[i].insert(value, payload)

    def delete(self, value, payload):
        ''' Remove foilage, but do not prune '''
        i = (value >> self.shift) & 0xf
        j = self.branches[i]
        assert j is not None
        if isinstance(j, TreeNode):
            j.delete(value, payload)
        else:
            assert j[0] == value
            assert j[1] == payload
            self.branches[i] = None

    def last(self):
        ''' Return the last leaf in this branch '''
        for j in reversed(self.branches):
            if j is None:
                pass
            elif isinstance(j, TreeNode):
                rva, rvv = j.last()
                if rva is not None:
                    return rva, rvv
            else:
                return j
        return None, None

    def find(self, value):
        ''' Find the leaf containing value '''
        i = (value >> self.shift) & 0xf
        j = self.branches[i]
        if j is None:
            pass
        elif isinstance(j, TreeNode):
            rva, rvv = j.find(value)
            if rva is not None:
                return rva, rvv
        elif j[0] <= value:
            return j
        i -= 1
        while i >= 0:
            j = self.branches[i]
            if j is None:
                pass
            elif isinstance(j, TreeNode):
                rva, rvv = j.last()
                if rva is not None:
                    return rva, rvv
            elif j[0] <= value:
                return j
            i -= 1
        return None, None

class HeapHead(bittools.R1kSegBase):
    ''' Head of all non code-segments '''
    def __init__(self, seg, chunk, **kwargs):
        super().__init__(seg, chunk, title="SegHeapHead", **kwargs)
        self.compact = True
        self.get_fields(
            ("first_free_bit", 32),
            ("max_bits", 32),
            ("zero", 32),
            ("alloced_bits", 32),
        )

class R1kSegHeap():

    ''' A '97' segment from the backup tape '''

    def __init__(self, this):
        if len(this) > (1<<20):
            return
        if not this.has_note("R1k_Segment"):
            return
        for i in (
            "74_tag",        # CODE
            "75_tag",        # CODE
            "81_tag",        # 12MB, some strings incl TRIG_LIB
            "83_tag",        # 2.7MB, no strings
            "84_tag",        # 300KB, no strings
            "e3_tag",        # sources
            "R1k6ZERO",      # texts
        ):
            if this.has_note(i):
                return
        t0 = time.time()

        bits = bin(int.from_bytes(b'\xff' + this[:16].tobytes(), 'big'))[10:]

        x = int(bits[:32], 2)
        y = int(bits[32:64], 2)
        if int(bits[64:96], 2):
            return
        z = int(bits[96:128], 2)

        if x > z:
            return
        if y & 0xfff != 0xfff:
            return
        if z & 0xfff != 0xfff:
            return

        i = z
        j = 0
        while i > 15:
            i >>= 4
            j += 4
        self.tree = TreeNode(j)

        self.this = this
        self.end = x + 0x7f
        self.type_case = this.type_case
        self.fdot = None
        print("?R1SH", this)

        chunk = bittools.R1kSegChunk(
            0,
            bin(int.from_bytes(b'\xff' + this.tobytes(), 'big'))[10:10+self.end]
        )
        assert len(chunk) > 0
        self.tree.insert(0, chunk)


        self.starts = {}
        self.starts[0] = chunk

        self.tfn = this.filename_for(suf=".segheap")
        self.tfile = open(self.tfn.filename, "w")

        self.head = HeapHead(self, self.cut(0x0, 0x80))

        try:
            self.ponder()
        except Exception as err:
            print("PONDERING FAILED", this, err)
            raise

	# Render to a temporary file while parsing, so we can delete
	# all the bitmaps, otherwise the memory footprint roughly
	# doubles.

        self.render_chunks(self.tfile)
        self.tfile.close()

        this.add_interpretation(self, self.render_real)

        del self.starts
        del self.tree
        dt = time.time() - t0
        if dt > 20:
            print(this, "SH Pondering took %.1f" % dt)

    def __getitem__(self, idx):
        return self.starts[idx]

    def get(self, idx):
        ''' Look for chunk at specific address '''
        return self.starts.get(idx)

    def ponder(self):
        ''' Ponder the contents of this segment '''
        if self.this[0x10:0x24].tobytes() == b'This is a Link Pack.':
            try:
                LinkPack.R1kSegLinkPack(self, self.mkcut(0x80))
            except bittools.MisFit as err:
                print("FAIL LINKPACK", self.this, err)
                raise
            return # no hunting, dissector is fairly competent.

        if self.this.has_note('97_tag'):
            try:
                seg97.R1kSeg97(self)
            except bittools.MisFit as err:
                print("FAIL SEG97", self.this, err)

        # Make copy of chunks list, because it will be modified along the way
        for chunk in list(y for _x, y in self.tree):
            if not chunk.owner:
                bittools.hunt_array_strings(self, chunk)

        if len(self.this) > 100000:
            return
        # Make copy of chunks list, because it will be modified along the way
        for chunk in list(y for _x, y in self.tree):
            if not chunk.owner:
                bittools.hunt_strings(self, chunk)

    def hunt_orphans(self):
        ''' Hut for 32 bit pointers to start of existing chunks '''
        for _i, chunk in self.tree:
            if chunk.begin < 0x1000: # Too many false positives with small numbers
                continue
            cuts = self.hunt(bin((1<<32) + chunk.begin)[3:])
            for chunk2, offset, address in cuts:
                if chunk2.owner is not None:
                    continue
                print(chunk, "    pointer at 0x%x in " % offset, chunk2)
                if chunk.owner:
                    print("OWNED", chunk, self.this)
                    bittools.BitPointer(self, address, ident="orphan " + chunk.owner.title)
                else:
                    bittools.BitPointer(self, address, ident="orphan")
                    print("WHITE SPACE", chunk, self.this)

    def hunt(self, pattern):
        ''' hunt for particular pattern '''
        cuts = []
        for _i, chunk in self.tree:
            offset = 0
            while True:
                j = chunk.bits[offset:].find(pattern)
                if j < 0:
                    break
                cuts.append((chunk, offset + j, chunk.begin + offset + j))
                offset += j + 1
        return cuts

    def mkcut(self, idx):
        ''' Return cut at address, make anonymous cut if there is none '''
        t = self.starts.get(idx)
        if not t:
            t = self.cut(idx)
        return t

    def cut(self, where, length=-1):
        ''' Cut out a chunk '''
        assert where or length == 0x80
        if where >= self.end:
            raise bittools.MisFit("0x%x is past end of allocation (0x%x)" % (where, self.end))

        chunk = self.starts.get(where)
        if not chunk:
            offset, chunk = self.tree.find(where)
            assert offset is not None
            assert offset == chunk.begin
            assert chunk.begin <= where
            assert chunk.begin + len(chunk) > where

        assert self.starts.get(chunk.begin) == chunk

        if chunk.owner:
            raise bittools.MisFit(
                "Has " + str(chunk) +
                " already owned " + str(chunk.owner) +
                " wanted 0x%x" % where
            )

        if chunk.begin == where and length in (-1, len(chunk)):
            return chunk

        if where > chunk.begin:
            self.tree.delete(chunk.begin, chunk)

            i = where - chunk.begin
            newchunk = bittools.R1kSegChunk(chunk.begin, chunk.bits[:i])
            chunk.bits = chunk.bits[i:]
            chunk.begin += i

            self.starts[chunk.begin] = chunk
            assert len(chunk) > 0
            self.tree.insert(chunk.begin, chunk)

            self.starts[newchunk.begin] = newchunk
            assert len(newchunk) > 0
            self.tree.insert(newchunk.begin, newchunk)

        if length in (-1, len(chunk)):
            return chunk

        if length > len(chunk):
            raise bittools.MisFit("Has " + str(chunk) + " want 0x%x" % length)

        assert length < len(chunk)

        self.tree.delete(chunk.begin, chunk)

        newchunk = bittools.R1kSegChunk(chunk.begin, chunk.bits[:length])

        self.starts[newchunk.begin] = newchunk
        assert len(newchunk) > 0
        self.tree.insert(newchunk.begin, newchunk)

        chunk.bits = chunk.bits[length:]
        chunk.begin += length

        self.starts[chunk.begin] = chunk
        assert len(chunk) > 0
        self.tree.insert(chunk.begin, chunk)

        return newchunk


    def render_chunks(self, fo):
        ''' Ask all the chunks to chime in '''
        loffset = 0
        for offset, chunk in self.tree:
            assert offset == loffset
            loffset += len(chunk)
            fo.write(str(chunk) + ":")
            if chunk.owner is None:
                fo.write(" ===================\n")
                bittools.render_chunk(fo, chunk)
            else:
                chunk.owner.render(chunk, fo)
        assert loffset == self.end

    def render_real(self, fo, _this):
        ''' Copy from temp file to output file '''
        fo.write("<H3>Segmented Heap</H3>\n")
        fo.write("<pre>\n")
        for i in open(self.tfn.filename):
            fo.write(html.escape(i))
        fo.write("</pre>\n")
        os.remove(self.tfn.filename)
