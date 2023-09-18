#!/usr/bin/env python3

'''
   Generic Text files, based on type_case
'''

PATTERNS = {
    b'+++ Low_Level_Action Started':	'R1000 Log file',
}

class TextFiles():

    def __init__(self, this):
        if not this.has_note("ASCII"):
            return
        for k, v in PATTERNS.items():
            if k in this.tobytes():
                this.add_note(v)

        if this[:2] == b'%!':
            this.add_note("PostScript")

class TextFile():
    ''' General Text-File-Excavator '''

    verbose = False

    MAX_TAIL = 128

    def __init__(self, this):
        self.this = this
        self.txt = []
        type_case = this.type_case
        for j in this.iter_bytes():
            slug = type_case.slugs[j]
            if slug.flags & type_case.INVALID:
                if self.verbose:
                    print(this, "TextFile fails on", hex(j))
                return
            if slug.flags & type_case.IGNORE:
                continue
            self.txt.append(slug.long)
            if slug.flags & type_case.EOF:
                break
        if not self.credible():
            return
        tmpfile = this.add_utf8_interpretation("TextFile")
        with open(tmpfile.filename, "w", encoding="utf-8") as file:
            file.write(''.join(self.txt))
        this.add_type("TextFile")

    def credible(self):
        ''' Determine if result warrants a new artifact '''
        if len(self.this) - len(self.txt) > self.MAX_TAIL:
            return False
        if '\n' not in self.txt:
            return False
        return True
