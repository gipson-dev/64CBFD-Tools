"""Random basis position: live sampling, ordered aliases and complete-image closure."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-random-basis-position-1514F808-match'
BASELINE='50a5fd84eaff7f7f4bb61300e1ff9200987ba37e6fc4a6fcde83140f71748416'
LINKED='40b181d8e957f4afd4d70bab07dabb3874995809488ad1b40ae99a63001a12f4'
SPECS=(('func_1514F808','generated_17CAF0',0x1514F808,0x17CCB8),)
PATCHES=((52, 1174413698, 1174667650), (124, 1174951040, 1175078016), (148, 3322413088, 3322544160), (152, 1174831746, 1174831618), (160, 1175601410, 1175605506), (164, 1174688768, 1174684672), (168, 1175466496, 1174831744), (172, 1174422658, 1174426754), (184, 3322544152, 3322413080), (188, 3349676076, 3349807148), (192, 3322937380, 3322282020), (196, 1174688130, 1174684674), (204, 1174963330, 1175073922), (208, 1175597696, 1175618048), (212, 1175069696, 1174684032), (216, 1174438402, 1174418050), (220, 3829923848, 3830054920))
RAW_SHA='5e5525a4a3c923eee0f9c5a106d417674cf5adf926201306a71ba664598d3e3e'
BINDINGS={24:[('R_MIPS_26','func_150ADA20')],32:[('R_MIPS_26','func_150ADA68')],76:[('R_MIPS_26','func_15143874')]}
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
    if len(raw)!=240 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Random basis position payload or bindings changed')
    return raw,bindings

def normalized(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for at,before,after in PATCHES:
        if struct.unpack_from('>I',out,at)[0]!=before:raise ValueError('Random basis position spill guard changed')
        struct.pack_into('>I',out,at,after)
    return bytes(out),bindings

def recovered_owner(before,target):
    function,owner,entry,rom=SPECS[target];lo,hi=function_span(before,function)
    if before[lo:hi]!='s32 '+function+'() {\n    return 0;\n}':raise ValueError('Random basis position predecessor changed')
    return before[:lo]+HEADERS.replace('#include <ultra64.h>\n','')+'/* Sample a radial point and transform its three components through the live basis. */\n'+SELECTED.replace(SPECS[0][0],function).rstrip()+before[hi:]

def snapshot(output):
    index=(output/'input-snapshot.json').read_bytes()
    if sha(index)!=SNAPSHOT_SHA:raise ValueError('Random basis position snapshot index changed')
    values={}
    for name,wanted in json.loads(index)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(data)!=wanted:raise ValueError('Random basis position frozen input changed: '+name)
        values[name]=data
    return values

def verify_prepared(output):
    index=(output/'prepared-artifacts.json').read_bytes()
    if sha(index)!=ARTIFACT_SHA:raise ValueError('Random basis position preparation index changed')
    for name,wanted in json.loads(index).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random basis position preparation changed: '+name)
    return True

def predict(before,rom):
    if sha(before)!=BASELINE:raise ValueError('Random basis position image predecessor changed')
    out=bytearray(before)
    for function,owner,entry,offset in SPECS:
        row,=[r for r in symbol_rows(before)if r[1]==function]
        if row[2][1:3]!=(entry,12):raise ValueError('Random basis position predecessor extent changed')
        truth=rom[offset:offset+240]
        if len(truth)!=240:raise ValueError('Random basis position retail slot missing')
        at=elf_slot_offset(before,entry,240);out[at:at+240]=truth;struct.pack_into('>I',out,row[0]+8,240)
    return bytes(out)

def check_image(before,actual,rom):
    if actual!=predict(before,rom):raise ValueError('Random basis position entire image differs')

def expected_map(output):
    data=(output/'private-joint-linked.map').read_bytes()
    for _,owner,_,_ in SPECS:
        private=(BUILD.removeprefix('conker/')+'/make-shadow-'+owner+'/src/game/'+owner+'.c.o').encode()
        if data.count(private)!=9:raise ValueError('Random basis position map owner count changed')
        data=data.replace(private,('build/src/game/'+owner+'.c.o').encode())
    private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
    if data.count(private)!=1:raise ValueError('Random basis position map output changed')
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
        if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Random basis position live input changed: '+name)
    return values

def audit(root,output,installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output);values=check_inputs(root,output,installed)
    elf=root/'conker/build/conker.us.elf'if installed else output/'private-joint-linked.elf'
    actual=elf.read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'])
    if sha(actual)!=LINKED:raise ValueError('Random basis position linked image changed')
    data=audit_layout(elf,root/'conker')
    if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Random basis position protected data changed')
    targets={v[0]for v in SPECS};expected=Counter((n,f[1],240 if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
    if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Random basis position named definition changed')
    q=json.loads((output/'private-owner-image-v11.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
    if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
    return q

def prove_roles(raw,original):
    a=struct.unpack('>60I',raw);b=struct.unpack('>60I',original)
    assert tuple((i*4,x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y)==PATCHES
    def expr(op,x,y):return(op,*sorted((x,y),key=repr))
    states=[[('initial',i)for i in range(32)]for _ in range(2)];proof=[];calls=[];stores=[]
    for i,(x,y)in enumerate(zip(a,b)):
        pc=i*4;op=x>>26
        if x!=y:
            assert op==y>>26
            if op in(49,57):assert (x&~(31<<16))==(y&~(31<<16))
            else:
                assert op==17 and x>>21&31==y>>21&31==16 and x&63==y&63 and x&63 in(0,2)
        results=[]
        for code,state in zip((x,y),states):
            op,rs,rt,fs,fd,fn=code>>26,code>>21&31,code>>16&31,code>>11&31,code>>6&31,code&63
            if op==49:state[rt]=('read',pc,rs,code&65535)
            elif op==17 and rs==16 and fn in(0,2):
                state[fd]=expr('add32'if fn==0 else'mul32',state[fs],state[rt])
            elif op==17 and rs==0:results.append(('GPR',rt,state[fs]))
            elif op==57:results.append(('store',rs,code&65535,state[rt]))
            elif op==3:
                for reg in range(20):state[reg]=('call-clobber',pc,reg)
            else:assert x==y
        if results:
            assert len(results)==2 and results[0]==results[1],(pc,results)
            proof.append(dict(offset=pc,obligation=results[0]))
            if results[0][0]=='store':stores.append(pc)
        if op==3:calls.append(pc)
    assert calls==[0x18,0x20,0x4C] and stores==[0x84,0xB0,0xDC]
    assert states[0][20:]==states[1][20:]==[('initial',i)for i in range(20,32)]
    # Exact non-FP instruction identity closes GPRs, stack/literal addresses, branch
    # structure and frame. FP expression equality closes every value crossing into
    # a GPR, helper argument, output store or callee-saved FP register. Treat loads
    # as ordered symbolic observations so overlapping stores do not justify caching.
    return dict(obligations=proof,helper_call_offsets=calls,output_store_offsets=stores,finite_intermediate_domain=True,callee_saved_FP_unchanged=True)

HEADERS='#include <ultra64.h>\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143874(s16,f32,f32*,f32*);\n'
SELECTED='void func_1514F808(f32 *basis, f32 scale, f32 *output) {\n    f32 second;\n    f32 first;\n    f32 sample;\n    s32 random;\n    random = func_150ADA20();\n    sample = func_150ADA68();\n    func_15143874((s16)(random & 255), sample * basis[10], &first, &second);\n    output[0] = ((basis[4] * first + basis[7] * second) + basis[1]) * scale;\n    output[1] = ((basis[5] * first + basis[8] * second) + basis[2]) * scale;\n    output[2] = ((basis[6] * first + basis[9] * second) + basis[3]) * scale;\n}\n'
SNAPSHOT_SHA='ec9b527e9b4bde4db7665748b8a774d87f18558b16ba6c46b246ff69daa7fa76'
ARTIFACT_SHA='ca3c1744244bad63cb9715b5abaae1b9cb29ede24ff32cbf9a0f49feb66260cd'
