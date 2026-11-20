from pathlib import Path
import importlib.util,json,struct,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run(root,out,types,fragment,guest):
 values=[];corpus=list(guest.cases());values.append(len(corpus))
 def index(ptr):
  if not ptr:return 0xFFFFFFFF
  q=ptr-guest.NODES;return(q//0x300)*3+(q%0x300)//0x80
 for c in corpus:
  m=guest.fixture(c);answer,_=guest.reference(m,c.key);values.extend((c.key,*c.columns,index(answer)))
  for group in range(2):
   for row in range(2):values.append(index(guest.read(m,guest.HEADS+row*0x1A0+c.columns[group]*4)))
  for chain in range(4):
   for depth in range(3):
    at=guest.NODES+chain*0x300+depth*0x80;values.extend((m[at+0x13],guest.read(m,at+0x28),index(guest.read(m,at+8))))
 binary=out/'native-input.bin';binary.write_bytes(struct.pack('>%dI'%len(values),*values))
 template=(Path(__file__).with_suffix('.c.in')).read_text().replace('@TYPES@',types).replace('@BINARY@',binary.relative_to(root).as_posix()).replace('@START@',START)
 controls={
 'type':fragment.replace('node->type == 0x2E','node->type == 0x2F'),
 'key':fragment.replace('node->key == key','node->key != key'),
 'next':fragment.replace('node = node->next;','node = NULL;'),
 'outer-bound':fragment.replace('nextGroup < 2','nextGroup < 1'),
 'row-bound':fragment.replace('nextRow < 2','nextRow < 1'),
 'key-width':fragment.replace('node->key == key','(u16)node->key == (u16)key'),
 'type-mask':fragment.replace('node->type == 0x2E','(node->type & 0x7F) == 0x2E')}
 assert all(v!=fragment for v in controls.values());checks=[]
 for label,body,opt in[('valid',fragment,opt)for opt in('-O0','-O2','-O3')]+[(n,t,'-O2')for n,t in controls.items()]:
  path=out/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(template.replace('@FRAGMENT@',body))
  q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,timeout=20);assert(q.returncode==0)==(label=='valid'),(label,q.returncode)
  checks.append(dict(label=label,profile=opt,exit_code=q.returncode))
 result=dict(cases_each_profile=len(corpus),profiles=3,controls=len(controls),SDK32=True,strict_aliasing=True,UBSan=True,checks=checks)
 (out/'native-report.json').write_text(json.dumps(result,indent=2)+'\n');return result
