from pathlib import Path
import struct,subprocess
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;obj=out/'variant-case1_default.o';_,fs,_=parse_object(obj)
pool=sections(obj)['.rodata'][1];assert len(pool)==64
relocs=subprocess.run(['mips-linux-gnu-readelf','-r',str(obj)],capture_output=True,text=True,check=True).stdout.split("Relocation section '.rel.rodata'",1)[1]
assert sum('R_MIPS_32' in line and '.text' in line for line in relocs.splitlines())==16
words=struct.unpack('>16I',pool);actual=[0x1500E738+(value-fs['func_1500E738']['value']) for value in words]
addr,game=sections(root/'conker/build/conker.us.elf')['.game_data'];table=game[0x800961D0-addr:0x800961D0-addr+64];retail=list(struct.unpack('>16I',table))
assert actual==retail,(actual,retail)
print('all 16 compiler table relocations resolve to the existing retail case addresses',flush=True)
