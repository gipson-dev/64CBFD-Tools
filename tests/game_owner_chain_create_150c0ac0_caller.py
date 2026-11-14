from tools.tests.game_owner_chain_create_150c0ac0_common import *
caller=0x1514f5cc;rom=(conker/'conker.us.bin').read_bytes();body=struct.unpack_from('>26I',rom,0x17ca7c);assert body[20]==0x0d4302b0
copy_words=struct.unpack_from('>11I',rom,0x22ec0);code=dict(zip(range(COPY,COPY+44,4),copy_words))
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==entry:self.calls.append((t,tuple(self.arguments(3))));return
  return super().record_call(t)
count=0
for valid,allocation,mutation,identity in itertools.product((0,1),(0,1),(0,1,2,3),(0,0x7f,0xff)):
 if valid and allocation and mutation&1:continue
 c=Scenario(20,4,1,allocation,mutation,0xff,1,STACK-0x1c,OUTPUT);m=fixture(c);m[RESOURCE+0x3b]=identity
 put(m,RESOURCE,0x12345678 if valid else 0);const=syms['D_800A5E5C'];m.update({const+i:0 for i in range(4)});put(m,const,0x3e800000)
 # Build the request as the original caller does before entering the callee.
 put(m,c.desc,0);put(m,c.desc+4,0);put(m,c.desc+8,RESOURCE);m[c.desc+0xc]=identity;put(m,c.desc+0x10,0x3e800000);put(m,c.desc+0x14,20,2);put(m,c.desc+0x16,0x12c,2);m[c.desc+0x18]=4
 want,calls,ret=reference(m,c);runs=[]
 for name in ('retail','raw','guarded'):
  q=CallerOracle(programs[name],m.copy(),c,connected=code);q.code.update(zip(range(caller,caller+104,4),body));q.entry=caller;q.r[4]=RESOURCE;q.before=q.r[:]
  q.run();assert (public(q.memory),q.calls,q.r[2])==(want,[(entry,(c.desc,0xff,1))]+calls,ret),(name,valid,allocation,mutation,identity,q.calls,calls,hex(q.r[2]),hex(ret));runs.append(q)
 assert runs[0].memory==runs[1].memory==runs[2].memory and runs[0].r==runs[1].r==runs[2].r;count+=1
print(json.dumps(dict(actual_caller_cases=count,caller='func_1514F5CC',original_caller_words=26,original_memcpy_words=11,allocator_modeled=True,uncredited=True)),flush=True)
