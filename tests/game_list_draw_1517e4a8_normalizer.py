"""Closed source-origin derivation. No retail bytes/assembly are read here."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_list_draw_1517e4a8_recovery as source

def gpr_fields(w):
    op,rs,fn=w>>26,w>>21&31,w&63
    if op==0:
        if fn in(0,2,3):return(16,11)
        if fn in(4,33,35,36,37,42,43):return(21,16,11)
        if fn in(16,18):return(11,)
        if fn in(25,26,27):return(21,16)
        if fn in(8,9):return(21,)if fn==8 else(21,11)
        if fn==13:return()
        raise ValueError(('unsupported register format',hex(w)))
    if op==17:return(16,)if rs in(0,4)else()
    if op in(3,):return()
    if op in(1,6,7,22,23,49,53,57,61):return(21,)
    if op==15:return(16,)
    return(21,16)

def branch(w):return w>>26 in(1,4,5,6,7,20,21,22,23)or(w>>26==17 and w>>21&31==8)

def derive(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=source.SPEC['raw_sha256']:raise ValueError('Draw payload changed')
    if json.loads(json.dumps(refs))!=source.SPEC['raw_refs']:raise ValueError('Draw bindings changed')
    words=struct.unpack('>361I',raw);origins={i:i for i in range(361)}
    origins.update({39:93,42:39,85:None,87:94,88:87,89:95,90:96,91:88,92:89,93:99,94:91,95:92,96:90,99:102,102:None,
        115:199,194:200,195:193,196:201,197:202,198:194,199:195,200:203,201:197,202:198,203:196,
        274:275,275:274,281:282,282:283,283:281,
        312:315,314:316,315:317,316:318,317:319,318:320,319:321,320:322,321:323,322:324,323:325,324:312,325:326,326:327,327:314,
        345:347,347:345})
    origins.update({i+1:i for i in range(115,193)})
    retained=[i for i in origins.values()if i is not None]
    assert len(retained)==len(set(retained))==359
    assert set(range(361))-set(retained)=={42,85}
    inverse={old:new for new,old in origins.items()if old is not None}
    # Moved delay operations require the corresponding shared continuation.
    destinations={38:42,40:87,84:87,92:96,94:97,98:103,168:194,172:194,199:203,201:204,252:274}
    tick_roles={93,94,95,96,99,104,106,107,199,200,201,202,203,204,212}
    def color(index,w):
        roles={}
        if 28<=index<=187:roles[6]=7  # strength A2 -> A3
        if 59<=index<=218:roles[5]=6  # retained squared-distance A1 -> A2
        if index in tick_roles:roles[3]=5
        if index==97:roles[25]=5
        if index in(168,172)or 187<=index<=192:roles[2]=18
        if index==193:roles[18]=3
        if index==194:roles.update({2:18,18:3,3:2})
        if index in(195,196):roles[3]=2
        if index in(206,209):roles.update({2:18,18:3})
        if index==208:roles[2]=18
        if index==212:roles[18]=3
        if 274<=index<=293:roles.update({10:18,11:14,12:10,13:11,14:12,15:13})
        if index in(300,319):roles[25]=15
        if index in(331,333):roles[10]=24
        if index in(335,337):roles[14]=12
        if index in(339,340):roles[11]=14
        if index in(343,346):roles[13]=11
        result=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in roles:result=(result&~(31<<shift))|(roles[reg]<<shift)
        if index in(92,198):
            assert w>>26==0 and w&63==35
            # current-target == -(target-current), modulo 32 bits.
            result=(result&~((31<<21)|(31<<16)))|((3 if index==92 else 2)<<16)
        if index==211:
            assert w>>26==0 and w&63==33
            result=(result&~((31<<21)|(31<<16)))|(3<<21)|(5<<16)
        if index in(302,338):
            assert w>>21&31==29 and w&65535==0xA0
            result=(result&0xFFFF0000)|0xB0
        return result
    result=[];bindings={}
    for out in range(361):
        origin=origins[out]
        if out==85:word=0
        elif out==102:word=color(102,words[102]) # retail's unreachable duplicate comparison
        else:
            word=color(origin,words[origin])
            if out in(38,98):
                assert word>>26==(21 if out==38 else 4)
                word=(word&0x03FFFFFF)|((5 if out==38 else 20)<<26)
            if branch(word):
                old_target=origin+1+(((words[origin]&65535)^32768)-32768)
                target=destinations.get(out,inverse.get(old_target))
                assert target is not None and 0<=target<361,(out,origin,old_target)
                word=(word&0xFFFF0000)|((target-out-1)&65535)
            if origin*4 in refs:bindings[out*4]=refs[origin*4]
        result.append(word)
    report=dict(raw_words=361,output_words=361,retained_unique_origins=359,omitted_origins=[42,85],added_output_indices=[85,102],
        counter_home_origins=[302,338],frame=184,executed_FP_primitives_retained=True,whole_body_replacement=False)
    return struct.pack('>361I',*result),bindings,report


from tools.experiments.game_actor_classifier_candidates import sections
s=source
OUT=s.OUT/'match-proof'
OUT.mkdir(parents=True,exist_ok=True)

def original():
    text=(s.ROOT/'conker/asm/1AB530.s').read_text();a=text.index('glabel '+s.FUNCTION+'\n');b=text.index('endlabel '+s.FUNCTION,a)+len('endlabel '+s.FUNCTION)
    p=OUT/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text[a:b]+'\n.size '+s.FUNCTION+',.-'+s.FUNCTION+'\n')
    obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(s.ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
    return s.payload(obj,s.FUNCTION)

def independent_links():
    raw,refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION);derived,bindings,report=derive(raw,refs)
    expected,oldrefs=original();assert(derived,bindings)==(expected,oldrefs)
    truth=struct.unpack_from('>361I',(s.ROOT/'conker/conker.us.bin').read_bytes(),s.ROM)
    assert s.bind(derived,bindings)==truth
    bad=bytearray(raw);bad[3]^=1
    for blob,relocs in((bytes(bad),refs),(raw,{**refs,12:[('R_MIPS_26','func_1517E4A8')]})):
        try:derive(blob,relocs)
        except ValueError:pass
        else:raise AssertionError('corrupted payload/bindings accepted')
    linked=[];folder=OUT/'independent-links';folder.mkdir(exist_ok=True)
    for n,(entry_shift,code_shift,data_shift)in enumerate(((0,0,0),(0x1000,0x2000,0x12348))):
        objects=[]
        for label,payload,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
            text=['.set noat','.set noreorder','.text','.globl '+s.FUNCTION,'.type '+s.FUNCTION+', @function',s.FUNCTION+':']
            for i,w in enumerate(struct.unpack('>361I',payload)):
                for kind,name in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+name)
                text.append('.word 0x%08X'%w)
            text.append('.size '+s.FUNCTION+',.-'+s.FUNCTION)
            p=folder/(label+'-'+str(n)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(s.ENTRY+entry_shift))
            anchors={name:int(name.split('_')[1],16)+(code_shift if name.startswith('func_')else data_shift)for rs in relocs.values()for kind,name in rs}
            elf=p.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
            objects.append(sections(elf)['.text'][1])
        assert objects[0]==objects[1];linked.append(dict(entry_shift=entry_shift,code_shift=code_shift,data_shift=data_shift))
    report.update(independent_GNU_links=linked,payload_and_binding_controls_rejected=True,matching_credit=0)
    (OUT/'independent-links.json').write_text(json.dumps(report,indent=2)+'\n');return report
