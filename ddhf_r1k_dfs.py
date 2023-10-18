'''
Rational R1000/400 DFS Tapes from Datamuseum.dk's BitStore
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

from autoarchaeologist import ddhf

from autoarchaeologist.generic import tap_file
from autoarchaeologist.generic import ansi_tape_labels
from autoarchaeologist.generic import sccs_id
from autoarchaeologist.type_case import Ascii
from autoarchaeologist.rational import tape_blocks
from autoarchaeologist.rational import index_data
from autoarchaeologist.rational import dfs_tape
from autoarchaeologist.rational import r1k_assy
from autoarchaeologist.rational import r1k_configuration
from autoarchaeologist.rational import r1k_ucode
from autoarchaeologist.rational import r1k_m200
from autoarchaeologist.rational import r1k_experiment

from autoarchaeologist.generic import samesame
from autoarchaeologist.generic import textfiles

class TextFile(textfiles.TextFile):
    def credible(self):
        if len(self.txt) < 5:
            return False
        if len(self.txt) < 10 and '\n' not in self.txt:
            return False
        if len(self.this) - len(self.txt) >= 1024:
            return False
        return True

class TypeCase(Ascii):
    ''' ... '''
    def __init__(self):
        super().__init__()
        self.set_slug(0, ' ', '«nul»', self.EOF)

class R1KDFS(ddhf.DDHF_Excavation):
    ''' Rational R1000/400 DFS tapes '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_examiner(tap_file.TAPfile)
        self.add_examiner(ansi_tape_labels.AnsiTapeLabels)
        self.add_examiner(tape_blocks.R1K_Tape_blocks)
        self.add_examiner(index_data.R1K_Index_Data)
        self.add_examiner(dfs_tape.R1K_DFS_Tape)
        self.add_examiner(r1k_configuration.R1kM200ConfigFile)
        self.add_examiner(r1k_assy.R1kAssyFile)
        self.add_examiner(r1k_ucode.R1K_Ucode_File)
        self.add_examiner(r1k_m200.R1kM200File)
        self.add_examiner(r1k_experiment.R1kExperiment)
        self.add_examiner(TextFile)
        self.add_examiner(sccs_id.SccsId)
        self.add_examiner(samesame.SameSame)

        self.type_case = TypeCase()

        self.from_bitstore(
            "30000744",   # precise file sizes
            "30000407",   # precise file sizes

            "30000528",   # file sizes rounded up
            "30000743",   # file sizes rounded up
            "30000750",   # file sizes rounded up
        )

if __name__ == "__main__":
    ddhf.main(
        R1KDFS,
        html_subdir="r1k_dfs",
        ddhf_topic = "Rational R1000/400 DFS Tapes",
        ddhf_topic_link = 'https://datamuseum.dk/wiki/Rational/R1000s400',
    )
