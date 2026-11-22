"""SDK32 indexed traversal with typed tables/nodes and independent state hashes."""
from pathlib import Path
from types import FunctionType
import json,struct,subprocess,sys
from tools.experiments import game_indexed_column_event_walker_15169260_match as packet
root,out=packet.ROOT,packet.OUT
import guest as q
from tools.tests import game_node_range_walker_15169070_native as template
from tools.tests.test_game_projected_packet_draw import native_command
CASES=[c for c in q.cases()if not c.list_home and c.payload_kind in(0,1)and c.depth in(-1,0,2)and not c.mode&32]
PATTERNS=list(dict.fromkeys(c.columns for c in CASES))
class Row:
 def __init__(self,c):self.case=c
 def __getattr__(self,name):return getattr(self.case,name)
 @property
 def first(self):return PATTERNS.index(self.columns)
 @property
 def last(self):return self.count
 @property
 def caller(self):return False
def cases():return[Row(c)for c in CASES]
def nid(p):return 0 if not p else q.NODES.index(p)+1
def expected(c):
 c=c.case if isinstance(c,Row)else c;m,calls,obs=q.reference(q.fixture(c),c);s=q.SYMS;values=[m[s['D_800DD190']]]
 values +=[nid(q.read(m,s['D_800DCE50']+4*i))for i in range(208)]
 for i in range(104):
  at=s['D_8008B4A8']+52*i;values.append({0:0,q.g.CB0:1,q.g.CB1:2}[q.read(m,at+28)]);values +=[m[at+j]for j in range(52)if not 28<=j<32]
 values +=[nid(q.read(m,s['D_800DD198']+4*i))for i in range(6)]
 for node in q.NODES:values +=[nid(q.read(m,node+8)),*[m[node+j]for j in range(q.SIZE)if not 8<=j<12]]
 values +=[q.read(m,q.LIST+4*i)for i in range(8)]+[q.read(m,q.CHILD_LIST)]
 trace=[]
 for(t,a),o in zip(calls,obs):
  if t==q.ENTRY:code,x,y,z=5,1,a[1],a[3]&255
  else:code={q.g.HELPER:1,q.g.CLEAN:2,q.g.CB0:3,q.g.CB1:4}[t];x=nid(a[0]);y=0 if code==2 else{q.g.PAYLOAD:0,s['D_800DD190']:1}[a[1]];z=0 if code==2 else a[2]
  trace +=[code,x,y,z,o[0],nid(o[1]),0]
 return template.digest(values),template.digest(trace),len(calls)
def mutations(selected):
 cached=selected.replace('    struct102 *node;','    struct102 *node;\n    void (*callback)(void *,s32,u8);').replace('                if (D_8008B4A8[*(s32 *)indices].unk1C != NULL) {','                callback = D_8008B4A8[*(s32 *)indices].unk1C;\n                if (callback != NULL) {').replace('D_8008B4A8[*(s32 *)indices].unk1C(node, payload, opcode);','callback(node, payload, opcode);')
 stale=selected.replace('    struct102 *node;','    struct102 *node;\n    s32 selected;').replace('            do {\n                if','            do {\n                selected = *(s32 *)indices;\n                if').replace('D_8008B4A8[*(s32 *)indices].unk1C(node, payload, opcode);','D_8008B4A8[selected].unk1C(node, payload, opcode);')
 result={'wrong-count-guard':selected.replace('if (count > 0)','if (count > 1)'),
  'wrong-first-counter':selected.replace('state.index = 0;','state.index = 1;'),
  'wrong-head-column':selected.replace('state.row + *(s32 *)indices * 4','state.row + *(s32 *)indices * 4 + 4'),
  'missing-next-snapshot':selected.replace('D_800DD198[D_800DD190] = (void *)node->unk8;','D_800DD198[D_800DD190] = 0;'),
  'late-next-reload':selected.replace('node = D_800DD198[D_800DD190];','node = (struct102 *)node->unk8;'),
  'cached-callback':cached,'cached-input-entry':stale,
  'missing-callback':selected.replace('D_8008B4A8[*(s32 *)indices].unk1C(node, payload, opcode);',';'),
  'missing-depth-unwind':selected.replace('D_800DD190--;',';'),
  'wrong-opcode':selected.replace('(u8 *)payload, opcode','(u8 *)payload, opcode ^ 0x80'),
  'row-zero-only':selected.replace('D_800DCE50 + sizeof(D_800DCE50)','D_800DCE50 + 0x1A0'),
  'missing-input-advance':selected.replace('indices = (u8 *)indices + 4;',';')}
 assert len(result)==12 and all(v!=selected for v in result.values());return result
