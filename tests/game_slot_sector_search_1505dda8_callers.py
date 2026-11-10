"""Original caller windows and real 51-word float-return helper integration."""
import csv,itertools,json,struct
from dataclasses import replace
from tools.tests import game_slot_sector_search_1505dda8_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ANGLE=0x1505A630
def census():
 rom=(g.root/'conker/conker.us.bin').read_bytes();rows=list(csv.DictReader((g.root/'conker/retail_layout.us.txt').open()));result={}
 for target in(g.ENTRY,g.HELPER):
  sites=[];pointers=[]
  for at in range(0,len(rom)-3,4):
   w=struct.unpack_from('>I',rom,at)[0]
   if w==target:pointers.append(hex(at))
   if w>>26 in(2,3)and(w&0x03FFFFFF)<<2==target&0x0FFFFFFF:
    pc=0x10000000+at if at<0x2D4B0 else 0x15000000+at-0x2D4B0 if at<0x255880 else 0x16000000+at-0x255880;owner=[v for v in rows if int(v['address'],16)<=pc<int(v['end'],16)];assert len(owner)==1,(hex(at),hex(pc));sites.append(dict(ROM=hex(at),VA=hex(pc),kind='JAL'if w>>26==3 else'J',parent=owner[0]['function'],owner=owner[0]['filename']))
  result[hex(target)]=dict(sites=sites,aligned_literal_pointers=pointers)
 assert[len(result[hex(t)]['sites'])for t in(g.ENTRY,g.HELPER)]==[1,2]
 assert all(v['kind']=='JAL'for r in result.values()for v in r['sites'])and all(not r['aligned_literal_pointers']for r in result.values())
 (g.out/'caller-census.json').write_text(json.dumps(result,indent=2)+'\n');return result
def fixture(c):
 m=g.fixture(c);a=g.actor(c)
 for i in range(26):
  p=g.TABLE+i*812;xyz=(0.,0.,0.)if i==c.match else(20.+i,30.+i,40.+i)
  for j,f in enumerate(xyz):g.put(m,p+0x14+j*4,g.bits(f))
 xyz=((0,0,0),(g.bits(-1.),g.bits(2.),g.bits(-3.)),(0x80000000,1,0x80000001),(0x7F800000,0,g.bits(1.)),(0x7FC12345,g.bits(2.),g.bits(3.)))[c.seed%5]
 for j,v in enumerate(xyz):g.put(m,a+0x14+j*4,v)
 return m
def angle_effect(m,c,slot,dx,dz):
 g.put(m,g.MARK,g.read(m,g.MARK)+1);g.put(m,g.MARK+4,dx);g.put(m,g.MARK+8,slot)
 if c.mutation&1:
  a=g.actor(c);g.put(m,a+0x14,g.bits(5.));g.put(m,a+0x76,g.read(m,a+0x76,2)^0x100,2)
 return c.heading&65535
def helper_reference(m,c,slot,outputs):
 a=g.actor(c);p=g.TABLE+slot*812;dx=g.rounded(g.floating(g.read(m,p+0x14))-g.floating(g.read(m,a+0x14)));dy=g.rounded(g.floating(g.read(m,a+0x18))-g.floating(g.read(m,p+0x18)));dz=g.rounded(g.floating(g.read(m,a+0x1C))-g.floating(g.read(m,p+0x1C)))
 g.put(m,outputs[2],g.bits(dy));heading=angle_effect(m,c,slot,g.bits(dx),g.bits(dz));g.put(m,outputs[0],heading,2)
 x2=g.rounded(dx*dx);y2=g.rounded(dy*dy);z2=g.rounded(dz*dz);g.put(m,outputs[1],g.bits(g.rounded(x2+z2)));return g.bits(g.rounded(g.rounded(x2+y2)+z2)),(g.bits(dx),g.bits(dz),0)
