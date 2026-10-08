"""Complete record construction, live player loops and guarded zero-gate schedule."""

import csv
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_player_registration_candidates as screen
from tools.experiments import game_selected_player_state_candidates as predicate
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import signed

OWNER, RECORD, ALTERNATE = 0x20000, 0x21000, 0x22000
SOURCE = 'conker/src/game/generated_205C90.c'


def public(memory):
    return {a:v for a,v in memory.items() if not prior.STACK-0x600<=a<prior.STACK+0x140}


def public_events(model):
    return [e for e in model.events if not prior.STACK-0x600<=e[1]<prior.STACK+0x140]


def fixture(mask=15, limit=3, gates=(0,0,0,0), disabled=0, symbols=None):
    symbols=symbols or screen.SYMBOLS
    memory={prior.STACK+i:0xA5 for i in range(-0x200,0x100)}
    for base in (OWNER,RECORD,ALTERNATE):
        memory.update({base+i:0xA5 for i in range(-32,96)})
    for i,value in enumerate((1,0xA5,0x12,0x34,8,mask,255,0x5A)):
        put(memory,OWNER+i,value,1)
    put(memory,symbols['D_800E0B94'],disabled,1)
    for i,value in enumerate(gates):
        put(memory,symbols['D_800BEAC%d'%i],value,1)
    put(memory,symbols['D_80082FA0'],limit)
    return memory


def settings(**changes):
    result=dict(pred=1,good=0xFFFFFFFF,bad=0,good_value=1,bad_value=1,
                allocation=RECORD,mode=0,actual_predicate=False)
    result.update(changes)
    return result


def mutations(role,index,memory,config,owner,record,stack,symbols):
    mode=config['mode']
    if mode==1 and role=='func_151D87E0':
        return [(owner+5,15,1),(symbols['D_80082FA0'],1,4),(symbols['D_800BEAC2'],1,1)]
    if mode==2 and role=='func_15181CC8' and index==0:
        return [(owner+5,14,1),(symbols['D_80082FA0'],3,4),(owner+4,255,1)]
    if mode==3 and role=='func_1517EF00' and index==0:
        return [(symbols['D_80082FA0'],0xFFFFFFFF,4)]
    if mode==4 and role=='func_15167A68':
        return [(owner+i,v,1) for i,v in enumerate((2,0xA5,0xFE,0xDC,127,15,0,0x91))]
    if mode==5 and role=='func_1501C010' and index==0:
        return [(record+0x13,0,1),(owner+4,128,1)]
    if mode==6 and role=='func_1501C010':
        return [(record+0x13,15,1),(owner+4,(read(memory,owner+4,1)+1)&255,1)]
    if mode==7 and role=='func_15181CC8' and index==0:
        return [(stack,ALTERNATE,4),(stack+4,0x11223344,4),
                (stack+8,0xFFFFFFAB,4),(stack+12,0x87654321,4)]
    return []