EFFECT=r'''static void effect(void*p){void**saved;void*next;if(fired)return;fired=1;saved=cursor();next=*saved;
 if(c->mode&1)((struct102*)p)->unk8=(s32)node(8);
 if(c->mode&2)*saved=next?(void*)((struct102*)next)->unk8:0;
 if(c->mode&4){next=*saved;D_800DD190++;*cursor()=next;}
 if(c->mode&8)D_8008B4A8[inputColumns[0]].unk1C=cb1;
 if(c->mode&16){inputColumns[0]=3;D_8008B4A8[3].unk1C=cb1;}
 if(c->mode&64){record(5,1,1,c->opcode&255);subject(childColumns,1,(s32)data(),(u8)c->opcode);}
 if(c->mode&128)inputColumns[1]=102;
}
'''
def program(selected):
 namespace=dict(template.program.__globals__,root=root,out=out,cases=cases,expected=expected,mutations=mutations,CLAMP_BODY='',
  body=lambda text,name:'void native_original_wrapper(s32 payload,u8 opcode){subject(inputColumns,2,payload,opcode);}')
 render=FunctionType(template.program.__code__,namespace);text=render(selected.replace('func_15169260(','func_15169070('))
 patterns='static const s32 inputPatterns[][8]={'+','.join('{'+','.join(str(p[i%len(p)])for i in range(8))+'}'for p in PATTERNS)+'};\nstatic s32 inputColumns[8],childColumns[1];\n'
 text=text.replace('struct Matrix{',patterns+'struct Matrix{',1)
 replacements={
  'typedef void(*Subject)(s32,s32,s32,u8);':'typedef void(*Subject)(void*,s32,s32,u8);',
  'hash(&trace,(u32)*ctx.last);':'hash(&trace,0);',
  'subject((s32)c->first,(s32)c->last,(s32)data(),(u8)c->opcode);':'subject(inputColumns,(s32)c->last,(s32)data(),(u8)c->opcode);',
  'struct Matrix{u8 before[16],bytes[832],after[16];};':'struct Matrix{u8 before[16];struct102 *heads[208];u8 after[16];};',
  'struct Node{u8 before[8],bytes[128],after[8];};':'struct Node{u8 before[8];struct102 object;u8 after[8];};\n_Static_assert(sizeof(struct102)==472&&__builtin_offsetof(struct102,unk8)==8&&__builtin_offsetof(struct102,unkC)==12,"SDK node layout");',
  '*(void**)(nodes[i].bytes+8)=following[i]<0?0:node((u32)following[i]);':'nodes[i].object.unk8=(s32)(following[i]<0?0:node((u32)following[i]));',
  'nodeId(*(void**)(nodes[i].bytes+8))':'nodeId((void*)nodes[i].object.unk8)',
  'nodes[i].bytes':'((u8 *)&nodes[i].object)',
  'j<128':'j<sizeof(struct102)',
  '(j+128)':'(j+sizeof(struct102))',
  '*(void**)(D_800DCE50':'*(struct102**)(D_800DCE50',
 }
 for old,new in replacements.items():assert old in text,old;text=text.replace(old,new)
 lo=text.index('static void effect(void*p){');hi=text.index('void func_1516972C',lo);text=text[:lo]+EFFECT+text[hi:]
 old='if(!c->empty){*(struct102**)(D_800DCE50+8)=node(0);*(struct102**)(D_800DCE50+12)=node(3);*(struct102**)(D_800DCE50+416+8)=node(5);*(struct102**)(D_800DCE50+416+12)=node(7);}'
 assert old in text
 text=text.replace(old,'if(!c->empty)for(i=0;i<104;i++){*(struct102**)(D_800DCE50+4*i)=node(i&1?3:0);*(struct102**)(D_800DCE50+416+4*i)=node(i&1?7:5);}\n for(i=0;i<8;i++)inputColumns[i]=inputPatterns[c->first][i];childColumns[0]=3;')
 assert text.count(' return h;\n}')==1
 text=text.replace(' return h;\n}',' for(i=0;i<8;i++)hash(&h,(u32)inputColumns[i]);hash(&h,(u32)childColumns[0]);return h;\n}')
 return text
def main():
 selected=packet.MANIFEST['body'];source=out/'native.c';source.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);command=native_command(opt)+['-fstrict-aliasing','-Wno-unused-variable',str(source),'-o',str(exe)]
  r=subprocess.run(command,cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,struct.unpack('<II',r.stderr)if len(r.stderr)==8 else r.stderr)
  profiles[opt]=dict(cases=len(CASES),SDK32=True,strict_aliasing=True,UBSan=True,effective_controls=12)
 report=dict(profiles=profiles,full_SDK_node_descriptor_matrix_input_and_slot_state=True,canaries=True,
  live_input_mutation_and_bounded_recursive_provider=True,effective_source_controls=list(mutations(selected)),
  limits='Incoming count-home mutation, invalid indices/depths, and byte aliases into multi-byte words remain guest-only. The original cleanup provider is contracted.',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