def reference(initial,c,home):
 m=dict(initial);calls=[];slot=0;a=g.actor(c)
 while slot<=g.signed(g.read(m,g.LIMIT)):
  if g.read(m,g.TABLE+slot*812):
   radius=g.rounded(g.rounded(g.floating(g.read(m,a+0x3C))*g.floating(c.scale))*.5);outputs=(home-4,home-8,home-12);value,angles=helper_reference(m,c,slot,outputs);calls.extend(((g.HELPER,(a,slot,*outputs,0)),(ANGLE,angles)))
   if g.floating(value)<g.rounded(radius*radius)and((g.read(m,a+0x76,2)-g.read(m,outputs[0],2)+(c.width&65535)//2)&65535)<(c.width&65535):return m,calls,g.u32(g.s8(slot))
  slot=(slot+1)&255;assert slot<26
 return m,calls,0xFFFFFFFF
class ConnectedOracle(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(map(g.u32,self.arguments(4)));assert a[0]==g.actor(self.c);self.c=replace(self.c,unused=a[1],width=a[2],scale=a[3]);self.entered=a
  elif t==g.HELPER:
   a=tuple(map(g.u32,self.arguments(6)));assert a[0]==g.actor(self.c)and a[5]==0;self.slot=a[1]
  else:assert t==ANGLE,hex(t);a=(self.f[12],self.f[14],self.r[6])
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==ANGLE;args=self.calls[-1][1];value=angle_effect(self.memory,self.c,self.slot,args[0],args[1])
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011
def helper_code(rom):return dict(zip(range(g.HELPER,g.HELPER+204,4),struct.unpack_from('>51I',rom,0x8B3C0)))
def run_target(rom,ws,c,parent=False):
 memory=fixture(c);home=g.STACK+c.phase;code=helper_code(rom)
 if parent:
  start,end=0x150540F4,0x15054114;code.update(zip(range(g.ENTRY,g.ENTRY+360,4),ws));code.update({end:0,0x1505415C:0});window=struct.unpack_from('>8I',rom,0x815A4);m=ConnectedOracle.__new__(ConnectedOracle);m.c=c;m.s=g.symbols();FactoryOracle.__init__(m,window,memory,c,entry=start,arguments=(g.actor(c),c.unused,c.width,c.scale),connected=code);m.r[16]=g.actor(c);m.code=WindowCode(m.code,m);m.code.ends=(end,0x1505415C)
 else:m=ConnectedOracle(ws,memory,c,connected=code)
 m.initial=dict(m.memory);m.before=m.r[:];m.before_f=m.f[:]
 try:m.run()
 except WindowBoundary:assert parent
 else:assert not parent
 expected,calls,result=reference(m.initial,m.c,home);actual=[v for v in m.calls if v[0]!=g.ENTRY];assert actual==calls,(c,parent,'calls');assert g.public(m.memory)==g.public(expected),(c,parent,'public');assert m.r[2]==result,(c,parent,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.r[31]==(0x15054108 if parent else m.before[31])and m.f[20:]==m.before_f[20:],(c,parent,'saved');return m
WINDOWS=((0x1505DBF8,0x1505DC28),(0x1505DE38,0x1505DE7C))
def run_helper_window(rom,c,index):
 start,end=WINDOWS[index];memory=fixture(c);home=g.STACK+c.phase;slot=max(0,c.match);outputs=(home+0xEC,home+0xDC,home+0xD8)if index==0 else(home+0x6C,home+0x68,home+0x64)
 ws=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0);code=helper_code(rom);code[end]=0;code[0x1505DEB8]=0;m=ConnectedOracle.__new__(ConnectedOracle);m.c=c;m.s=g.symbols();FactoryOracle.__init__(m,ws,memory,c,entry=start,arguments=(0,0,0,0),connected=code);m.r[19]=g.actor(c);m.r[17]=slot if index==0 else g.actor(c);m.r[16]=slot;m.r[21],m.r[22],m.r[23]=outputs;m.f[22]=c.scale;m.f[24]=g.bits(.5);m.code=WindowCode(m.code,m);m.code.ends=(end,0x1505DEB8);initial=dict(m.memory)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing helper caller continuation')
 expected=dict(initial);value,angles=helper_reference(expected,c,slot,outputs);assert m.calls==[(g.HELPER,(g.actor(c),slot,*outputs,0)),(ANGLE,angles)]
 assert g.public(m.memory)==g.public(expected)
 for a,size in zip(outputs,(2,4,4)):assert g.canonical(g.read(m.memory,a,size))==g.canonical(g.read(expected,a,size)),(c,index,'outputs',a)
 assert g.canonical(m.f[0])==g.canonical(value)
 if index==0:assert g.canonical(m.f[20])==g.canonical(value)and m.r[24]==c.heading&65535
 else:assert g.canonical(m.f[20])==g.canonical(g.bits(g.rounded(g.rounded(g.floating(c.velocity)*g.floating(c.scale))*.5)))
 return m
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();programs=(g.words(g.out/'selected.o'),struct.unpack_from('>90I',rom,0x8B258));cs=[replace(g.Case(limit=n,pattern=p,match=k,velocity=g.bits(v),alias=a,heading=h,mutation=mu),seed=i%5,phase=(i&1)*8)for i,(n,p,k,v,a,h,mu)in enumerate(itertools.product((-1,0,3),(0,1),(-1,0,1),(0.,2.,float('inf')),(-1,0),(0,256,65535),(0,1)))];seen=set();helper_seen=set();runs=pairs=0
 for parent in(False,True):
  for c in cs:
   models=[run_target(rom,ws,c,parent)for ws in programs];a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);runs+=2;pairs+=1;helper_seen.update(pc for pc in a.visits if g.HELPER<=pc<g.HELPER+204)
   if parent:seen.update(pc for pc in a.visits if 0x150540F4<=pc<0x15054114)
 assert len(seen)==8 and len(helper_seen)==51
 counts={};window_runs=0
 for index,(start,end)in enumerate(WINDOWS):
  covered=set()
  for c in cs[:108]:
   m=run_helper_window(rom,c,index);covered.update(pc for pc in m.visits if start<=pc<end);window_runs+=1
  assert covered==set(range(start,end,4));counts[hex(start)]=len(covered)
 result=dict(cases_per_connected_mode=len(cs),connected_target_and_parent_executions=runs,complete_machine_and_trace_pairs=pairs,real_helper_words=len(helper_seen),parent_window_words=len(seen),helper_caller_window_words=counts,helper_caller_executions=window_runs,all_three_original_call_sites=True,angle_provider_opaque=True,full_parent_algorithms_qualified=False,census=census());(g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
