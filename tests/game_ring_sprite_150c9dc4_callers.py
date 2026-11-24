"""Original sprite callback window and independently bound 0x7C retail copy contract."""
import hashlib,itertools,json,struct
from tools.experiments import game_ring_sprite_150c9dc4_match as p
from tools.tests import game_ring_sprite_150c9dc4_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOW=0x150c8cb8;END=0x150c8ce4;TABLE=0x8008885c
def run(m):
 m.code[END]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run();raise AssertionError('Missing caller boundary')
 except WindowBoundary:return m
def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word==jal:sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x22d31c],(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();at=p.elf_slot_offset(before,TABLE,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 words=list(struct.unpack_from('>11I',rom,0xf6168));assert words==[0xe7a20010,0x820f003c,0x4407a000,0x02002025,0x000fc080,0x03d8c821,0x8f390000,0x02e02825,0x322600ff,0x0320f809,0]
 cases=0
 for ws in g.streams():
  code=dict(zip(range(g.ENTRY,g.ENTRY+696,4),ws))
  for phase,angle,mode,outcome in itertools.product((0,8),(0,127,128,255),(0,7,15),(0,1)):
   c=g.Case(phase=phase,angle=0xabcdef00|angle,mode=mode,outcome=outcome,point_override=g.STACK+phase+0x74);memory=g.fixture(c);g.put(memory,g.OWNER+0x3c,1,1);g.put(memory,TABLE,g.ENTRY)
   def model(selected):
    m=g.Oracle(selected,c,entry=WINDOW,memory=dict(memory),arguments=(),connected=code);m.r[16]=g.OWNER;m.r[17]=c.angle;m.r[23]=g.point(c);m.r[30]=TABLE-4;m.f[20]=c.unused_sine;m.f[2]=c.unused_cosine;m.before=m.r[:];m.before_f=m.f[:];return m
   wanted,calls,obs,fcsr=g.reference(memory,c);m=run(model(words));expected=(g.OWNER,g.point(c),angle,c.unused_sine,c.unused_cosine)
   assert m.calls==[(g.ENTRY,expected),*calls];assert g.public(m.memory,c)==g.public(wanted,c);assert m.observations==obs;assert m.fcsr==fcsr and m.r[29]==g.STACK+phase and m.r[16:24]==m.before[16:24]and m.r[30]==m.before[30]and m.f[20:]==m.before_f[20:];cases+=1
 bad=list(words);bad[8]=0x3226007f;m=run(model(bad));assert m.calls[0][1][2]==127 and m.calls!=[(g.ENTRY,expected),*calls]
 # Independently bind the complete original wrapper and descriptor consumer.
 asm=(p.OUT/'baseline/conker/asm/15F680.s').read_text();symbols={n:v[1]for _,n,v,_ in p.symbol_rows(before)};helpers=[]
 for name,entry,romat,size in [('func_1513264C',0x1513264c,0x15fafc,1024),('func_15132A4C',0x15132a4c,0x15fefc,60)]:
  fragment='glabel '+name+asm.split('glabel '+name,1)[1].split('endlabel '+name,1)[0]+'endlabel '+name+'\n';target=p.OUT/(name+'-retail.o');p.assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'.size '+name+',.-'+name+'\n',target);data,refs=g.payload(target,name)
  for pairs in refs.values():
   for _,label in pairs:
    if label.startswith(('D_','func_')):symbols[label]=int(label.split('_',1)[1],16)
  linked=g.bound_blob(data,refs,symbols);pristine=rom[romat:romat+size];assert linked==list(struct.unpack('>'+str(size//4)+'I',pristine));at=p.elf_slot_offset(before,entry,size);helpers.append(dict(function=name,words=size//4,sha256=hashlib.sha256(pristine).hexdigest(),matches_live_ELF=before[at:at+size]==pristine))
 assert helpers[0]['matches_live_ELF']is False and helpers[1]['matches_live_ELF']is True
 assert rom[0x15fd74:0x15fd7c]==bytes.fromhex('0c008bb02406007c')
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer=hex(TABLE),actual_caller_cases=cases,streams=4,caller_routes=1,five_argument_callback_ABI=True,ignored_float_payloads_preserved=True,effective_wrong_angle_mask_control=True,additional_static_entry_references=0,complete_parent_execution=False,descriptor_copy_bytes=124,original_helpers=helpers,retail_consumer_independently_bound=True,live_consumer_remains_unmatched=True,helpers_internals_contracted=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
