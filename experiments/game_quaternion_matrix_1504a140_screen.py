"""Screen uncredited quaternion-matrix C against retail and bounded models."""
from pathlib import Path
import hashlib,itertools,json,os,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-quaternion-matrix-v3';entry=0x1504a140
SOURCE="""void func_1504A140(float *q, float *m) {
    float x = q[0], y = q[1], z = q[2], w = q[3];
    float scale = 2.0f / (((x*x + y*y) + z*z) + w*w);
    float sy = y*scale, sz = z*scale, sw = w*scale;
    float xy=x*sy, xz=x*sz, xw=x*sw;
    float yy=y*sy, yz=y*sz, yw=y*sw;
    float zz=z*sz, zw=z*sw, ww=w*sw;
    m[0]=1.0f-(zz+ww); m[1]=yz+xw; m[2]=yw-xz;
    m[4]=yz-xw; m[6]=zw+xy; m[5]=1.0f-(yy+ww);
    m[9]=zw-xy; m[8]=yw+xz; m[3]=0.0f; m[7]=0.0f;
    m[11]=0.0f; m[15]=1.0f; m[10]=1.0f-(yy+zz);
}
"""

def f(x):return floating(bits(x))
def fixture(qv,alias):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-256,128)};m.update({0x30000+i:(i*13+0x53)&255 for i in range(256)});m.update({0x40000+i:(i*11+0x37)&255 for i in range(256)})
 output=0x30040;q=(0x40040,output,output+4,output+32,output-8)[alias]
 for i,v in enumerate(qv):put(m,q+4*i,bits(v))
 return m,(q,output)
def model(initial,args):
 m=initial.copy();q,o=args;x,y,z,w=[floating(read(m,q+i*4)) for i in range(4)]
 scale=f(2.0/f(f(w*w)+f(f(f(x*x)+f(y*y))+f(z*z))))
 sy,sz,sw=f(y*scale),f(z*scale),f(w*scale)
 xy,xz,xw=f(x*sy),f(x*sz),f(x*sw)
 yy,yz,yw=f(y*sy),f(y*sz),f(y*sw)
 zz,zw,ww=f(z*sz),f(z*sw),f(w*sw)
 for index,value in ((0,f(1.-f(zz+ww))),(1,f(yz+xw)),(2,f(yw-xz)),(4,f(yz-xw)),(6,f(zw+xy)),(5,f(1.-f(yy+ww))),(9,f(zw-xy)),(8,f(yw+xz)),(3,0.),(7,0.),(11,0.),(15,1.),(10,f(1.-f(yy+zz)))):put(m,o+index*4,bits(value))
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+128}


def is_nan(n):return n&0x7f800000==0x7f800000 and n&0x007fffff!=0
class NaNOracle(FactoryOracle):
 prefer_left=True
 def execute(self,word):
  if word>>26==17 and (word>>21)&31==16 and (word&63) in (0,1,2,3):
   left=self.f[(word>>11)&31];right=self.f[(word>>16)&31]
   if is_nan(left) or is_nan(right):
    chosen=(left if is_nan(left) else right) if self.prefer_left else (right if is_nan(right) else left)
    self.f[(word>>6)&31]=chosen|0x00400000;return
  super().execute(word)

def array_variant(source):
 names=('xy','xz','xw','yy','yz','yw','zz','zw','ww')
 old='    float xy=x*sy, xz=x*sz, xw=x*sw;\n    float yy=y*sy, yz=y*sz, yw=y*sw;\n    float zz=z*sz, zw=z*sw, ww=w*sw;'
 expr=('x*sy','x*sz','x*sw','y*sy','y*sz','y*sw','z*sz','z*sw','w*sw')
 assert source.count(old)==1
 source=source.replace(old,'    float t[9];\n    '+'; '.join('t[%d]=%s'%(i,e) for i,e in enumerate(expr))+';')
 for i,n in enumerate(names):source=re.sub(r'\b'+n+r'\b','t[%d]'%i,source)
 return source


def direct_variant(source):
 declaration='    float x = q[0], y = q[1], z = q[2], w = q[3];\n'
 assert source.count(declaration)==1
 source=source.replace(declaration,'')
 for i,n in enumerate('xyzw'):source=re.sub(r'\b'+n+r'\b','q[%d]'%i,source)
 return source

