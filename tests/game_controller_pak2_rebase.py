"""Independently link retail and generated objects with equivalent PIF aliases."""
from pathlib import Path
import subprocess,json
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-controller-pak2-durable'
def link(obj,entry,defs,label):
 elf=out/(label+'.elf');binary=out/(label+'.bin')
 undef=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout.splitlines()
 names=[line.split()[-1] for line in undef if line.split()]
 assert set(names)<=set(defs),(obj,set(names)-set(defs))
 script=out/(label+'.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 argv=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','0',*[x for name in names for x in ('--defsym',f'{name}={hex(defs[name])}')],'-o',str(elf),str(obj)]
 r=subprocess.run(argv,capture_output=True,text=True);assert not r.returncode,r.stderr
 subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
 return binary.read_bytes()
count=0
for kind in ('read','write'):
 name='__osContRam'+kind.capitalize()+'2';child='__osPackRam'+kind.capitalize()+'Data2'
 offset=0x244 if kind=='read' else 0x230; sizes=(580,360) if kind=='read' else (560,380)
 for index,(entry,pif) in enumerate(((0x15100000,0x80010000),(0x17107ff0,0x80017fc4),(0x1910fff0,0x80017ffc),(0x1b10fff0,0x8001fffc))):
  defs={'D_800429D0':pif,'D_80042A0C':pif+60,'__osPfsPifRam':pif,child:entry+offset,'__osContLastCmd':0x80070010}
  for i,n in enumerate(('__osContAddressCrc','__osContDataCrc','__osPfsGetStatus','osRecvMesg','__osSiGetAccess','__osSiRawStartDma','__osSiRelAccess')):defs[n]=(entry&0xf0000000)+0x10000+i*0x100
  a=link(out/(name+'-retail.o'),entry,defs,f'{kind}-{index}-retail-parent')[:sizes[0]]
  b=link(out/(child+'-retail.o'),entry+offset,defs,f'{kind}-{index}-retail-child')[:sizes[1]]
  for suffix in ('after','generated','generic'):
   c=link(out/f'generated_contram{kind}2-{suffix}.o',entry,defs,f'{kind}-{index}-{suffix}')
   assert c[:sizes[0]]==a and c[offset:offset+sizes[1]]==b,(kind,index,suffix)
  count+=2
report={'functions_rebased':count,'independent_pif_bases':4,'including_low_half_carry':True,'retail_aliases_linked_to_pif_offsets':True,'streams':3}
(out/'rebase.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
