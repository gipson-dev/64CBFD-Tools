"""Independent GNU links of original assembly, padded C and raw C at two bases."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests import game_audio_command_dispatch_1509e730_guest as g
from tools import pad_generated_object as pg
from tools.experiments.game_actor_classifier_candidates import sections
def run():
    where=out/'links';where.mkdir(exist_ok=True)
    original=where/'original.s';original.write_text((out/'baseline/conker/asm/CBAF0.s').read_text())
    original_object=original.with_suffix('.o')
    assembled=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(original_object),str(original)],capture_output=True,text=True)
    assert assembled.returncode==0,assembled.stdout+assembled.stderr
    paths={'original':original_object,'padded_C':out/'image-qualification/assembly.o','raw_C':out/'qualified-source-screen/candidate.o'}
    parsed={n:pg.parse_object(p)for n,p in paths.items()}
    external={symbol for text,functions,refs in parsed.values()for entries in refs.values()for _,symbol in entries if symbol not in functions and symbol!='.rodata'}
    report=[]
    for code_shift,data_shift in((0,0),(0x10010,0x18020)):
        label=f'{code_shift:x}-{data_shift:x}';text_base=0x1509e640+code_shift;data_base=g.TABLE+data_shift
        anchors={}
        for name in external:
            match=re.fullmatch(r'(func_|D_|jtbl_)([0-9A-Fa-f]{8})(?:_game)?',name);assert match,name
            anchors[name]=int(match[2],16)+(code_shift if match[1]=='func_'else data_shift)
        loaded={}
        for name,obj in paths.items():
            script=where/(label+'-'+name+'.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(text_base,data_base))
            elf=script.with_suffix('.elf')
            command=['mips-linux-gnu-ld','-m','elf32btsmip','--no-warn-mismatch','-T',str(script),'-e','func_1509E640',
                     *['--defsym='+n+'=0x%X'%v for n,v in sorted(anchors.items())],'-o',str(elf),str(obj)]
            linked=subprocess.run(command,capture_output=True,text=True)
            assert linked.returncode==0,linked.stdout+linked.stderr
            loaded[name]=sections(elf)
        assert loaded['original']['.text']==loaded['padded_C']['.text']
        if code_shift==data_shift==0:
            assert loaded['original']['.text'][1]==(root/'conker/conker.us.bin').read_bytes()[0xcbaf0:0xcbdb0]
        raw_blob,raw_refs=g.payload(paths['raw_C'],'func_1509E730')
        raw_anchors=dict(anchors);raw_anchors['.rodata']=data_base
        bound=struct.pack('>92I',*g.bound_blob(raw_blob,raw_refs,raw_anchors))
        raw_start=parsed['raw_C'][1]['func_1509E730']['value']
        assert loaded['raw_C']['.text'][1][raw_start:raw_start+368]==bound
        _,table=g.program(paths['raw_C'])
        assert struct.unpack('>7I',loaded['raw_C']['.rodata'][1][:28])==tuple(value+code_shift for value in table)
        report.append(dict(code_shift=code_shift,data_shift=data_shift,whole_owner_text_bytes=len(loaded['original']['.text'][1]),
         original_assembly_equals_padded_C=True,raw_C_GNU_equals_independent_binding=True,raw_table_entries=7,
         data_HI16_LO16_carry_exercised=data_shift!=0))
    r=dict(passes=True,links=report,source_installed=recovery.installed(),matching_credit=0)
    (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
