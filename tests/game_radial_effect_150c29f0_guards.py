"""Closed schedule/home/register groups and fail-closed guard application."""
import csv,io,json,struct
from tools.experiments import game_radial_effect_150c29f0_match as s
from tools.experiments.game_paired_ground_constructor_match import payload

def main():
 raw,refs=payload(s.OUT/'recovered.o',s.NAME);fixed,fr=s.normalize(raw,refs);a=list(struct.unpack('>132I',raw));b=list(struct.unpack('>132I',fixed))
 assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==set(s.PATCHES)
 assert a[5]==b[5]==0x00402025
 # Exact symbolic block effects; A0 equals V0 on entry after the shared move.
 def block(words):
  regs={i:('input',i) for i in range(32)};regs[4]=regs[2];memory={}
  for w in words:
   op,rs,rt,imm=w>>26,w>>21&31,w>>16&31,w&65535
   if op==9:regs[rt]=('add32',regs[rs],(imm^32768)-32768)
   elif op==12:regs[rt]=('and32',regs[rs],imm)
   elif op in (40,41):
    for j in range(1 if op==40 else 2):memory[(regs[rs],imm+j)]=('byte',regs[rt],j,1 if op==40 else 2)
   else:raise AssertionError(hex(w))
  return regs,memory
 assert block(a[6:9])==block(b[6:9]) and a[6:9]==[0x2484ffc0,0x308e00ff,0xa3a20033] and b[6:9]==[0xa3a40033,0x2484ffc0,0x308e00ff]
 assert block(a[27:29])==block(b[27:29]) and a[27:29]==b[27:29][::-1] and a[27]&65535==0x5c and a[28]&65535==0x5e
 # Only the two encoded accesses name either private pointer home. Both are
 # beyond outgoing arguments, outside the packet and away from the RA save.
 def stack_at(words,offset):return [i for i,w in enumerate(words) if w>>26 in (32,33,35,36,37,40,41,43,49,53,57,61) and w>>21&31==29 and w&65535==offset]
 assert stack_at(a,0x84)==[39,52] and not stack_at(a,0x20)
 assert stack_at(b,0x20)==[39,52] and not stack_at(b,0x84)
 assert a[39]>>26==43 and a[52]>>26==35 and a[39]>>16&31==a[52]>>16&31==3
 assert 0x18<=0x20<0x3c and 0x84==0x3c+72 and 0x1c not in (0x20,0x84)
 assert a[0]==b[0]==0x27bdff78 and a[1]==b[1]==0xafbf001c and a[-4:]==b[-4:]
 # The owner reload and its two byte reads are one isolated scratch role;
 # only A0..A3 and stack arguments are live at the following O32 call.
 assert [a[i] for i in (104,115,117)]==[0x8fa30088,0x906f000c,0x90780001]
 assert [b[i] for i in (104,115,117)]==[0x8fa20088,0x904f000c,0x90580001]
 def gpr_uses(w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op in (32,33,35,36,37):return {rs},{rt}
  if op in (40,41,43):return {rs,rt},set()
  if op in (49,53,57,61):return {rs},set()
  if op==15:return set(),{rt}
  if op in (9,12,13):return {rs},{rt}
  if op in (4,5):return {rs,rt},set()
  if op in (1,6,7):return {rs},set()
  if op==17:return ({rt},set()) if rs==4 else (set(),{rt}) if rs==0 else (set(),set())
  if op==0:
   if fn in (0,2,3):return {rt},{rd}
   if fn in (16,18):return set(),{rd}
   if fn in (33,35,36,37):return {rs,rt},{rd}
  raise AssertionError(hex(w))
 assert [i for i in range(104,118) if set.union(*gpr_uses(a[i]))&{2,3}]==[104,115,117]
 original=(s.ROOT/'conker/conker.us.bin').read_bytes();callee=struct.unpack_from('>186I',original,0x176a00)
 for w in callee:
  if w>>26==3:break
  reads,_=gpr_uses(w);assert not reads&{2,3}
 else:raise AssertionError('No bounded constructor call frontier')
 assert a[22]==0x46002082 and b[22]==0x46040082
 # Ordered NaN changes are deliberately tested by qualification; no claim
 # that swapping arbitrary NaN operands preserves the raw compiler result.
 rejected=0
 for i in s.PATCHES:
  corrupt=bytearray(raw);corrupt[i*4+3]^=1
  try:s.normalize(bytes(corrupt),refs)
  except AssertionError:rejected+=1
  else:raise AssertionError('Corrupt compiler word accepted')
 for offset in refs:
  wrong=dict(refs);wrong[offset]=[('R_MIPS_26','func_150ADA20')]
  if wrong[offset]==refs[offset]:wrong[offset]=[('R_MIPS_26','func_150ADA68')]
  try:s.normalize(raw,wrong)
  except AssertionError:rejected+=1
  else:raise AssertionError('Corrupt relocation accepted')
 rows=list(csv.DictReader(io.StringIO((s.OUT/'proposed-guards.csv').read_text())));selected=[r for r in rows if r['function']==s.NAME]
 assert len(selected)==11 and all(r['filename']=='game_EF410' and r['omit']=='false' and not r['insert_after'] and r['expected_relocations']==r['replacement_relocations']=='-' for r in selected)
 report=dict(groups=5,guards=11,frame_unchanged=True,private_pointer_homes=[0x84,0x20],home_not_exposed_to_helpers=True,defined_owner_must_not_alias_callee_private_frame=True,corrupt_words_and_relocations_rejected=rejected,source_radius_order_restored=True)
 (s.OUT/'guard-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
