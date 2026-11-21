from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,struct,subprocess,sys
from tools.experiments import game_camera_script_state_15125c40_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_script_state_15125c40_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY;START=0x15122F00;NEXT=0x15128680;END=START+16
def caller_checks():
    census=json.loads((out/'caller-census.json').read_text());assert len(census['direct_original_calls'])==1 and not census['aligned_loaded_pointer_literals']
    assert census['direct_original_calls'][0]['entry']==START
    rom=(root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>4I',rom,0x1503B0)
    assert window==(0x0D449710,0x02002025,0x0D44A1A0,0x02002025)
    class Connected(g.Machine):
        def __init__(self,words,c,m,opening=window):
            self.c=c;code=dict(zip(range(ENTRY,ENTRY+372,4),words));code[END]=0
            FactoryOracle.__init__(self,opening,m,c,entry=START,s=g.SYMS,arguments=(0xDEADC0DE,),connected=code)
            self.r[16]=g.CAMERA;self.before[16]=g.CAMERA;self.visited_words=set()
            self.code=WindowCode(self.code,self);self.code.ends=(END,)
        def record_call(self,t):
            if t in(ENTRY,NEXT):
                a=tuple(self.arguments(1));assert a==(g.CAMERA,),(hex(t),a)
                self.calls.append((t,a));self.events.append(('CALL',t,a))
            else:super().record_call(t)
        def hook(self,t):
            if t==NEXT:
                for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xB9000000+r
            else:super().hook(t)
    count=0
    cases=[g.Case(phase,category,state,timer,flags,mutation)for phase,category,state,timer,flags,mutation in itertools.product((0,8),(0,0x42),(0,3,26),(0,1,2),(0,2),(0,1))]
    for c in cases:
        initial=g.fixture(c);expected,calls=g.reference(initial,c);states=[]
        for words in g.programs():
            m=Connected(words,c,dict(initial))
            try:m.run();raise AssertionError('missing caller boundary')
            except WindowBoundary:pass
            assert(g.public(m.memory,c),m.calls)==(expected,[(ENTRY,(g.CAMERA,))]+calls+[(NEXT,(g.CAMERA,))]),c
            assert m.r[16]==g.CAMERA and m.r[29]==g.STACK+c.phase
            states.append(g.state(m))
        assert states[0]==states[1]==states[2];count+=1
    rejected=[]
    for label,index,word in(('lost-delay-argument',1,0),('skipped-dispatch',0,0)):
        opening=list(window);opening[index]=word;c=g.Case(category=0x42,state=26,timer=1)
        failed=False
        try:
            m=Connected(g.programs()[0],c,g.fixture(c),opening);m.run()
        except(AssertionError,KeyError):failed=True
        except WindowBoundary:failed=m.calls[0][0]!=ENTRY
        assert failed,label;rejected.append(label)
    r={'caller':'func_15122C5C','window':hex(START),'window_words':4,'cases_per_stream':count,'streams':3,
       'effective_controls':rejected,'return_value_unused_before_next_call':True,'whole_caller_claim':False,
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def links():
    where=out/'links';where.mkdir(exist_ok=True);reports=[]
    files={'raw':out/'variant-s32-first/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/game_14FF90.c.o'}
    parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_15125C40'],parsed[2],'func_15125C40',g.SYMS)
    assert not missing,missing
    isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
    assert payload(isolated,'func_15125C40')==payload(files['raw'],'func_15125C40')
    files['raw']=isolated
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        symbols={g.HELPER:g.HELPER+code_delta,g.GLOBAL:g.GLOBAL+data_delta}
        bind={'func_1509BFB0':symbols[g.HELPER],'D_800D1940':symbols[g.GLOBAL]}
        expected=bound_blob(*payload(files['retail'],'func_15125C40'),bind)
        for label,obj in files.items():
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%(0x15122C5C+code_delta))
            undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines();definitions={}
            anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'))
            anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
            for line in undefined:
                n=line.split()[-1]
                if n in bind:definitions[n]=bind[n]
                elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
                elif n.startswith(('D_','func_')):
                    value=int(n.split('_')[1],16);definitions[n]=value+(data_delta if value&0x80000000 else code_delta)
                else:raise AssertionError(('unqualified undefined symbol',n))
            q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15125C40',
                *['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
            assert tuple(functions['func_15125C40'][:93])==tuple(expected),(label,code_delta)
            reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':93,'GNU_equals_independent_binding':True})
    r={'links':reports,'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated target payload and bindings; unused raw-owner data is outside this link scope.',
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':caller_checks();links()
