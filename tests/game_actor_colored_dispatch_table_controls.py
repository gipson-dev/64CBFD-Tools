import json,struct,sys
from pathlib import Path
from tools.experiments import game_actor_colored_dispatch_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object,ELF_HEADER,SECTION_HEADER,read_c_string
from tools.experiments.game_actor_classifier_candidates import sections
def main():
 candidate=out/'mixed-target.o';elf=(root/'conker/build/conker.us.elf').read_bytes();retail=struct.unpack_from('>41I',elf,0x242b20+0x800a2298-0x80082b20)
 def check(path):
  text,fs,rs=parse_object(path);base=fs['func_151026BC']['value'];pool=sections(path);table=pool['.rodata'][1];rel=pool['.rel.rodata'][1];assert len(table)>=164 and len(rel)==41*8
  offsets=struct.unpack_from('>41I',table);assert tuple(0x151026bc+(v-base)for v in offsets)==retail
  assert [struct.unpack_from('>II',rel,i*8)for i in range(41)]==[(i*4,0x102)for i in range(41)]
 check(candidate);raw=candidate.read_bytes();h=ELF_HEADER.unpack_from(raw);hs=[SECTION_HEADER.unpack_from(raw,h[6]+i*h[11])for i in range(h[12])];names=hs[h[13]];strings=raw[names[4]:names[4]+names[5]];pool=next(x for x in hs if read_c_string(strings,x[0])=='.rodata');rel=next(x for x in hs if read_c_string(strings,x[0])=='.rel.rodata')
 for i in range(42):
  bad=bytearray(raw);bad[(pool[4]+4*i+3)if i<41 else (rel[4]+7)]^=1;path=out/f'table-bad-{i}.o';path.write_bytes(bad)
  try:check(path)
  except AssertionError:pass
  else:raise AssertionError(('failed corruption control',i))
 report=dict(entries=41,corruption_controls=42,source_installed=False);(out/'table_controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
