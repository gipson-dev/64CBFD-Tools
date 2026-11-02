"""Particle factory: complete scratch layout, ordered helpers and full-image qualification."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-particle-factory-15152520-match'
BASELINE='6ed3289ece934063956b8dfac11c99799e7cb6fd72ae7ed46c5a474784bfb16a'
LINKED='6ae9f23a08f217174eaf205953426224966321f4d8769900dfd599bb7417dd4e'
SPECS=(('func_15152520','generated_17CAF0',0x15152520,0x17F9D0),)
PATCHES=((64, 2745172192, 2745172188), (88, 2746155176, 2746155172), (92, 2745172137, 2745172133), (96, 2746745002, 2746744998), (100, 2746810539, 2746810535), (104, 2745696428, 2745696424), (120, 2947088560, 2947088556), (156, 2947219660, 2947219656), (160, 2947285200, 2947285196), (164, 2946498744, 2946498740), (168, 2947350716, 2947350712), (172, 2947416256, 2947416252), (176, 2745172180, 2745172176), (180, 2746155221, 2746155217), (184, 2948071620, 2948071616), (188, 2948137160, 2948137156), (192, 2946498788, 2946498784), (196, 2745172200, 2745172196), (200, 2745696489, 2745696485), (204, 2947154100, 2947154096), (212, 665387244, 665387240), (216, 665649368, 665649364), (228, 666435804, 666435800), (248, 3886284960, 3886284956), (288, 2812870908, 2812870904), (296, 2813067518, 2813067514), (308, 2746155172, 2746155168), (320, 666108072, 1006715828), (352, 1006715828, 666239088), (360, 666239092, 666173604), (368, 666173572, 666108032), (416, 2813067438, 2813067434), (436, 3886415988, 3886415984), (448, 3886547064, 3886547060), (460, 3886678140, 3886678136), (464, 3323068492, 3322937420), (468, 3322937416, 3322150984), (472, 1175585026, 1175454850), (476, 1174700416, 1174704512), (484, 3886416000, 3886415996), (512, 3322544160, 3322413088), (532, 1175061634, 1174930050), (540, 3322413084, 3322937372), (552, 1175602176, 1175475328), (580, 1141276672, 1141280768), (620, 44054565, 41957413), (632, 3322282076, 3322151004), (636, 3322150992, 3322413136), (640, 1174798978, 1174667650), (644, 1175069184, 1174942336), (652, 3886547088, 3886678156), (660, 3323068500, 3322150996), (664, 1175454082, 1175454850), (668, 1174835456, 1174704512), (676, 3886284948, 3886416016), (684, 3322544216, 3322937432), (688, 1174930434, 1174930050), (700, 3887202456, 3887202452), (708, 3322282024, 3322413096), (712, 1174667778, 1174667650), (724, 3886678172, 3886678168), (728, 3323068484, 3322937412), (732, 3322937408, 3322150976), (740, 1175585026, 1175454850), (764, 41951269, 44048421), (768, 1174700416, 1174704512))
GUARDS=((64, 2745172192, 2745172188, (), ()), (88, 2746155176, 2746155172, (), ()), (92, 2745172137, 2745172133, (), ()), (96, 2746745002, 2746744998, (), ()), (100, 2746810539, 2746810535, (), ()), (104, 2745696428, 2745696424, (), ()), (120, 2947088560, 2947088556, (), ()), (156, 2947219660, 2947219656, (), ()), (160, 2947285200, 2947285196, (), ()), (164, 2946498744, 2946498740, (), ()), (168, 2947350716, 2947350712, (), ()), (172, 2947416256, 2947416252, (), ()), (176, 2745172180, 2745172176, (), ()), (180, 2746155221, 2746155217, (), ()), (184, 2948071620, 2948071616, (), ()), (188, 2948137160, 2948137156, (), ()), (192, 2946498788, 2946498784, (), ()), (196, 2745172200, 2745172196, (), ()), (200, 2745696489, 2745696485, (), ()), (204, 2947154100, 2947154096, (), ()), (212, 665387244, 665387240, (), ()), (216, 665649368, 665649364, (), ()), (228, 666435804, 666435800, (), ()), (248, 3886284960, 3886284956, (), ()), (288, 2812870908, 2812870904, (), ()), (296, 2813067518, 2813067514, (), ()), (308, 2746155172, 2746155168, (), ()), (320, 666108072, 1006715828, (), ()), (352, 1006715828, 666239088, (), ()), (360, 666239092, 666173604, (), ()), (368, 666173572, 666108032, (), ()), (416, 2813067438, 2813067434, (), ()), (436, 3886415988, 3886415984, (), ()), (448, 3886547064, 3886547060, (), ()), (460, 3886678140, 3886678136, (), ()), (464, 3323068492, 3322937420, (), ()), (468, 3322937416, 3322150984, (), ()), (472, 1175585026, 1175454850, (), ()), (476, 1174700416, 1174704512, (), ()), (484, 3886416000, 3886415996, (), ()), (512, 3322544160, 3322413088, (), ()), (532, 1175061634, 1174930050, (), ()), (540, 3322413084, 3322937372, (), ()), (552, 1175602176, 1175475328, (), ()), (580, 1141276672, 1141280768, (), ()), (620, 44054565, 41957413, (), ()), (632, 3322282076, 3322151004, (), ()), (636, 3322150992, 3322413136, (), ()), (640, 1174798978, 1174667650, (), ()), (644, 1175069184, 1174942336, (), ()), (652, 3886547088, 3886678156, (), ()), (660, 3323068500, 3322150996, (), ()), (664, 1175454082, 1175454850, (), ()), (668, 1174835456, 1174704512, (), ()), (676, 3886284948, 3886416016, (), ()), (684, 3322544216, 3322937432, (), ()), (688, 1174930434, 1174930050, (), ()), (700, 3887202456, 3887202452, (), ()), (708, 3322282024, 3322413096, (), ()), (712, 1174667778, 1174667650, (), ()), (724, 3886678172, 3886678168, (), ()), (728, 3323068484, 3322937412, (), ()), (732, 3322937408, 3322150976, (), ()), (740, 1175585026, 1175454850, (), ()), (764, 41951269, 44048421, (), ()), (768, 1174700416, 1174704512, (), ()))
RAW_SHA='b93dae5d275ed5c49b0cea927bb1c02c75d4230e095dac75f6715e6b2a27eda7'
BINDINGS={304: [('R_MIPS_26', 'func_150ADA20')], 372: [('R_MIPS_26', 'func_150ADA20')], 420: [('R_MIPS_26', 'func_150ADA68')], 432: [('R_MIPS_26', 'func_150ADA68')], 444: [('R_MIPS_26', 'func_150ADA68')], 456: [('R_MIPS_26', 'func_150ADA68')], 480: [('R_MIPS_26', 'func_150ADA20')], 488: [('R_MIPS_26', 'func_150ADA20')], 496: [('R_MIPS_26', 'func_150ADA68')], 616: [('R_MIPS_26', 'func_15143794')], 624: [('R_MIPS_26', 'func_150ADA68')], 648: [('R_MIPS_26', 'func_150ADA68')], 672: [('R_MIPS_26', 'func_150ADA68')], 696: [('R_MIPS_26', 'func_150ADA68')], 720: [('R_MIPS_26', 'func_150ADA68')], 780: [('R_MIPS_26', 'func_15157898')]}
ORIGINAL_BINDINGS={304: [('R_MIPS_26', 'func_150ADA20')], 372: [('R_MIPS_26', 'func_150ADA20')], 420: [('R_MIPS_26', 'func_150ADA68')], 432: [('R_MIPS_26', 'func_150ADA68')], 444: [('R_MIPS_26', 'func_150ADA68')], 456: [('R_MIPS_26', 'func_150ADA68')], 480: [('R_MIPS_26', 'func_150ADA20')], 488: [('R_MIPS_26', 'func_150ADA20')], 496: [('R_MIPS_26', 'func_150ADA68')], 616: [('R_MIPS_26', 'func_15143794')], 624: [('R_MIPS_26', 'func_150ADA68')], 648: [('R_MIPS_26', 'func_150ADA68')], 672: [('R_MIPS_26', 'func_150ADA68')], 696: [('R_MIPS_26', 'func_150ADA68')], 720: [('R_MIPS_26', 'func_150ADA68')], 780: [('R_MIPS_26', 'func_15157898')]}
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
    if len(raw)!=852 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Particle factory payload or bindings changed')
    return raw,bindings

def normalized(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw);refs={k:list(v)for k,v in bindings.items()}
    for at,before,after,old,new in GUARDS:
        if struct.unpack_from('>I',out,at)[0]!=before or refs.get(at,[])!=list(old):raise ValueError('Particle factory guard or relocation changed')
        struct.pack_into('>I',out,at,after)
        refs.pop(at,None)
        if new:refs[at]=list(new)
    if refs!=ORIGINAL_BINDINGS:raise ValueError('Particle factory normalized binding set differs')
    return bytes(out),refs


def recovered_owner(before,target):
    function,owner,entry,rom=SPECS[target];lo,hi=function_span(before,function)
    if before[lo:hi]!='s32 '+function+'() {\n    return 0;\n}':raise ValueError('Particle factory predecessor changed')
    return before[:lo]+HEADERS.replace('#include <ultra64.h>\n','')+'/* Emit randomized particles from live input fields using one contiguous spawn scratch object. */\n'+SELECTED.replace(SPECS[0][0],function).rstrip()+before[hi:]

def snapshot(output):
    index=(output/'input-snapshot.json').read_bytes()
    if sha(index)!=SNAPSHOT_SHA:raise ValueError('Particle factory snapshot index changed')
    values={}
    for name,wanted in json.loads(index)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(data)!=wanted:raise ValueError('Particle factory frozen input changed: '+name)
        values[name]=data
    return values

def verify_prepared(output):
    index=(output/'prepared-artifacts.json').read_bytes()
    if sha(index)!=ARTIFACT_SHA:raise ValueError('Particle factory preparation index changed')
    for name,wanted in json.loads(index).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Particle factory preparation changed: '+name)
    return True

def predict(before,rom):
    if sha(before)!=BASELINE:raise ValueError('Particle factory image predecessor changed')
    out=bytearray(before)
    for function,owner,entry,offset in SPECS:
        row,=[r for r in symbol_rows(before)if r[1]==function]
        if row[2][1:3]!=(entry,12):raise ValueError('Particle factory predecessor extent changed')
        truth=rom[offset:offset+852]
        if len(truth)!=852:raise ValueError('Particle factory retail slot missing')
        at=elf_slot_offset(before,entry,852);out[at:at+852]=truth;struct.pack_into('>I',out,row[0]+8,852)
    reorder_metadata(before,out)
    return bytes(out)

def check_image(before,actual,rom):
    if actual!=predict(before,rom):raise ValueError('Particle factory entire image differs')

def expected_map(output):
    data=(output/'private-joint-linked.map').read_bytes()
    for _,owner,_,_ in SPECS:
        private=(BUILD.removeprefix('conker/')+'/make-shadow-'+owner+'/src/game/'+owner+'.c.o').encode()
        if data.count(private)!=9:raise ValueError('Particle factory map owner count changed')
        data=data.replace(private,('build/src/game/'+owner+'.c.o').encode())
    private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
    if data.count(private)!=1:raise ValueError('Particle factory map output changed')
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
        if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Particle factory live input changed: '+name)
    return values

def audit(root,output,installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output);values=check_inputs(root,output,installed)
    elf=root/'conker/build/conker.us.elf'if installed else output/'private-joint-linked.elf'
    actual=elf.read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'])
    if sha(actual)!=LINKED:raise ValueError('Particle factory linked image changed')
    data=audit_layout(elf,root/'conker')
    if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Particle factory protected data changed')
    targets={v[0]for v in SPECS};expected=Counter((n,f[1],852 if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
    if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Particle factory named definition changed')
    q=json.loads((output/'private-owner-image-v15.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
    if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
    return q

METADATA_GROUPS=()

def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Particle factory named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Particle factory symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Particle factory metadata length changed')


"""Complete scratch relocation and finite FP-role proof for the complete factory."""
import struct

def prove(raw,original,refs,original_refs):
 a=struct.unpack('>213I',raw);b=struct.unpack('>213I',original)
 assert refs==original_refs
 differences=tuple((i*4,x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y)
 assert len(differences)==66
 def u(v):return v&0xFFFFFFFF
 def add(v,n):
  if isinstance(v,int):return u(v+n)
  if v[0]=='SP':return('SP',v[1]+n)
  return('add32',v,n)
 def low(v,n):return v&((1<<(n*8))-1)if isinstance(v,int)else('low',v,n)
 def fp(op,left,right):return(op,*sorted((left,right),key=repr))
 def run(code,is_raw):
  r=[('initial-GPR',i)for i in range(32)];r[0]=0;r[29]=('SP',0)
  f=[('initial-FP',i)for i in range(32)];events=[];calls=[];pending=None;hi=lo=('initial-HILO',);low_edge=0;branches=[]
  start=-140 if is_raw else -144
  def address(value):
   if isinstance(value,tuple)and value[0]=='SP'and start<=value[1]<start+140:return('scratch',value[1]-start)
   return value
  def read(at,n):
   at=address(at);v=('read',len(events),at,n);events.append(('R',at,n));return v
  def write(at,v,n):events.append(('W',address(at),n,low(v,n)if n<4 else v))
  for i,w in enumerate(code):
   pc=i*4;op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;imm=((w&65535)^32768)-32768
   if op==9:r[rt]=add(r[rs],imm)
   elif op==15:r[rt]=(w&65535)<<16
   elif op==12:r[rt]=('and32',r[rs],w&65535)
   elif op==13:r[rt]=u(r[rs]|(w&65535))if isinstance(r[rs],int)else('or32',r[rs],w&65535)
   elif op==0 and fn==37:r[rd]=r[rs]if r[rt]==0 else r[rt]if r[rs]==0 else('or32',r[rs],r[rt])
   elif op==0 and fn==33:r[rd]=('uadd32',*sorted((r[rs],r[rt]),key=repr))
   elif op==0 and fn in(0,3):
    shift=w>>6&31
    if w:r[rd]=('sll32'if fn==0 else'sra32',r[rt],shift)
   elif op==0 and fn==27:lo=('udiv32',r[rs],r[rt]);hi=('umod32',r[rs],r[rt])
   elif op==0 and fn==16:r[rd]=hi
   elif op in(35,36,33,49):
    n=1 if op==36 else 2 if op==33 else 4;v=read(add(r[rs],imm),n)
    if op==49:f[rt]=v
    else:r[rt]=('sext16',v)if op==33 else v
   elif op in(40,41,43,57):write(add(r[rs],imm),f[rt]if op==57 else r[rt],{40:1,41:2,43:4,57:4}[op])
   elif op in(34,38):
    # Both color words are aligned for a valid typed input; both pair reads remain visible.
    at=add(r[rs],imm-(3 if op==38 else 0));r[rt]=read(at,4)
   elif op in(42,46):write(add(r[rs],imm-(3 if op==46 else 0)),r[rt],4)
   elif op==61:write(add(r[rs],imm),('pair',f[rt],f[rt+1]),8)
   elif op==53:
    value=read(add(r[rs],imm),8);f[rt]=('upper',value);f[rt+1]=('lower',value)
   elif op==17:
    fs=w>>11&31;fd=w>>6&31
    if rs==4:f[fs]=r[rt]
    elif rs==0:r[rt]=f[fs]
    else:
     assert rs==16 and fn in(0,2),(pc,hex(w));f[fd]=fp('add32'if fn==0 else'mul32',f[fs],f[rt])
   elif op in(4,5):branches.append((pc,op,r[rs],r[rt],pc+4+4*imm));events.append(('branch',pc,op,r[rs],r[rt],pc+4+4*imm))
   elif op==0 and fn==13:events.append(('unreachable-divisor-trap',pc))
   elif op==3:
    binding=refs.get(pc);assert binding and len(binding)==1;pending=(pc,binding[0][1]);r[31]=('return',pc+8)
   elif op==0 and fn==8:events.append(('return',r[rs]))
   else:raise AssertionError((pc,hex(w)))
   r[0]=0
   if pending and pc==pending[0]+4:
    callpc,name=pending;count={'func_150ADA20':0,'func_150ADA68':0,'func_15143794':4,'func_15157898':9}[name]
    args=list(r[4:4+min(count,4)])
    # Outgoing stack writes are checked as ordered observations independently.
    pointer_positions={'func_15143794':(3,),'func_15157898':(0,1)}.get(name,())
    for at in pointer_positions:args[at]=address(args[at])
    calls.append((callpc,name,tuple(args),count));events.append(('call',callpc,name,tuple(args),count))
    for reg in(1,2,3,*range(4,16),24,25):r[reg]=('call-GPR',callpc,reg)
    for reg in range(20):f[reg]=('call-FP',callpc,reg)
    pending=None
  return events,calls,branches,r[16:24]+[r[28],r[29],r[30],r[31]],f[20:]
 first=run(a,True);second=run(b,False)
 assert first==second,'Private-layout symbolic closure differs'
 assert len(first[1])==16 and len(first[2])==6
 return dict(success=True,words=213,frame=256,guards=66,ordered_observations=len(first[0]),call_sites=len(first[1]),branch_sites=len(first[2]),private_scratch_bytes=140,raw_private_shift=4,all_ordered_accesses_calls_branches_and_saved_roles_equal=True,finite_FP_domain_required=True,commutative_FP_order_only=True,no_frame_or_instruction_count_change=True,loop_body_and_backedge_closed=True,raw_undefined_padding_requires_corresponding_scratch_seed=True)

HEADERS='#include <ultra64.h>\ntypedef struct {\n    s32 baseCount, countRange;\n    f32 position[3];\n    s16 field14, field16, field18, field1A;\n    f32 parameters[5];\n    s16 lifetimeBase, lifetimeRange;\n    s32 field34, field38, field3C;\n    f32 values[10];\n    u8 colors[8];\n    u8 field70, field71;\n    s16 field72, field74;\n    u8 padding76[2];\n} ParticleFactoryInput;\ntypedef struct { u8 r, g, b, a; } ParticleColor;\ntypedef struct { f32 x, y, z; } ParticlePosition;\ntypedef struct {\n    u8 flags, field1, field2;\n    s8 field3, field4;\n    u8 padding5;\n    s16 lifetime;\n    s32 field8, fieldC, field10;\n    u32 field14, field18;\n    s32 field1C, field20, field24, field28;\n    u8 field2C, field2D, padding2E[2];\n    ParticleColor colors[2];\n    u8 field38, padding39[3];\n    s32 field3C;\n    u8 field40, field41, padding42[2];\n    ParticlePosition position;\n    u8 padding50[4];\n    s16 field54, field56;\n} ParticleSpawnDescriptor;\ntypedef struct {\n    f32 rotation[3];\n    f32 fieldC;\n    f32 direction[3];\n    f32 velocity[3];\n    f32 field28, field2C;\n    u8 property, padding31[3];\n} ParticleSpawnState;\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143794(s16, s16, f32, f32 *);\ns32 func_15157898(s32, void *, s32, f32,\n                  s32, s32, u8 *, u8, s32);\n\n/* Spawn copies state plus the descriptor first word from this complete object. */\ntypedef struct { ParticleSpawnState state; ParticleSpawnDescriptor descriptor; } ParticleSpawnScratch;\n'
SELECTED='void func_15152520(ParticleFactoryInput *input, u8 mode, s32 extra) {\n    ParticleSpawnScratch scratch;\n    u32 remaining;\n    u32 first;\n    u32 second;\n\n    scratch.descriptor.field38 = 0;\n    scratch.descriptor.flags = input->field70 | 2;\n    scratch.descriptor.field1 = 0;\n    scratch.descriptor.field2 = 1;\n    scratch.descriptor.field3 = -1;\n    scratch.descriptor.field4 = -1;\n    scratch.descriptor.field8 = input->field34;\n    scratch.descriptor.fieldC = input->field38;\n    scratch.descriptor.field24 = 128;\n    scratch.descriptor.field28 = 32;\n    scratch.descriptor.field10 = 0;\n    scratch.descriptor.field14 = 0x220405;\n    scratch.descriptor.field18 = 0x40200;\n    scratch.descriptor.field2C = 0;\n    scratch.descriptor.field2D = 8;\n    scratch.descriptor.field1C = 1;\n    scratch.descriptor.field20 = 0x38;\n    scratch.descriptor.field3C = 0;\n    scratch.descriptor.field40 = 0;\n    scratch.descriptor.field41 = 2;\n    scratch.descriptor.position = *(ParticlePosition *)input->position;\n    scratch.state.field2C = input->parameters[2];\n    scratch.descriptor.colors[0] = *(ParticleColor *)&input->colors[0];\n    scratch.descriptor.colors[1] = *(ParticleColor *)&input->colors[4];\n    scratch.descriptor.field54 = input->field72;\n    scratch.descriptor.field56 = input->field74;\n    scratch.state.property = input->field71;\n    remaining = (u32)func_150ADA20();\n    remaining = remaining % ((u32)input->countRange + 1U) + (u32)input->baseCount;\n    while (remaining != 0) {\n        first = (u32)func_150ADA20();\n        scratch.descriptor.lifetime = (s16)(first % (u32)(input->lifetimeRange + 1) + input->lifetimeBase);\n        scratch.state.rotation[0] = func_150ADA68() * 360.0f;\n        scratch.state.rotation[1] = func_150ADA68() * 360.0f;\n        scratch.state.rotation[2] = func_150ADA68() * 360.0f;\n        scratch.state.fieldC = func_150ADA68() * input->values[3] + input->values[2];\n        first = (u32)func_150ADA20();\n        second = (u32)func_150ADA20();\n        func_15143794((s16)(first % (u32)(input->field16 + 1) + input->field14),\n                      (s16)(second % (u32)(input->field1A + 1) + input->field18),\n                      func_150ADA68() * input->parameters[1] + input->parameters[0], scratch.state.direction);\n        scratch.state.velocity[0] = func_150ADA68() * input->values[7] + input->values[4];\n        scratch.state.velocity[1] = func_150ADA68() * input->values[8] + input->values[5];\n        scratch.state.velocity[2] = func_150ADA68() * input->values[9] + input->values[6];\n        scratch.state.field28 = func_150ADA68() * input->parameters[4] + input->parameters[3];\n        func_15157898((s32)&scratch.descriptor, &scratch, input->field3C, func_150ADA68() * input->values[1] + input->values[0], 0, 0, 0, (u8)mode, extra);\n        remaining--;\n    }\n}\n'
SNAPSHOT_SHA='687c386e7b327aa52cb89274a1187bea96fdd9793e439cd56a257fe7a4a4311b'
ARTIFACT_SHA='76512495260ac0d964d8748315148c8f84685f9a62db053ea578bbbe468ee0e5'
