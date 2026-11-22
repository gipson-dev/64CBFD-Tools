from pathlib import Path
from dataclasses import replace
import itertools,json,struct,subprocess,sys,csv,io
from collections import Counter
from tools.experiments import game_owner_mask_effect_151b9f00_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_owner_mask_effect_151b9f00_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as pg
from tools.experiments.alternative_source_draft_word_screen import emit_function

ENTRY=g.ENTRY
CALLER,GATE,PRESET0,PRESET1=0x1514F194,0x800BE616,0x800A5958,0x800A5964
CHANNEL,INIT,OPTIONAL,FLAGS,CREATE,ATTACH=0x151D0F60,0x151BB044,0x151BC074,0x151BD2F8,0x15160A58,0x1514EC1C
COUNTS={CHANNEL:4,INIT:1,OPTIONAL:1,FLAGS:3,CREATE:16,ATTACH:3}
SECOND=0x51000

def caller_checks():
    census=json.loads((out/'caller-census.json').read_text())
    assert census['direct_original_calls']==[dict(entry=0x1514F204,ROM=0x17C6B4,kind='JAL')]
    assert not census['aligned_loaded_pointer_literals']
    rom=(root/'conker/conker.us.bin').read_bytes()
    elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
    caller=list(struct.unpack_from('>93I',rom,0x17C644));streams=g.programs()

    def fixture(c,gate):
        memory=g.fixture(c)
        for base,n in ((PRESET0,24),(SECOND,64),(GATE,4)):
            memory.update({base+i:(i*29+0x35)&255 for i in range(n)})
        memory[GATE]=gate
        return memory

    def parent_effect(memory,c,ordinal,p):
        if p:g.put(memory,p+16+4*(ordinal%3),0x12340000+ordinal)

    def reference(initial,c,second):
        memory=dict(initial);calls=[];observations=[];ordinal=0;p=g.owner(c)
        def call(t,a):
            nonlocal ordinal
            calls.append((t,a));ordinal+=1
            if t==CREATE:observations.append(('parent-create',(a,g.data(memory,a[2],12))))
            parent_effect(memory,c,ordinal,a[1]if t==ATTACH else a[0])
        call(CHANNEL,(p,1,255,1));call(CHANNEL,(p,2,255,1));call(INIT,(p,))
        if memory[GATE]==0:call(OPTIONAL,(p,))
        call(FLAGS,(p,255,1))
        public,childcalls,answer,childobservations=g.reference(memory,c,home=g.STACK+c.phase-80,arguments=(p,255,1))
        memory.update(public);calls.extend(childcalls);observations.extend(childobservations)
        call(CREATE,(p,1,PRESET0,2,300,12,255,255,255,2,0,0xFFFFFFFF,0,0,255,1))
        call(CREATE,(p,1,PRESET1,2,300,15,255,0,0,255,1,0xFFFFFFFF,0,0,255,1))
        if second:call(ATTACH,(SECOND,p,25))
        return g.public(memory),calls,observations

    class Connected(g.Machine):
        def __init__(self,words,c,memory,second,opening=caller):
            self.c=c;self.observations=[];self.target_entries=[];self.parent_calls=0;self.second=second
            code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words))
            FactoryOracle.__init__(self,opening,memory,c,entry=CALLER,s=g.SYMS,arguments=(g.owner(c),),connected=code)
        def record_call(self,t):
            if t==ENTRY:
                a=tuple(self.arguments(3));self.target_entries.append(a);assert a==(g.owner(self.c),255,1)
                self.events.append(('CONNECTED',t,a))
            elif t in (g.FACTORY,g.COPY):super().record_call(t)
            else:
                a=tuple(self.arguments(COUNTS[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
                if t==CREATE:self.observations.append(('parent-create',(a,g.data(self.memory,a[2],12))))
        def hook(self,t):
            if t in (g.FACTORY,g.COPY):return super().hook(t)
            a=self.calls[-1][1];self.parent_calls+=1
            parent_effect(self.memory,self.c,self.parent_calls,a[1]if t==ATTACH else a[0])
            for i in range(COUNTS[t]):self.put(self.r[29]+4*i,0xB5000000+i,4)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
            self.r[2]=SECOND if t==CREATE and self.second else 0

    coverage=set();cases=0
    for delta,mode,gate,outcome,mutation,second,phase in itertools.product((0,812,1624),(0,2,4,255),(0,1),(0,1),(0,1),(0,1),(0,8)):
        c=g.Case(delta=delta,mode=mode,outcome=outcome,mutation=mutation,phase=phase)
        initial=fixture(c,gate);expected=reference(initial,c,second);states=[]
        for words in streams:
            machine=Connected(words,c,dict(initial),second).run()
            assert(g.public(machine.memory),machine.calls,machine.observations)==expected,('caller model',c,gate,second)
            assert machine.target_entries==[(g.owner(c),255,1)]
            assert machine.r[29]==g.STACK+c.phase
            for reg in(*range(16,24),30):assert machine.r[reg]==machine.before[reg]
            coverage.update(machine.visits);states.append(g.state(machine))
        assert states[0]==states[1]==states[2]
        cases+=1
    assert set(range(CALLER,CALLER+372,4))<=coverage
    controls=[]
    for label,index,value in(('missing-call',28,0),('wrong-context-delay',29,0x24060002),('wrong-owner',26,0x00002025)):
        changed=list(caller);changed[index]=value;c=g.Case();initial=fixture(c,0)
        try:
            machine=Connected(streams[0],c,dict(initial),1,changed).run()
            rejected=(g.public(machine.memory),machine.calls,machine.observations)!=reference(initial,c,1)or not machine.target_entries
        except(AssertionError,KeyError):rejected=True
        assert rejected,label;controls.append(label)
    at=elf_slot_offset(elf,CALLER,372);assert elf[at:at+372]==struct.pack('>93I',*caller)
    report=dict(caller='func_1514F194',caller_words=93,cases_per_stream=cases,streams=3,covered_caller_words=93,actual_JAL='0x1514F204',delay_slot_context=1,current_caller_equals_original=True,effective_controls=controls,limits='Complete original caller and target execute together. Other helpers retain bounded mutation/ABI-clobber contracts; no allocator or gameplay acceptance.',source_installed=packet.installed(),matching_credit=0)
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

def guard_checks():
    baseline=(out/'baseline/conker/retail_word_patches.us.csv').read_bytes()
    selected=(out/'private-guards.csv').read_bytes();assert selected.startswith(baseline)
    rows=list(csv.DictReader(io.StringIO(selected.decode())));target=[r for r in rows if r['function']=='func_151B9F00']
    assert len(target)==25 and all(r['filename']=='generated_1E73B0'and r['omit']=='false'and not r['insert_after']for r in target)
    fields=list(rows[0]);where=out/'guard-controls';where.mkdir(exist_ok=True)
    raw,raw_refs=payload(out/'qualified-source/candidate.o','func_151B9F00')
    original,original_refs=payload(out/'image-qualification/retail.o','func_151B9F00')
    a,b=struct.unpack('>97I',raw),struct.unpack('>97I',original)
    key=lambda words,refs,i:(words[i],tuple(refs.get(4*i,[])))
    assert Counter(key(a,raw_refs,i)for i in range(9,34))==Counter(key(b,original_refs,i)for i in range(9,34))
    assert a[32]==b[32]==0x10200017 and a[87]==0x03222021 and b[87]==0x00592021
    assert all(key(a,raw_refs,i)==key(b,original_refs,i)for i in range(97)if i not in set(range(9,34))|{87})
    controls=[]
    for label in('wrong-word','wrong-relocation','wrong-function','wrong-owner','duplicate-offset'):
        changed=[dict(r)for r in rows];first=next(r for r in changed if r['function']=='func_151B9F00')
        if label=='wrong-word':first['expected']='0xFFFFFFFF'
        elif label=='wrong-relocation':first['expected_relocations']='R_MIPS_HI16:D_8008FD90'
        elif label=='wrong-function':first['function']='func_151B9F00_invalid'
        elif label=='wrong-owner':
            for r in changed:
                if r['function']=='func_151B9F00':r['filename']='wrong_owner'
        else:changed.append(dict(first))
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(changed)
        file=where/(label+'.csv');file.write_text(stream.getvalue())
        try:
            text=pg.emit_padded_assembly(out/'qualified-source/candidate.o',root/'conker/asm/1E73B0.s',filename='generated_1E73B0',word_patches_path=file)
            # A different owner legitimately selects no rows, which must fail exact output.
            rejected=label=='wrong-owner'and text!=(out/'image-qualification/padded.s').read_text()
        except ValueError:rejected=True
        assert rejected,label;controls.append(label)
    report=dict(guards=25,original_CSV_prefix_preserved=True,closed_schedule_words=25,changed_schedule_words=24,commutative_operand_words=1,effective_controls=controls,insertions=0,omissions=0)
    (out/'guard-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

def links():
    where=out/'links';where.mkdir(exist_ok=True)
    paths={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_1E73B0.c.o'}
    parsed=parse_object(paths['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_151B9F00'],parsed[2],'func_151B9F00',g.SYMS);assert not missing
    file=where/'raw-target.s';file.write_text(assembly);isolated=file.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(file)],capture_output=True,check=True)
    assert payload(isolated,'func_151B9F00')==payload(paths['raw'],'func_151B9F00');paths['raw']=isolated
    anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'))
    anchored.update({name:row[1]for _,name,row,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if name})
    reports=[]
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        bindings={name:value+(data_delta if value&0x80000000 else code_delta)for name,value in g.SYMS.items()}
        for label,obj in paths.items():
            expected=bound_blob(*payload(obj,'func_151B9F00'),bindings)
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%(ENTRY+code_delta))
            definitions={}
            for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
                name=line.split()[-1];address=bindings.get(name)
                if address is None:
                    assert name in anchored,('unqualified binding',name);address=anchored[name]+(data_delta if anchored[name]&0x80000000 else code_delta)
                definitions[name]=address
            result=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151B9F00',*['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');addresses={name:row[1]for _,name,row,_ in symbol_rows(elf.read_bytes())if name}
            assert addresses['func_151B9F00']==ENTRY+code_delta
            assert tuple(functions['func_151B9F00'][:97])==tuple(expected)
            reports.append(dict(stream=label,code_delta=code_delta,data_delta=data_delta,words=97,GNU_equals_independent_binding=True))
    guard_checks()
    report=dict(links=reports,target_relocation_kinds=['R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'],HI16_LO16_carry_exercised=True,source_installed=packet.installed(),matching_credit=0)
    (out/'GNU-links.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

if __name__=='__main__':caller_checks();links()
