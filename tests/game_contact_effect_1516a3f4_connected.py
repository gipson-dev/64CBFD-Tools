from tools.tests.game_contact_effect_1516a3f4_oracle import *
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();table=0x8008C9C8
 assert struct.unpack_from('>I',rom,0x2314a4)[0]==ENTRY, 'retail table entry 7 changed'
 programs=[struct.unpack_from('>81I',rom,0x1978a4)]+[program(out/(x+'.o')) for x in ('after','generated','generic')]
 windows=((0x15167e80,0x15167eb0,0x2f),(0x151689d4,0x15168a00,0xb2))
 class Connected(Machine):
  def __init__(self,w,c,window):
   start,end,field=window;memory=fixture(c)
   for i in range(0x80,0xd0):memory[OWNER+i]=(i*29+0x51)&255
   for i in range(22):put(memory,table+4*i,ENTRY if i==7 else 0)
   memory[OWNER+field]=7;code=dict(zip(range(ENTRY,ENTRY+len(w)*4,4),w));code[end]=0
   words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
   FactoryOracle.__init__(self,words,memory,c,entry=start,s=S,arguments=(OWNER,),connected=code)
   self.observations=[];self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:self.calls.append((ENTRY,(self.r[4],)))
   else:super().record_call(t)
 count=0
 for phase,initial,floor,alpha,mutation in itertools.product((0,8),(0,128,0x7fffffff),(127,128,0x7fffffff),(0,255),(0,1)):
  c=Case(phase,initial,floor,alpha,0x3f000000,mutation);want,calls,observations=reference(c)
  for window in windows:
   start,end,field=window;expected=dict(want)
   for i in range(0x80,0xd0):expected[OWNER+i]=(i*29+0x51)&255
   for i in range(22):put(expected,table+4*i,ENTRY if i==7 else 0)
   expected[OWNER+field]=7
   for words in programs:
    m=Connected(words,c,window)
    try:m.run();raise AssertionError('missing caller boundary')
    except WindowBoundary:pass
    assert (public(m.memory),m.calls,m.observations)==(expected,[(ENTRY,(OWNER,))]+calls,observations),(c,window,m.calls,calls)
   count+=1
 print('two original indirect caller windows:',count,'cases per stream via table entry 7',flush=True)