class ConstructionReference:
    def __init__(self,memory,args,config,phase=0,symbols=None):
        self.memory,self.events,self.calls=dict(memory),[],[]
        self.args,self.config,self.stack=args,config,prior.STACK+phase
        self.symbols=symbols or screen.SYMBOLS
        self.counts={}

    def get(self,address,size=4):
        value=read(self.memory,address&0xFFFFFFFF,size)
        self.events.append(('R',address&0xFFFFFFFF,size,value))
        return value

    def put(self,address,value,size=1):
        address &= 0xFFFFFFFF
        self.events.append(('W',address,size,value&((1<<(size*8))-1)))
        assert all(address+i in self.memory for i in range(size))
        put(self.memory,address,value,size)

    def call(self,role,args):
        target=self.symbols[role]
        self.calls.append((target,*args))
        self.events.append(('CALL',target,tuple(args)))
        index=self.counts.get(role,0)
        self.counts[role]=index+1
        if role=='func_151D87E0':
            result=self.config['pred']
            if self.config['actual_predicate']:
                result=0
                for player in range(4):
                    if args[0]&(1<<player):
                        mapped=self.get(predicate.SYMBOLS['D_80084060']+player,1)
                        if mapped>=4:
                            break
                        if self.get(predicate.SYMBOLS['D_800BE944']+mapped,1):
                            result=1
                            break
        elif role=='func_15181CC8':
            result=self.config['good_value'] if self.config['good']&(1<<args[0]) else 0
        elif role=='func_1517EF00':
            result=self.config['bad_value'] if self.config['bad']&(1<<args[0]) else 0
        elif role=='func_15167A68':
            result=self.config['allocation']
        elif role=='memcpy':
            destination,source,size=args
            assert size<=16
            for i in range(size):
                self.put(destination+i,self.get(source+i,1),1)
            result=destination
        else:
            assert role=='func_1501C010'
            result=0
        for address,value,size in mutations(role,index,self.memory,self.config,self.args[0],
                self.config['allocation'],self.stack,self.symbols):
            self.put(address,value,size)
        return result&0xFFFFFFFF

    def run(self):
        owner,payload,slot,context=self.args
        for i,value in enumerate(self.args[1:]):
            put(self.memory,self.stack+4+i*4,value)
        if self.get(self.symbols['D_800E0B94'],1):
            return 0
        if not self.call('func_151D87E0',(self.get(owner+5,1),)):
            return 0
        for i in range(4):
            if self.get(self.symbols['D_800BEAC%d'%i],1):
                return 0
        limit=signed(self.get(self.symbols['D_80082FA0']))
        player=0
        while player<=limit:
            if self.get(owner+5,1)&(1<<player):
                if not self.call('func_15181CC8',(player,)):
                    return 0
                if self.call('func_1517EF00',(player,)):
                    return 0
            limit=signed(self.get(self.symbols['D_80082FA0']))
            player+=1
            assert player<=32
        payload,slot,context=[read(self.memory,self.stack+4+i*4) for i in range(3)]
        record=self.call('func_15167A68',(63,context,(payload+24)&0xFFFFFFFF,1,slot&255,1))
        if not record:
            return 0
        self.call('memcpy',((record+14)&0xFFFFFFFF,owner,8))
        for player in range(4):
            if self.get(record+19,1)&(1<<player):
                self.call('func_1501C010',(player,self.get(owner+4,1)))
        self.put(record+22,self.get(owner+4,1),1)
        return record


class ConstructionOracle(TriangleOracle):
    def __init__(self,words,memory,args,config,phase=0,symbols=None,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        self.symbols=symbols or screen.SYMBOLS
        self.roles={address:name for name,address in self.symbols.items() if name.startswith('func_') or name=='memcpy'}
        self.args,self.config,self.phase=args,config,phase
        self.counts={}

    def record_call(self,target):
        role=self.roles[target]
        count=6 if role=='func_15167A68' else 3 if role=='memcpy' else 2 if role=='func_1501C010' else 1
        args=tuple(self.r[4:4+min(count,4)])
        if count>4:
            args+=tuple(self.get(self.r[29]+0x10+i*4,4) for i in range(count-4))
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))

    def hook(self,target):
        role=self.roles[target]
        args=self.calls[-1][1:]
        index=self.counts.get(role,0)
        self.counts[role]=index+1
        if role=='func_151D87E0':
            result=self.config['pred']
        elif role=='func_15181CC8':
            result=self.config['good_value'] if self.config['good']&(1<<args[0]) else 0
        elif role=='func_1517EF00':
            result=self.config['bad_value'] if self.config['bad']&(1<<args[0]) else 0
        elif role=='func_15167A68':
            result=self.config['allocation']
        elif role=='memcpy':
            destination,source,size=args
            assert size<=16
            for i in range(size):
                self.put(destination+i,self.get(source+i,1),1)
            result=destination
        else:
            assert role=='func_1501C010'
            result=0
        for address,value,size in mutations(role,index,self.memory,self.config,self.args[0],
                self.config['allocation'],prior.STACK+self.phase,self.symbols):
            self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result&0xFFFFFFFF


