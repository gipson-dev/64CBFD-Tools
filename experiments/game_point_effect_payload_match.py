"""Attached-point particle payload: symbolic role closure and complete-image qualification."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-point-effect-payload-15193660-match'
BASELINE='ca4d0c821f391a246d79dd62c5f32c3ec98d094feb4b48678a568a3a4696d673'
LINKED='6ed3289ece934063956b8dfac11c99799e7cb6fd72ae7ed46c5a474784bfb16a'
SPECS=(('func_15193660','generated_1C0B10',0x15193660,0x1C0B10),)
PATCHES=((36, 2357658068, 2357330388), (44, 283115605, 272629845), (48, 14688293, 4202533), (64, 3290431488, 3290562560), (72, 3290562560, 3291348992), (132, 1149263872, 1149239296), (136, 1149267968, 1149263872), (168, 604897313, 1006698496), (172, 604963071, 604897313), (176, 1006698496, 604963071), (328, 3886022776, 3886153848), (332, 3886022768, 3886153840), (336, 3886153860, 3886940292), (340, 3886153852, 3886940284), (364, 3886809184, 3886022752), (368, 3886809196, 3886022764), (372, 3886940276, 3886809204), (376, 3886940288, 3886809216))
GUARDS=((36, 2357658068, 2357330388, (), ()), (44, 283115605, 272629845, (), ()), (48, 14688293, 4202533, (), ()), (64, 3290431488, 3290562560, (('R_MIPS_LO16', 'D_800A81C0'),), (('R_MIPS_LO16', 'D_800A81C0'),)), (72, 3290562560, 3291348992, (('R_MIPS_LO16', 'D_800A81C4'),), (('R_MIPS_LO16', 'D_800A81C4'),)), (132, 1149263872, 1149239296, (), ()), (136, 1149267968, 1149263872, (), ()), (168, 604897313, 1006698496, (), (('R_MIPS_HI16', 'D_800A81E0'),)), (172, 604963071, 604897313, (), ()), (176, 1006698496, 604963071, (('R_MIPS_HI16', 'D_800A81E0'),), ()), (328, 3886022776, 3886153848, (), ()), (332, 3886022768, 3886153840, (), ()), (336, 3886153860, 3886940292, (), ()), (340, 3886153852, 3886940284, (), ()), (364, 3886809184, 3886022752, (), ()), (368, 3886809196, 3886022764, (), ()), (372, 3886940276, 3886809204, (), ()), (376, 3886940288, 3886809216, (), ()))
RAW_SHA='2dc0abcb7bb9b7465c0dc27a06e64724908e7a45cdfda395c10b59e825df5c79'
BINDINGS={52: [('R_MIPS_26', 'func_15142314')], 60: [('R_MIPS_HI16', 'D_800A81C0')], 64: [('R_MIPS_LO16', 'D_800A81C0')], 68: [('R_MIPS_HI16', 'D_800A81C4')], 72: [('R_MIPS_LO16', 'D_800A81C4')], 76: [('R_MIPS_HI16', 'D_800A81C8')], 80: [('R_MIPS_LO16', 'D_800A81C8')], 84: [('R_MIPS_HI16', 'D_800A81CC')], 88: [('R_MIPS_LO16', 'D_800A81CC')], 92: [('R_MIPS_HI16', 'D_800A81D0')], 96: [('R_MIPS_LO16', 'D_800A81D0')], 100: [('R_MIPS_HI16', 'D_800A81D4')], 104: [('R_MIPS_LO16', 'D_800A81D4')], 108: [('R_MIPS_HI16', 'D_800A81D8')], 112: [('R_MIPS_LO16', 'D_800A81D8')], 120: [('R_MIPS_HI16', 'D_800A81DC')], 124: [('R_MIPS_LO16', 'D_800A81DC')], 176: [('R_MIPS_HI16', 'D_800A81E0')], 184: [('R_MIPS_LO16', 'D_800A81E0')], 380: [('R_MIPS_26', 'func_15152520')]}
ORIGINAL_BINDINGS={52: [('R_MIPS_26', 'func_15142314')], 60: [('R_MIPS_HI16', 'D_800A81C0')], 64: [('R_MIPS_LO16', 'D_800A81C0')], 68: [('R_MIPS_HI16', 'D_800A81C4')], 72: [('R_MIPS_LO16', 'D_800A81C4')], 76: [('R_MIPS_HI16', 'D_800A81C8')], 80: [('R_MIPS_LO16', 'D_800A81C8')], 84: [('R_MIPS_HI16', 'D_800A81CC')], 88: [('R_MIPS_LO16', 'D_800A81CC')], 92: [('R_MIPS_HI16', 'D_800A81D0')], 96: [('R_MIPS_LO16', 'D_800A81D0')], 100: [('R_MIPS_HI16', 'D_800A81D4')], 104: [('R_MIPS_LO16', 'D_800A81D4')], 108: [('R_MIPS_HI16', 'D_800A81D8')], 112: [('R_MIPS_LO16', 'D_800A81D8')], 120: [('R_MIPS_HI16', 'D_800A81DC')], 124: [('R_MIPS_LO16', 'D_800A81DC')], 168: [('R_MIPS_HI16', 'D_800A81E0')], 184: [('R_MIPS_LO16', 'D_800A81E0')], 380: [('R_MIPS_26', 'func_15152520')]}
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
    if len(raw)!=404 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Point effect payload payload or bindings changed')
    return raw,bindings

def normalized(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw);refs={k:list(v)for k,v in bindings.items()}
    for at,before,after,old,new in GUARDS:
        if struct.unpack_from('>I',out,at)[0]!=before or refs.get(at,[])!=list(old):raise ValueError('Point payload guard or relocation changed')
        struct.pack_into('>I',out,at,after)
        refs.pop(at,None)
        if new:refs[at]=list(new)
    if refs!=ORIGINAL_BINDINGS:raise ValueError('Point payload normalized binding set differs')
    return bytes(out),refs


def recovered_owner(before,target):
    function,owner,entry,rom=SPECS[target];lo,hi=function_span(before,function)
    if before[lo:hi]!='s32 '+function+'() {\n    return 0;\n}':raise ValueError('Point effect payload predecessor changed')
    return before[:lo]+HEADERS.replace('#include <ultra64.h>\n','')+'/* Resolve attached point 10 and submit its live particle parameters after validating the owner. */\n'+SELECTED.replace(SPECS[0][0],function).rstrip()+before[hi:]

def snapshot(output):
    index=(output/'input-snapshot.json').read_bytes()
    if sha(index)!=SNAPSHOT_SHA:raise ValueError('Point effect payload snapshot index changed')
    values={}
    for name,wanted in json.loads(index)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(data)!=wanted:raise ValueError('Point effect payload frozen input changed: '+name)
        values[name]=data
    return values

def verify_prepared(output):
    index=(output/'prepared-artifacts.json').read_bytes()
    if sha(index)!=ARTIFACT_SHA:raise ValueError('Point effect payload preparation index changed')
    for name,wanted in json.loads(index).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Point effect payload preparation changed: '+name)
    return True

def predict(before,rom):
    if sha(before)!=BASELINE:raise ValueError('Point effect payload image predecessor changed')
    out=bytearray(before)
    for function,owner,entry,offset in SPECS:
        row,=[r for r in symbol_rows(before)if r[1]==function]
        if row[2][1:3]!=(entry,12):raise ValueError('Point effect payload predecessor extent changed')
        truth=rom[offset:offset+404]
        if len(truth)!=404:raise ValueError('Point effect payload retail slot missing')
        at=elf_slot_offset(before,entry,404);out[at:at+404]=truth;struct.pack_into('>I',out,row[0]+8,404)
    reorder_metadata(before,out)
    return bytes(out)

def check_image(before,actual,rom):
    if actual!=predict(before,rom):raise ValueError('Point effect payload entire image differs')

def expected_map(output):
    data=(output/'private-joint-linked.map').read_bytes()
    for _,owner,_,_ in SPECS:
        private=(BUILD.removeprefix('conker/')+'/make-shadow-'+owner+'/src/game/'+owner+'.c.o').encode()
        if data.count(private)!=9:raise ValueError('Point effect payload map owner count changed')
        data=data.replace(private,('build/src/game/'+owner+'.c.o').encode())
    private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
    if data.count(private)!=1:raise ValueError('Point effect payload map output changed')
    return data.replace(private,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:
        for i,(_,owner,_,_)in enumerate(SPECS):
            name='conker/src/game/'+owner+'.c';changes[name]=recovered_owner(values[name].decode(),i).encode()
            changes['conker/build/src/game/'+owner+'.c.o']=(output/('qualified-'+owner+'.o')).read_bytes()
        changes.update({'conker/retail_word_patches.us.csv':(output/'proposed-guards.csv').read_bytes(),
            'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin']),
            'conker/build/conker.us.map':expected_map(output)})
    for name,data in values.items():
        if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Point effect payload live input changed: '+name)
    return values

def audit(root,output,installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output);values=check_inputs(root,output,installed)
    elf=root/'conker/build/conker.us.elf'if installed else output/'private-joint-linked.elf'
    actual=elf.read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'])
    if sha(actual)!=LINKED:raise ValueError('Point effect payload linked image changed')
    data=audit_layout(elf,root/'conker')
    if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Point effect payload protected data changed')
    targets={v[0]for v in SPECS};expected=Counter((n,f[1],404 if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
    if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Point effect payload named definition changed')
    q=json.loads((output/'private-owner-image-v14.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
    if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
    return q

METADATA_GROUPS=((2739368, ('D_800A81DC', 'D_8009626C'), (1, 0)), (2807368, ('D_800A81D0', 'D_80096260', 'D_80089158'), (1, 2, 0)), (2819192, ('D_800A81D4', 'D_80096264', 'D_8008FF80', 'D_80086B80'), (1, 2, 3, 0)), (2822120, ('D_800A81D8', 'D_80096268'), (1, 0)), (2880632, ('D_800A81CC', 'D_8009625C'), (1, 0)), (2898040, ('D_800A81C4', 'D_80096254'), (1, 0)), (2900696, ('D_800A81C0', 'D_80096250'), (1, 0)), (2908568, ('D_800A81C8', 'D_80096258'), (1, 0)), (2997896, ('D_800A81E0', 'D_8009FB40', 'D_80096270'), (1, 2, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Point effect payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Point effect payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Point effect payload metadata length changed')

"""Symbolic closure of every ordered read, store, branch and helper argument."""

def prove_roles(raw,original,raw_refs,original_refs,patches):
 a=struct.unpack('>101I',raw);b=struct.unpack('>101I',original)
 assert tuple((i*4,x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y)==tuple(tuple(p[:3])for p in patches)
 def add(value,n):
  if isinstance(value,int):return(value+n)&0xFFFFFFFF
  if isinstance(value,tuple)and value[0]=='add':return('add',value[1],value[2]+n)
  return value if not n else('add',value,n)
 def run(code,refs):
  r=[('initial-GPR',i)for i in range(32)];r[0]=0
  f=[('initial-FP',i)for i in range(32)];events=[];calls=[];pending=None
  for i,w in enumerate(code):
   pc=i*4;op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;imm=((w&65535)^32768)-32768;binding=refs.get(pc,[])
   if op==9:r[rt]=add(r[rs],imm)
   elif op==15:r[rt]=('HI',binding[0][1])if binding else(w&65535)<<16
   elif op==0 and fn==37:r[rd]=r[rs]if r[rt]==0 else r[rt]if r[rs]==0 else('or',r[rs],r[rt])
   elif op in(35,36,49):
    n=1 if op==36 else 4
    if binding:
     assert binding[0][0]=='R_MIPS_LO16'and r[rs]==('HI',binding[0][1]);address=('global',binding[0][1])
    else:address=add(r[rs],imm)
    value=('read',len(events),address,n);events.append(('R',address,n))
    if op==49:f[rt]=value
    else:r[rt]=value
   elif op in(40,41,43,57):
    n={40:1,41:2,43:4,57:4}[op];value=f[rt]if op==57 else r[rt]
    events.append(('W',add(r[rs],imm),n,('low',value,n)if n<4 else value))
   elif op==17 and rs==4:f[rd]=r[rt]
   elif op in(4,20):events.append(('BEQ',pc,pc+4+4*imm,r[rs],r[rt],op==20))
   elif op==3:
    assert len(binding)==1 and binding[0][0]=='R_MIPS_26';pending=(pc,binding[0][1]);r[31]=('return',pc+8)
   elif op==0 and fn==8:events.append(('return',r[rs]))
   else:assert w==0,(pc,hex(w))
   r[0]=0
   if pending and pc==pending[0]+4:
    callpc,name=pending;calls.append((callpc,name,tuple(r[4:7])));events.append(('CALL',name,tuple(r[4:7])))
    for reg in(1,2,3,*range(4,16),24,25):r[reg]=('call-GPR',callpc,reg)
    for reg in range(20):f[reg]=('call-FP',callpc,reg)
    pending=None
  return events,calls,[r[i]for i in(*range(16,24),28,29,30,31)],f[20:]
 first=run(a,raw_refs);second=run(b,original_refs);assert first==second
 assert [c[0]for c in first[1]]==[52,380]
 assert [c[1]for c in first[1]]==['func_15142314','func_15152520']
 assert first[3]==[('initial-FP',i)for i in range(20,32)]
 return dict(success=True,ordered_observations=len(first[0]),helper_call_offsets=[52,380],all_read_store_addresses_and_values_equal=True,all_branch_predicates_equal=True,all_helper_arguments_equal=True,callee_saved_roles_equal=True,caller_clobbered_scratch_not_equated=True,FP_bitcopy_no_arithmetic=True)

HEADERS='#include <ultra64.h>\ntypedef struct {\n s32 baseCount, countRange;\n f32 position[3];\n s16 field14,field16,field18,field1A;\n f32 parameters[5];\n s16 field30,field32;\n s32 field34,field38,field3C;\n f32 values[10];\n u8 colors[8];\n u8 field70,field71;\n s16 field72,field74;\n u8 padding76[2];\n} PointEffectPayload;\nvoid func_15142314(u8 *,s32,f32 *);\nvoid func_15152520(PointEffectPayload *,u8,s32);\nextern f32 D_800A81C0;\nextern f32 D_800A81C4;\nextern f32 D_800A81C8;\nextern f32 D_800A81CC;\nextern f32 D_800A81D0;\nextern f32 D_800A81D4;\nextern f32 D_800A81D8;\nextern f32 D_800A81DC;\nextern f32 D_800A81E0;\n'
SELECTED='void func_15193660(u8 *owner, s32 mode, s32 extra) {\n    PointEffectPayload payload;\n    u8 *attached;\n    if (owner != 0 && *(u32 *)owner != 0) {\n        attached = *(u8 **)(owner + 0x1D4);\n        if (attached != 0) {\n            func_15142314(attached, 10, payload.position);\n            payload.baseCount = 8;\n            payload.countRange = 7;\n            payload.values[6] = D_800A81C0;\n            payload.values[4] = D_800A81C0;\n            payload.values[9] = D_800A81C4;\n            payload.values[7] = D_800A81C4;\n            payload.parameters[0] = D_800A81C8;\n            payload.field14 = 0;\n            payload.field16 = 255;\n            payload.field18 = -33;\n            payload.field1A = 24;\n            payload.field30 = 40;\n            payload.field32 = 35;\n            payload.field34 = 160;\n            payload.field38 = 19;\n            payload.field3C = 0;\n            payload.field70 = 33;\n            payload.colors[0] = 255;\n            payload.colors[1] = 255;\n            payload.colors[2] = 255;\n            payload.colors[3] = 255;\n            payload.colors[4] = 255;\n            payload.colors[5] = 255;\n            payload.colors[6] = 255;\n            payload.colors[7] = 255;\n            payload.field71 = 15;\n            payload.field72 = 25;\n            payload.field74 = 10;\n            payload.parameters[1] = D_800A81CC;\n            payload.parameters[2] = D_800A81D0;\n            payload.parameters[3] = D_800A81D4;\n            payload.parameters[4] = D_800A81D8;\n            payload.values[1] = D_800A81DC;\n            payload.values[0] = 0;\n            payload.values[3] = 0;\n            payload.values[5] = 0.0f;\n            payload.values[8] = 0.0f;\n            payload.values[2] = D_800A81E0;\n            func_15152520(&payload, (u8)mode, extra);\n        }\n    }\n}\n'
SNAPSHOT_SHA='e4a551ee65d9b2a8860cdd85be35cf99b4f7b391218cd11c42f350858f6076a7'
ARTIFACT_SHA='2ba368a040a6b796ba3017feda406c88af8b08cadb336073e1d41fbed9142e62'