def main():
 out.mkdir(parents=True,exist_ok=True)
 ownerfile=root/'conker/src/game/generated_770F0.c';owner=ownerfile.read_text();name='func_1504A140';stub=body(owner,name)
 assert stub=='s32 func_1504A140() {\n    return 0;\n}'
 rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>89I',rom,0x775f0));slot=list(struct.unpack_from('>92I',rom,0x775f0))
 pattern='(((x*x + y*y) + z*z) + w*w)';assert SOURCE.count(pattern)==1
 fixed=SOURCE.replace(pattern,'(w*w + ((x*x + y*y) + z*z))')
 base,bd=compile_owner(root,out,owner,'baseline');programs={'retail':truth};summary={}
 for label,src in (('original',SOURCE),('scalar',fixed),('array',array_variant(fixed)),('direct',direct_variant(array_variant(fixed)))):
  obj,diag=compile_owner(root,out,owner.replace(stub,src),label)
  assert diag==bd and same_functions(base,obj,(name,))==3 and normalized_pools(base)==normalized_pools(obj)
  words=bound_blob(*payload(obj,name),{});programs[label]=words
  summary[label]={'words':len(words),'same_retail_slot_positions':sum(a==b for a,b in zip(words,slot)),'frame_instruction':hex(words[0])}
 assert [(summary[k]['words'],summary[k]['same_retail_slot_positions']) for k in ('original','scalar','array','direct')]==[(86,8),(86,9),(92,11),(97,7)],summary
 corpus=[];diff={k:0 for k in summary}
 for qv in itertools.product((-2.,-.25,.5,1.),repeat=4):
  for alias in range(5):
   initial,args=fixture(qv,alias);want=public(model(initial,args));corpus.append((initial,args,want))
   for label,code in programs.items():
    actual=FactoryOracle(code,initial.copy(),Case(),entry=entry,s={},arguments=args).run();different=public(actual.memory)!=want
    if label=='retail':assert not different,(qv,alias)
    else:diff[label]+=different
 assert len(corpus)==1280 and not any(diff.values()),diff
 controls=((0x46062200,0x46062201),(0xe4aa0000,0xe4aa0004),(0x46085183,0x46085182))
 for old,new in controls:
  assert truth.count(old)==1,hex(old)
  altered=truth.copy();altered[altered.index(old)]=new;caught=False
  for initial,args,want in corpus:
   try:caught=public(FactoryOracle(altered,initial.copy(),Case(),entry=entry,s={},arguments=args).run().memory)!=want
   except (AssertionError,ZeroDivisionError,OverflowError,KeyError):caught=True
   if caught:break
  assert caught,hex(old)
 nan_counts={}
 for rule in ('left','right'):
  NaNOracle.prefer_left=rule=='left';counts={k:0 for k in summary};cases=0
  for vals in itertools.product((0x3f800000,0x7fc00001,0x7fc30002),repeat=4):
   if not any(is_nan(v) for v in vals):continue
   initial,args=fixture((1.,1.,1.,1.),0)
   for i,v in enumerate(vals):put(initial,args[0]+4*i,v)
   def observe(code):
    machine=NaNOracle(code,initial.copy(),Case(),entry=entry,s={},arguments=args).run()
    return tuple(read(machine.memory,args[1]+i*4) for i in range(16))
   expected=observe(truth)
   for label in summary:counts[label]+=observe(programs[label])!=expected
   cases+=1
  assert cases==80;nan_counts[rule]=counts
 assert nan_counts=={'left':{'original':14,'scalar':0,'array':50,'direct':50},'right':{'original':26,'scalar':0,'array':0,'direct':34}},nan_counts
 report={'uncredited':True,'owner_sha256':hashlib.sha256(ownerfile.read_bytes()).hexdigest(),'rom_sha256':hashlib.sha256(rom).hexdigest(),'retail_real_words':89,'retail_slot_words':92,'variants':summary,'same_neighbor_functions':3,'normalized_pools_equal':True,'finite_cases_per_stream':len(corpus),'finite_differences':diff,'negative_controls':len(controls),'nan_cases_per_rule':cases,'nan_payload_differences':nan_counts,'nan_assumption':'left or right operand wins with quiet bit set; hardware rule unverified','limits':'finite nonzero norms; FCSR, fault-prefix, private-stack, native, caller, actual Make and full image not qualified'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