class GameRecordPlayerRegistrationTests(unittest.TestCase):
    run_host=prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-player-registration-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.words=screen.normalize(cls.raw)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>111I',cls.rom,screen.ROM))
        cls.functions,_,cls.addresses=load_elf_functions(str(cls.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,memory,args=(OWNER,28,255,0),config=None,phase=0,words=None,
                symbols=None,entry=screen.ENTRY,connected=None,full_state=True):
        config=config or settings()
        reference=ConstructionReference(memory,args,config,phase,symbols)
        result=reference.run()
        bodies=(self.raw,self.retail) if words is None else (words,)
        models=[]
        for body in bodies:
            model=ConstructionOracle(body,memory,args,config,phase,symbols,entry,connected).run()
            self.assertEqual((model.r[2],model.calls,public_events(model),public(model.memory)),
                (result,reference.calls,public_events(reference),public(reference.memory)))
            models.append(model)
        if len(models)==2 and full_state:
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                             (models[1].r,models[1].f,models[1].events,models[1].memory))
        return models

    def test_01_complete_slot_guarded_schedule_and_symbolic_relocations(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(111,48,2))
        self.assertEqual(self.words,self.retail)
        self.assertEqual([(i*4,a,b) for i,(a,b) in enumerate(zip(self.raw,self.retail)) if a!=b],
                         [(0x94,0x51000004,0x11000003),(0x98,0x8E490000,0)])
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.assertEqual(len(self.record['relocations']),18)
        for index in (37,38,39,41):
            stale=self.raw.copy()
            stale[index]^=1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        self.receipt('slot',dict(words=111,bytes=444,frame=48,raw_differences=2,normalized_differences=0,
            guards=2,symbolic_relocations=18,stale_schedule_rejections=4,
            complete_semantic_C=True,generated_filler_data=0))

    def test_02_masks_limits_checks_failure_order_and_reachable_words(self):
        seen=[set(),set()]
        cases=0
        for mask,good,bad,limit,allocation,phase in itertools.product(range(16),range(16),range(16),
                (-1,0,1,2,3),(0,RECORD),(0,8)):
            models=self.compare(fixture(mask,limit),config=settings(good=good,bad=bad,allocation=allocation),phase=phase)
            for reach,model in zip(seen,models):
                reach.update(model.visits)
            cases+=1
        for mask,limit,pattern,allocation,phase in itertools.product(range(256),(-2,-1,0,3,4,7,31),
                range(4),(0,RECORD),(0,8)):
            plans=((0xFFFFFFFF,0),(0,0),(0xFFFFFFFF,0xFFFFFFFF),(0x55555555,0xAAAAAAAA))
            good,bad=plans[pattern]
            models=self.compare(fixture(mask,limit),config=settings(good=good,bad=bad,allocation=allocation,
                good_value=(1,0xFFFFFFFF,0x80000000,255)[pattern]),phase=phase)
            for reach,model in zip(seen,models):
                reach.update(model.visits)
            cases+=1

        for phase,gate in itertools.product((0,8),range(6)):
            flags=[0]*4
            if gate>=2:
                flags[gate-2]=1
            models=self.compare(fixture(gates=flags,disabled=1 if gate==0 else 0),
                                config=settings(pred=0 if gate==1 else 1),phase=phase)
            for reach,model in zip(seen,models):
                reach.update(model.visits)
            cases+=1
        all_words=set(range(screen.ENTRY,screen.ENTRY+444,4))
        self.assertEqual([sorted((a-screen.ENTRY)//4 for a in all_words-s) for s in seen],[[41,62],[62]])
        self.receipt('guest',dict(cases=cases,all_low_mask_and_check_bitset_pairs=True,all_byte_masks=True,
            SP_phases=2,defined_unsigned_shift_limits=(-2,-1,0,3,4,7,31),
            missing_raw_words=(41,62),missing_retail_words=(62,),
            missing_only_unreachable_duplicate_loads=True,full_GP_FP_trace_memory_equal=True,
            independent_return_call_read_write_reference=True))

    def test_03_lazy_gate_bytes_and_required_instruction_fault_prefixes(self):
        cases=0
        for phase in (0,8):
            for value in (1,128,255):
                memory=fixture(disabled=value)
                for address in [OWNER+5,*[screen.SYMBOLS['D_800BEAC%d'%i] for i in range(4)],
                                *range(screen.SYMBOLS['D_80082FA0'],screen.SYMBOLS['D_80082FA0']+4)]:
                    del memory[address]
                self.compare(memory,phase=phase)
                cases+=1
            memory=fixture()
            for address in [*[screen.SYMBOLS['D_800BEAC%d'%i] for i in range(4)],
                            *range(screen.SYMBOLS['D_80082FA0'],screen.SYMBOLS['D_80082FA0']+4)]:
                del memory[address]
            self.compare(memory,config=settings(pred=0),phase=phase)
            cases+=1
        for index,value,phase in itertools.product(range(4),range(256),(0,8)):
            gates=[0]*4
            gates[index]=value
            memory=fixture(gates=gates,limit=-1)
            if value:
                for i in range(index+1,4):
                    del memory[screen.SYMBOLS['D_800BEAC%d'%i]]
                for address in range(screen.SYMBOLS['D_80082FA0'],screen.SYMBOLS['D_80082FA0']+4):
                    del memory[address]
            self.compare(memory,phase=phase)
            cases+=1
        faults=0
        for phase in (0,8):
            memory=fixture()
            complete=ConstructionOracle(self.retail,memory,(OWNER,28,255,0),settings(),phase).run()
            addresses={event[1] for event in complete.events if event[0] in ('R','W')}
            for address in sorted(addresses):
                broken=memory.copy()
                del broken[address]
                models=[]
                for body in (self.raw,self.retail):
                    model=ConstructionOracle(body,broken,(OWNER,28,255,0),settings(),phase)
                    with self.assertRaises(AssertionError):
                        model.run()
                    models.append(model)
                self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory),hex(address))
                faults+=1
        self.receipt('gates',dict(lazy_gate_cases=cases,required_fault_prefixes=faults,
            no_limit_read_on_final_nonzero_gate=True,all_gate_byte_values=True,
            saved_register_argument_home_and_constructor_prefixes=True,
            memcpy_faults_use_controlled_copy_boundary_not_actual_SDK=True,
            guest_fault_order_not_portable_C_fault_claim=True))

    def test_04_mutations_nonoverlapping_copy_aliases_and_raw_argument_homes(self):
        cases=0
        for mask,limit,mode,record,phase in itertools.product(range(16),(-1,0,3),
                range(7),(RECORD,OWNER-5,OWNER+16),(0,8)):
            self.compare(fixture(mask,limit),config=settings(mode=mode,allocation=record),phase=phase)
            cases+=1
        for payload,slot,context,phase in itertools.product(
                (0,0xFFFFFFE8,0x7FFFFFE7,0x7FFFFFFF,0x80000000),
                (0,1,255,256,0x80000080,0xFFFFFFFF),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
            self.compare(fixture(),args=(OWNER,payload,slot,context),phase=phase)
            cases+=1
        homes=0
        for phase,mask in itertools.product((0,8),(1,3,15,255)):
            self.compare(fixture(mask),config=settings(mode=7),phase=phase)
            homes+=1
        self.receipt('mutations',dict(public_mutation_alias_and_argument_cases=cases,
            private_home_instruction_cases=homes,live_mask_limit_copy_level_reads=True,
            owner_captured_while_three_allocator_arguments_reload_homes=True,
            copy_aliases_nonoverlapping=True,raw_wrapping_payload_and_home_aliases_not_extra_portable_C_range=True))

    def test_05_complete_native32_C_with_mutations_and_canaries(self):
        self.fixture=NATIVE+screen.SELECTED+NATIVE_REFERENCE
        self.run_host(r'''u32 mask,a,b,allocation,cases=0,mode,slot,i;int limit,error;
for(mask=0;mask<256;mask++)for(limit=-1;limit<=4;limit++)for(a=0;a<16;a++)for(b=0;b<16;b++)
for(allocation=0;allocation<2;allocation++){
    if((error=verify(mask,limit,a,b,allocation,0,0,255,28,0)))return error;
    cases++;
}
if(cases!=786432)return 20;
for(mask=0;mask<256;mask++)for(mode=0;mode<7;mode++)for(i=0;i<3;i++)for(slot=0;slot<256;slot++){
    if((error=verify(mask,3,0xFFFFFFFFu,0,1,mode,i,slot,28,0x81223344u)))return error;
    cases++;
}
if(cases!=2162688)return 21;
for(i=0;i<5;i++)for(slot=0;slot<256;slot++){
    static const s32 sizes[]={(-2147483647-1),-24,-1,0,2147483623};
    if((error=verify(15,3,0xFFFFFFFFu,0,1,0,0,slot|0xFFFF0000u,sizes[i],0xFFFFFFFFu)))return error;
    cases++;
}
if(cases!=2163968)return 22;
''')
        self.receipt('native',dict(cases=2163968,pointer_int_bytes=4,
            complete_C_through_volatile_pointer=True,all_masks_check_bitsets_and_failure_paths=True,
            all_slot_bytes_and_explicit_high_to_byte_conversions=True,seven_mutation_modes=True,
            three_nonoverlapping_allocation_aliases=True,all_160_storage_bytes_and_globals_checked=True,
            independent_expected_flow_and_ordered_call_trace=True,
            payload_domain_avoids_signed_add_overflow=True,actual_SDK_allocator_checks_gameplay_not_claimed=True))

    def test_06_source_profile_and_effective_compiled_negative_controls(self):
        records=[]
        ordinary=negative=0
        forms=[(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        cases=[(mask,limit,mode,allocation) for mask,limit,mode,allocation in
               ((0,-1,0,RECORD),(15,3,0,RECORD),(15,3,0,0),(1,0,2,RECORD),
                (15,3,3,RECORD),(1,3,4,RECORD),(15,3,5,RECORD),(1,3,6,RECORD))]
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            outcomes=[]
            for mask,limit,mode,allocation in cases:
                memory=fixture(mask,limit)
                config=settings(mode=mode,allocation=allocation)
                reference=ConstructionReference(memory,(OWNER,28,255,0),config)
                expected=reference.run()
                model=ConstructionOracle(words,memory,(OWNER,28,255,0),config).run()
                outcomes.append((model.r[2],model.calls,public_events(model),public(model.memory))==
                    (expected,reference.calls,public_events(reference),public(reference.memory)))
            if name.startswith('negative-'):
                self.assertFalse(all(outcomes),name)
                negative+=1
            else:
                self.assertTrue(all(outcomes),name)
                ordinary+=len(cases)
        self.assertEqual(negative,8)
        self.receipt('controls',dict(forms=len(forms),ordinary_executions=ordinary,effective_negatives=negative,
            all_controls_execute_without_exceptions=True,measurements=records))

    def test_07_copied_owner_real_padder_and_independent_symbol_rebases(self):
        source=(self.root/SOURCE).read_text()
        if screen.SELECTED in source:
            source=source.replace(screen.SELECTED,screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        candidate=source.replace(screen.ORIGINAL,screen.SELECTED)
        if screen.DECLARATIONS not in candidate:
            candidate=candidate.replace('void func_1501C17C',screen.DECLARATIONS+'void func_1501C17C')
        objects=[]
        for name,body in (('baseline',source),('selected',candidate)):
            obj,warnings=compile_owner(self.root,self.out,body,'owner-'+name)
            self.assertEqual(warnings,[])
            processed=self.out/('owner-'+name+'-processed.o')
            processed.write_bytes(obj.read_bytes())
            cfile=self.out/('owner-'+name+'.c')
            subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),
                '-O2','-g3',str(cfile.relative_to(self.root/'conker')),'--post-process',
                str(processed.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(processed)
        old,previous,old_rel=parse_object(objects[0])
        text,current,rel=parse_object(objects[1])
        self.assertEqual(current.keys(),previous.keys())
        for name,function in current.items():
            if name==screen.FUNCTION:
                continue
            before=previous[name]
            self.assertEqual(text[function['value']:function['value']+function['size']],
                old[before['value']:before['value']+before['size']],name)
            self.assertEqual({o-function['value']:r for o,r in rel.items() if function['value']<=o<function['value']+function['size']},
                {o-before['value']:r for o,r in old_rel.items() if before['value']<=o<before['value']+before['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        target=current[screen.FUNCTION]
        isolated,_,isolated_rel=parse_object(self.out/'selected.o')
        self.assertEqual(text[target['value']:target['value']+444],isolated[:444])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+444},isolated_rel)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            reader=csv.DictReader(stream)
            fields=reader.fieldnames
            guards=list(reader)
        assert_guard_history(self,guards)
        if len(guards)==11146:
            guards+=screen.owner_guards()
        else:
            self.assertEqual(guards[11146:11148],screen.owner_guards())
        manifest=self.out/'qualification-guards.csv'
        with manifest.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader()
            writer.writerows(guards)
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/205C90.s',
            word_patches_path=manifest,filename='generated_205C90')
        start=assembly.index('.type %s, @function'%screen.FUNCTION)
        end=assembly.index('.size %s, . - %s'%(screen.FUNCTION,screen.FUNCTION),start)
        end=assembly.index('\n',end)+1
        self.assertNotIn('.space',assembly[end:assembly.find('.type ',end)])
        asm,obj=self.out/'padded.s',self.out/'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n'%screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        _,functions,relocations=parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'],444)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        cases=0
        for index in range(6):
            entry=screen.ENTRY+(0x1000004 if index==1 else 0)
            symbols=screen.SYMBOLS.copy()
            if index>=2:
                for n,name in enumerate(symbols):
                    if name.startswith('D_'):
                        symbols[name]=(0x80007FFC,0xFFFF7FF8,0x7FFF8000,0x81018004)[index-2]+n*16
                    else:
                        symbols[name]+=index*0x100004
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>111I',sections(elf)['.text'][1]))
            for offset,rows in relocations.items():
                self.assertEqual(len(rows),1)
                kind,name=rows[0]
                value=symbols[name]
                expected=self.retail[offset//4]
                if kind=='R_MIPS_26':
                    expected=expected&0xFC000000|value>>2&0x3FFFFFF
                else:
                    value=(value+0x8000)>>16 if kind=='R_MIPS_HI16' else value
                    expected=expected&0xFFFF0000|value&65535
                self.assertEqual(words[offset//4],expected)
            for mask,limit,allocation,mode,phase in itertools.product((0,1,15,255),(-1,3),(0,RECORD),(0,2,5),(0,8)):
                self.compare(fixture(mask,limit,symbols=symbols),config=settings(allocation=allocation,mode=mode),
                    phase=phase,words=words,symbols=symbols,entry=entry)
                cases+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,strict_diagnostics=0,
            pools_relative_relocations_unchanged=True,padded_bytes=444,generated_filler_data=0,
            independent_links=6,rebased_executions=cases,all_18_symbolic_relocations_checked=True))

    def test_08_actual_complete_predicate_connection_and_current_linked_contract(self):
        actual=list(struct.unpack_from('>34I',self.rom,predicate.ROM))
        self.assertEqual((self.addresses[predicate.FUNCTION],self.functions[predicate.FUNCTION]),
                         (predicate.ENTRY,actual))
        self.assertEqual((self.addresses[screen.FUNCTION],self.functions[screen.FUNCTION]),
                         (screen.ENTRY,self.retail))
        connected=dict(zip(range(predicate.ENTRY,predicate.ENTRY+136,4),actual))
        cases=0
        for mask,mapping,state,limit,plan,allocation,phase in itertools.product(range(16),
                ((0,1,2,3),(255,0,1,2),(0,255,1,2),(3,2,1,0)),(0,1,5,15),(-1,0,3),
                ((15,0),(0,0),(15,15)),(0,RECORD),(0,8)):
            memory=fixture(mask,limit)
            for i,value in enumerate(mapping):
                put(memory,predicate.SYMBOLS['D_80084060']+i,value,1)
                put(memory,predicate.SYMBOLS['D_800BE944']+i,255 if state&(1<<i) else 0,1)
            self.compare(memory,config=settings(good=plan[0],bad=plan[1],allocation=allocation,actual_predicate=True),
                phase=phase,connected=connected)
            cases+=1
        source=(self.root/SOURCE).read_text()
        installed=screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertEqual(guards[11146:11148],screen.owner_guards() if installed else [])
        self.receipt('connected',dict(cases=cases,actual_complete_predicate_words=34,
            complete_constructor_words=111,linked_predicate_and_constructor_retail_exact=True,
            later_checks_allocator_memcpy_registration_are_controlled_boundaries=True,
            full_gameplay_hardware_not_claimed=True))

    def test_09_guard_history_preserves_prefix_and_rejects_unexpected_appends(self):
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            baseline=list(csv.DictReader(stream))[:11146]
        proposed=baseline+screen.owner_guards()
        before=assert_guard_history(self,baseline)
        after=assert_guard_history(self,proposed)
        malformed=[baseline[:-1],proposed[:-1],proposed+[dict(proposed[-1])]]
        for index,field,value in ((0,'replacement','0xFFFFFFFF'),
                (11145,'replacement','0xFFFFFFFF'),(11146,'replacement','0x11000002'),
                (11147,'expected_relocations','R_MIPS_LO16:D_80082FA0')):
            changed=[dict(row) for row in proposed]
            changed[index][field]=value
            malformed.append(changed)
        malformed.append(baseline+list(reversed(screen.owner_guards())))
        for manifest in malformed:
            with self.assertRaises(AssertionError):
                assert_guard_history(self,manifest)
        self.receipt('history',dict(original_rows=11146,appended_rows=2,
            accepted_sha256=(before,after),rejected_corrupt_manifests=len(malformed),
            complete_prior_history_remains_strict=True))




NATIVE = r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef unsigned int size_t;
#define NULL ((void *)0)
typedef char widths[sizeof(void *)==4&&sizeof(int)==4?1:-1];
u8 D_800E0B94,D_800BEAC0,D_800BEAC1,D_800BEAC2,D_800BEAC3;
s32 D_80082FA0;
static u8 storage[160];static u8 *owner=storage+32,*output;
static u32 goodMask,badMask,mode,allocationOK,trace[32][7],counts[6],callCount,failure;
enum {PREDICATE,CHECK,PRIOR,ALLOCATE,COPY,REGISTER};
static void push(u32 kind,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){
    u32 *row,i;
    if(callCount>=32){failure=1;return;}
    row=trace[callCount++];
    row[0]=kind;row[1]=a;row[2]=b;row[3]=c;row[4]=d;row[5]=e;row[6]=f;
    for(i=0;i<7;i++)row[i]&=0xFFFFFFFFu;
}
static void change(u32 kind){
    u32 index=counts[kind]++,i;
    static const u8 bytes[]={2,0xA5,0xFE,0xDC,127,15,0,0x91};
    if(mode==1&&kind==PREDICATE){owner[5]=15;D_80082FA0=1;D_800BEAC2=1;}
    if(mode==2&&kind==CHECK&&index==0){owner[5]=14;D_80082FA0=3;owner[4]=255;}
    if(mode==3&&kind==PRIOR&&index==0)D_80082FA0=-1;
    if(mode==4&&kind==ALLOCATE)for(i=0;i<8;i++)owner[i]=bytes[i];
    if(mode==5&&kind==REGISTER&&index==0){output[19]=0;owner[4]=128;}
    if(mode==6&&kind==REGISTER){output[19]=15;owner[4]++;}
}
s32 func_151D87E0(u8 mask){push(PREDICATE,mask,0,0,0,0,0);change(PREDICATE);return 1;}
s32 func_15181CC8(s32 player){
    s32 result=goodMask&(1u<<player)?(goodMask&16?(s32)0x80000000u:1):0;
    push(CHECK,player,0,0,0,0,0);change(CHECK);return result;
}
s32 func_1517EF00(s32 player){
    s32 result=badMask&(1u<<player)?(s32)0xFFFFFFFFu:0;
    push(PRIOR,player,0,0,0,0,0);change(PRIOR);return result;
}
void *func_15167A68(s32 kind,s32 context,s32 bytes,s32 flag,u8 slot,u8 pool){
    push(ALLOCATE,kind,context,bytes,flag,slot,pool);change(ALLOCATE);
    return allocationOK?output:NULL;
}
void *memcpy(void *destination,const void *source,size_t size){
    u8 *d=destination;const u8 *s=source;u32 i;
    push(COPY,(u32)d,(u32)s,size,0,0,0);
    if(size>16){failure=2;return d;}
    for(i=0;i<size;i++)d[i]=s[i];
    change(COPY);return d;
}
void func_1501C010(u8 player,u8 level){push(REGISTER,player,level,0,0,0,0);change(REGISTER);}
'''

NATIVE_REFERENCE = r'''
static u8 *(*volatile invoke)(u8 *,s32,u8,s32)=func_151D8868;
static u8 *expected_flow(s32 bytes,u8 slot,s32 context){
    u32 i=0;u8 *result;
    if(D_800E0B94)return NULL;
    if(!func_151D87E0(owner[5]))return NULL;
    if(D_800BEAC0)return NULL;
    if(D_800BEAC1)return NULL;
    if(D_800BEAC2)return NULL;
    if(D_800BEAC3)return NULL;
    while((s32)i<=D_80082FA0){
        if(owner[5]&(1u<<i)){
            if(!func_15181CC8(i))return NULL;
            if(func_1517EF00(i))return NULL;
        }
        i++;
    }
    result=func_15167A68(63,context,bytes+24,1,slot,1);
    if(!result)return NULL;
    memcpy(result+14,owner,8);
    i=0;
    while(i!=4){
        if(result[19]&(1u<<i))func_1501C010(i,owner[4]);
        i++;
    }
    result[22]=owner[4];
    return result;
}
static void initialize(u32 mask,s32 limit,u32 good,u32 bad,u32 allocate,u32 changeMode,u32 alias){
    u32 i;
    for(i=0;i<160;i++)storage[i]=0xA5;
    owner[0]=1;owner[2]=0x12;owner[3]=0x34;owner[4]=8;owner[5]=(u8)mask;owner[6]=255;owner[7]=0x5A;
    output=alias==1?owner-5:alias==2?owner+16:storage+80;
    D_800E0B94=D_800BEAC0=D_800BEAC1=D_800BEAC2=D_800BEAC3=0;
    D_80082FA0=limit;goodMask=good;badMask=bad;allocationOK=allocate;mode=changeMode;
    callCount=failure=0;for(i=0;i<6;i++)counts[i]=0;
}
static int verify(u32 mask,s32 limit,u32 good,u32 bad,u32 allocate,u32 changeMode,u32 alias,
                  u32 slot,s32 bytes,u32 context){
    u8 expected[160],globals[5];u32 expectedTrace[32][7],count,i,j,result; s32 liveLimit;
    initialize(mask,limit,good,bad,allocate,changeMode,alias);
    result=(u32)expected_flow(bytes,(u8)slot,(s32)context);
    if(failure)return 1;
    count=callCount;liveLimit=D_80082FA0;
    globals[0]=D_800E0B94;globals[1]=D_800BEAC0;globals[2]=D_800BEAC1;globals[3]=D_800BEAC2;globals[4]=D_800BEAC3;
    for(i=0;i<160;i++)expected[i]=storage[i];
    for(i=0;i<count;i++)for(j=0;j<7;j++)expectedTrace[i][j]=trace[i][j];
    initialize(mask,limit,good,bad,allocate,changeMode,alias);
    if((u32)invoke(owner,bytes,(u8)slot,(s32)context)!=result||failure||callCount!=count)return 2;
    if(D_80082FA0!=liveLimit||D_800E0B94!=globals[0]||D_800BEAC0!=globals[1]||D_800BEAC1!=globals[2]
       ||D_800BEAC2!=globals[3]||D_800BEAC3!=globals[4])return 3;
    for(i=0;i<160;i++)if(storage[i]!=expected[i])return 4;
    for(i=0;i<count;i++)for(j=0;j<7;j++)if(trace[i][j]!=expectedTrace[i][j])return 5;
    return 0;
}
'''


if __name__=='__main__':
    unittest.main()
