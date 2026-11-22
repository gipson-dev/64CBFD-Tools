"""SDK32 column traversal with typed storage and effective source controls."""
from pathlib import Path
from types import FunctionType,SimpleNamespace
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_column_event_walker_1516944c_guest as p
from tools.tests import game_node_range_walker_15169070_native as template
from tools.tests.test_game_projected_packet_draw import native_command
g=p.g

def cases():
 return[c for c in p.cases()if g.s32(c.first)>=0 and c.payload_kind in(0,1)and c.depth in(-1,0,2)and not c.mode&(16|32|128)]
def mutations(selected):
 cached=selected.replace('    void *node;','    void *node;\n    void (*callback)(void *,s32,u8);').replace('        if (descriptor->unk1C != NULL) {','        callback = descriptor->unk1C;\n        if (callback != NULL) {').replace('descriptor->unk1C(node, payload, opcode);','callback(node, payload, opcode);')
 result={'wrong-upper-bound':selected.replace('column = 0x67;','column = 0x66;'),
  'wrong-row-stride':selected.replace('head += 0x1A0;','head += 0x19C;'),
  'missing-next-snapshot':selected.replace('D_800DD198[D_800DD190] = *(void **)((u8 *)node + 8);','D_800DD198[D_800DD190] = 0;'),
  'late-next-reload':selected.replace('node = D_800DD198[D_800DD190];','node = *(void **)((u8 *)node + 8);'),
  'cached-callback':cached,'missing-callback':selected.replace('descriptor->unk1C(node, payload, opcode);',';'),
  'missing-depth-unwind':selected.replace('D_800DD190--;',';'),
  'wrong-opcode-byte':selected.replace('(u8 *)payload, opcode','(u8 *)payload, opcode ^ 0x80'),
  'wrong-payload':selected.replace('(u8 *)payload, opcode','(u8 *)payload + 1, opcode'),
  'row-zero-only':selected.replace('D_800DCE50 + sizeof(D_800DCE50)','D_800DCE50 + 0x1A0')}
 assert len(result)==10 and all(s!=selected for s in result.values());return result
def expected(c):
 m,calls,obs=p.reference(p.fixture(c),c);s=p.SYMS;values=[m[s['D_800DD190']]];nid=template.nid
 values +=[nid(g.read(m,s['D_800DCE50']+4*i))for i in range(208)]
 for i in range(104):
  at=s['D_8008B4A8']+52*i;cb=g.read(m,at+28);values.append({0:0,g.CB0:1,g.CB1:2}[cb]);values +=[m[at+j]for j in range(52)if not 28<=j<32]
 values +=[nid(g.read(m,s['D_800DD198']+4*i))for i in range(6)]
 for node in g.NODES:values +=[nid(g.read(m,node+8)),*[m[node+j]for j in range(128)if not 8<=j<12]]
 trace=[]
 for(t,a),o in zip(calls,obs):
  if t==p.ENTRY:code,x,y,z=5,a[0],0,a[2]&255
  else:code={g.HELPER:1,g.CLEAN:2,g.CB0:3,g.CB1:4}[t];x=nid(a[0]);y=0 if code==2 else{g.PAYLOAD:0,s['D_800DD190']:1}[a[1]];z=0 if code==2 else a[2]
  trace +=[code,x,y,z,o[0],nid(o[1]),0]
 return template.digest(values),template.digest(trace),len(calls)
def program(selected):
 namespace=dict(template.program.__globals__,root=root,out=out,cases=cases,expected=expected,mutations=mutations,
  body=lambda text,name:'void native_original_wrapper(s32 payload,u8 opcode){subject(2,payload,opcode);}',
  guest=SimpleNamespace(**dict(vars(g),ENTRY=p.ENTRY)))
 render=FunctionType(template.program.__code__,namespace)
 text=render(selected.replace('func_1516944C(','func_15169070('))
 replacements={
  'typedef void(*Subject)(s32,s32,s32,u8);':'typedef void(*Subject)(s32,s32,u8);',
  'hash(&trace,(u32)*ctx.last);':'hash(&trace,0);',
  'record(5,3,4,c->opcode&255);subject(3,4,(s32)data(),(u8)c->opcode);':'record(5,3,0,c->opcode&255);subject(3,(s32)data(),(u8)c->opcode);',
  'if(c->mode&8)D_8008B4A8[*(u8*)p].unk1C=cb1;':'if(c->mode&8)D_8008B4A8[(s32)c->first>=104?103:c->first].unk1C=cb1;',
  'subject((s32)c->first,(s32)c->last,(s32)data(),(u8)c->opcode);':'subject((s32)c->first,(s32)data(),(u8)c->opcode);',
  'struct Matrix{u8 before[16],bytes[832],after[16];};':'struct Matrix{u8 before[16];void *heads[208];u8 after[16];};',
  'struct Node{u8 before[8],bytes[128],after[8];};':'struct Node{u8 before[8];struct{u8 header[8];void *next;u8 tail[116];}fields;u8 after[8];};\n_Static_assert(sizeof(((struct Node*)0)->fields)==128&&__builtin_offsetof(struct Node,fields.next)==16,"typed next storage");',
  'nodes[i].bytes':'((u8 *)&nodes[i].fields)',
 }
 for old,new in replacements.items():assert old in text,old;text=text.replace(old,new)
 needle='for(i=0;i<32;i++)eventBytes[i]'
 assert needle in text
 text=text.replace(needle,'if(!c->empty){u32 col=(s32)c->first>=104?103:c->first;*(void**)(D_800DCE50+4*col)=node(0);*(void**)(D_800DCE50+416+4*col)=node(5);}\n '+needle)
 return text
def main():
 selected=packet.MANIFEST['body'];source=out/'native.c';source.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);command=native_command(opt)+['-fstrict-aliasing','-Wno-unused-variable',str(source),'-o',str(exe)]
  q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,struct.unpack('<II',q.stderr)if len(q.stderr)==8 else q.stderr)
  profiles[opt]=dict(cases=len(cases()),SDK32=True,strict_aliasing=True,UBSan=True,effective_controls=10)
 r=dict(profiles=profiles,full_table_node_and_slot_canaries=True,independent_reference_digests=True,native_columns_nonnegative_and_clamped=True,
  native_depths_bounded=True,guest_homes_and_negative_indices_excluded=True,effective_source_controls=list(mutations(selected)),source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
