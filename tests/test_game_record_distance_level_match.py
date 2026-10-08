"""Complete record distance/level recovery with bounded conversion semantics."""

import csv
import itertools
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_distance_level_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_point_transform_match import put, read

OWNER, PARAMETERS, ORIGIN, ALTERNATE, OTHER = 0x20000, 0x21000, 0x22000, 0x23000, 0x24000
LOOKUP, MAGNITUDE = screen.SYMBOLS.values()
WRAPPER, WRAPPER_ROM = 0x151D8BE0, 0x206090
SOURCE = 'conker/src/game/generated_205C90.c'


def rounded(value):
    return floating(bits(value))


def public(memory):
    return {a:v for a,v in memory.items() if not prior.STACK-0x600 <= a < prior.STACK+0x140}


def fixture(player=0, fields=(4.0, 6.0, 8.0, 2.0, 3.0, 1.0/3.0), parameters=PARAMETERS):
    memory = {prior.STACK+i:0xA5 for i in range(-0x600,0x140)}
    for base in (OWNER, PARAMETERS, ORIGIN, ALTERNATE, OTHER):
        memory.update({base+i:0xA5 for i in range(64)})
    for base,values in ((parameters,fields), (ALTERNATE,(10.,20.,30.,1.,8.,.125)),
                        (ORIGIN,(1.,2.,3.))):
        for i,value in enumerate(values):
            put(memory,base+i*4,bits(value))
    put(memory,parameters+0x18,player,1)
    return memory


def actions(call, mode, parameters, stack):
    if mode == 1:
        if call == LOOKUP:
            return [(parameters+i*4,bits(v),4) for i,v in enumerate((11.,13.,17.))]
        return [(parameters+12+i*4,bits(v),4) for i,v in enumerate((1.,8.,.125))]
    if mode == 2:
        return [(stack+0x3C,ALTERNATE,4)] if call == LOOKUP else [
            (stack+0x38,OTHER,4),(stack+0x3C,ALTERNATE,4)]
    return []


def reference(memory, args, distance, mode=0, phase=0, frame=0x38):
    memory = memory.copy()
    owner,parameters = args
    events,calls = [],[]
    stack = prior.STACK+phase-frame

    def get(address,size=4):
        value=read(memory,address,size)
        events.append(('R',address,size,value))
        return value

    def mutate(call):
        nonlocal owner,parameters
        for address,value,size in actions(call,mode,parameters,stack):
            put(memory,address,value,size)
            if not prior.STACK-0x600 <= address < prior.STACK+0x140:
                events.append(('W',address,size,value))
        if mode==2:
            parameters=ALTERNATE
            if call==MAGNITUDE:
                owner=OTHER

    player=get(parameters+0x18,1)
    calls.append((LOOKUP,player))
    events.append(('CALL',LOOKUP,(player,)))
    mutate(LOOKUP)
    delta=[]
    for i in range(3):
        origin=floating(get(ORIGIN+i*4))
        coordinate=floating(get(parameters+i*4))
        delta.append(bits(coordinate-origin))
    calls.append((MAGNITUDE,tuple(delta)))
    events.append(('CALL',MAGNITUDE,(tuple(delta),)))
    mutate(MAGNITUDE)
    inner=floating(get(parameters+12))
    if distance < inner:
        level=1.0
    else:
        width=floating(get(parameters+16))
        if rounded(inner+width) < distance:
            level=0.0
        else:
            inverse=floating(get(parameters+20))
            level=rounded(1.0-rounded(rounded(distance-inner)*inverse))
    scaled=rounded(level*8.0)
    if math.isfinite(scaled):
        value=math.trunc(scaled)
        result=value&255 if 0<=value<2**32 else 255
    else:
        result=255
    put(memory,owner+0x12,result,1)
    events.append(('W',owner+0x12,1,result))
    return public(memory),calls,events


class DistanceOracle(AreaOracle):
    def __init__(self,words,memory,args=(OWNER,PARAMETERS),distance=3.0,mode=0,
                 phase=0,fcsr=0,entry=screen.ENTRY,connected=None,symbols=None,frame=0x38):
        super().__init__(words,memory,args,phase=phase,fcsr=fcsr,entry=entry,connected=connected)
        self.distance,self.mode=rounded(distance),mode
        self.parameters=args[1] if len(args)>1 else args[0]+0x18
        self.lookup,self.magnitude=(symbols or screen.SYMBOLS).values()
        self.frame=frame

    def execute(self,word):
        # Signed-cast negative controls use trunc.w.s, without changing FCSR.
        if word>>26==32:
            CopyOracle.execute(self,word)
        elif word>>26==17 and word>>21&31==16 and word&63==13:
            value=floating(self.f[word>>11&31])
            self.f[word>>6&31]=math.trunc(value)&0xFFFFFFFF if math.isfinite(value) and -(2**31)<=value<2**31 else 0x80000000
            self.r[0]=0
        else:
            super().execute(word)

    def record_call(self,target):
        if target in self.code:
            self.calls.append((target,*self.r[4:6]))
            return
        if target==self.lookup:
            call=(LOOKUP,self.r[4])
            event=('CALL',LOOKUP,(self.r[4],))
        else:
            assert target==self.magnitude,hex(target)
            delta=tuple(self.get(self.r[4]+i*4,4) for i in range(3))
            call=(MAGNITUDE,delta)
            event=('CALL',MAGNITUDE,(delta,))
        self.calls.append(call)
        self.events.append(event)

    def hook(self,target):
        call=LOOKUP if target==self.lookup else MAGNITUDE
        stack=self.r[29]
        for address,value,size in actions(call,self.mode,self.parameters,stack):
            self.put(address,value,size)
        if self.mode==2:
            self.parameters=ALTERNATE
        if self.mode==3 and call==LOOKUP:
            del self.memory[stack+0x3C]
        if self.mode==4 and call==MAGNITUDE:
            del self.memory[stack+0x38]
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if call==LOOKUP:
            self.r[2]=ORIGIN
        else:
            self.f[0]=bits(self.distance)


def public_events(model):
    return [e for e in model.events if e[0]=='CALL' or not prior.STACK-0x600<=e[1]<prior.STACK+0x140]


BOUNDARIES = tuple((d,2.,3.,rounded(1./3.)) for d in
    (-0.,0.,1.,floating(bits(2.)-1),2.,floating(bits(2.)+1),
     3.,floating(bits(5.)-1),5.,floating(bits(5.)+1),6.))
SPECIAL = (
    (0.,0.,0.,0.), (0.,0.,0.,math.nan), (0.,0.,0.,math.inf),
    (1.,0.,2.,1.), (1.,0.,2.,2.), (1.,0.,2.,-1.),
    (1.,0.,2.,1.-(2**31-128)/8), (1.,0.,2.,1.-2**31/8),
    (1.,0.,2.,1.-(2**32-256)/8), (1.,0.,2.,1.-2**32/8),
    (1.,0.,2.,1.-2**33/8), (1.,0.,2.,math.nan), (1.,0.,2.,math.inf),
    (1.,0.,2.,-math.inf), (math.nan,0.,2.,.5), (math.inf,0.,2.,.5),
    (-math.inf,0.,2.,.5), (3.,math.nan,2.,.5), (3.,2.,math.nan,.5),
    (5.,2.,3.,0.), (0.,-1.,2.,.5))


class GameRecordDistanceLevelTests(unittest.TestCase):
    run_host=prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-distance-level-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>87I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,player=0,case=BOUNDARIES[6],phase=0,fcsr=0,mode=0,parameters=PARAMETERS):
        distance,inner,width,inverse=map(rounded,case)
        memory=fixture(player,(4.,6.,8.,inner,width,inverse),parameters)
        expected=reference(memory,(OWNER,parameters),distance,mode,phase)
        models=[DistanceOracle(w,memory,(OWNER,parameters),distance,mode,phase,fcsr).run()
                for w in (self.words,self.retail)]
        for model in models:
            self.assertEqual((public(model.memory),model.calls,public_events(model)),expected)
            self.assertEqual(model.fcsr,fcsr)
        self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                         (models[1].r,models[1].f,models[1].events,models[1].memory))
        return models

    def test_01_complete_slot_and_symbolic_calls(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(87,0x38,0))
        self.assertEqual(self.words,self.retail)
        self.assertEqual(self.record['relocations'],{0x10:[('R_MIPS_26','func_15144B34')],
                                                   0x4C:[('R_MIPS_26','func_15143E64')]})
        self.assertEqual((self.record['pool_bytes'],self.record['diagnostics']),(0,''))
        self.receipt('slot',dict(words=87,bytes=348,frame=0x38,differences=0,guards_added=0,
                                complete_unsigned_conversion_and_FCSR_sequence=True))

    def test_02_all_byte_players_boundaries_and_conversion_branches(self):
        seen,cases=set(),0
        for player,case,phase,fcsr in itertools.product(range(256),BOUNDARIES+SPECIAL,(0,8),(0,3,0x123456)):
            for model in self.compare(player,case,phase,fcsr):
                seen.update(model.visits)
            cases+=1
        missing=set(range(screen.ENTRY,screen.ENTRY+348,4))-seen
        self.assertEqual(missing,{screen.ENTRY+0x80,screen.ENTRY+0xA4,screen.ENTRY+0x138})
        self.receipt('guest',dict(cases=cases,players=256,boundary_configurations=len(BOUNDARIES)+len(SPECIAL),
            SP_phases=2,FCSR_patterns=3,reachable_words=len(seen),unreachable_duplicate_words=sorted(missing),
            complete_GP_FP_ordered_trace_memory_equality=True,independent_public_semantic_reference=True,
            signed_unsigned_fallback_negative_NaN_Inf_branches=True,
            bounded_model_not_hardware_rounding_status_traps_or_NaN_payload_claim=True))

    def test_03_mutations_aliases_reload_and_fault_prefixes(self):
        cases=0
        for player,phase,mode,parameters in itertools.product((0,127,128,255),(0,8),range(3),
                                                            (PARAMETERS,OWNER+0x18,ORIGIN)):
            self.compare(player,BOUNDARIES[6],phase,mode=mode,parameters=parameters)
            cases+=1
        faults=0
        # Required player/coordinate/inner/width/inverse/output and stack gates.
        for phase,mode in itertools.product((0,8),(3,4)):
            models=[DistanceOracle(w,fixture(),mode=mode,phase=phase) for w in (self.words,self.retail)]
            for model in models:
                with self.assertRaises(AssertionError):
                    model.run()
            self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
            faults+=1
        for address,case in ((PARAMETERS+0x18,BOUNDARIES[6]),(ORIGIN,BOUNDARIES[6]),
                             (PARAMETERS+12,BOUNDARIES[6]),(PARAMETERS+16,BOUNDARIES[6]),
                             (PARAMETERS+20,BOUNDARIES[6]),(OWNER+0x12,BOUNDARIES[6])):
            memory=fixture()
            del memory[address]
            models=[DistanceOracle(w,memory,distance=case[0]) for w in (self.words,self.retail)]
            for model in models:
                with self.assertRaises(AssertionError):
                    model.run()
            self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
            faults+=1
        for missing,case in ((PARAMETERS+16,BOUNDARIES[0]),(PARAMETERS+20,BOUNDARIES[-1])):
            memory=fixture()
            del memory[missing]
            for words in (self.words,self.retail):
                model=DistanceOracle(words,memory,distance=case[0]).run()
                self.assertFalse(any(e[0]=='R' and e[1]==missing for e in model.events))
        self.receipt('gates',dict(mutation_alias_reload_cases=cases,required_fault_prefixes=faults,
            skipped_field_read_gates=2,parameter_owner_homes_reload_across_both_calls=True,
            private_home_mutation_is_emitted_instruction_evidence_not_portable_C=True))

    def test_04_native32_actual_complete_C_and_canaries(self):
        self.fixture=r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
''' + screen.DECLARATIONS + r'''
typedef char widths[sizeof(void *)==4&&sizeof(int)==4&&sizeof(f32)==4&&sizeof(RecordDistanceLevel)==28?1:-1];
typedef char player_offset[__builtin_offsetof(RecordDistanceLevel,player)==24?1:-1];
static u8 owner[64],expected[64];static RecordDistanceLevel p,saved;
static f32 origin[3],wanted[3],distance;static u32 mode,error,calls,player;
f32 *func_15144B34(s32 index){
    if(index!=(s32)player||calls++)error=1;
    if(mode){p.x=11.f;p.y=13.f;p.z=17.f;}
    return origin;
}
f32 func_15143E64(f32 *vector){
    u32 i;if(calls++!=1)error=1;
    for(i=0;i<3;i++)if(vector[i]!=wanted[i])error=1;
    if(mode){p.inner=1.f;p.width=8.f;p.inverseWidth=.125f;}
    return distance;
}
''' + screen.SELECTED + r'''
static void (*volatile invoke)(u8 *,RecordDistanceLevel *)=func_151D8C00;
'''
        self.run_host(r'''u32 c,i,j,count=0;f32 inner,width,inverse,level,scaled;
static const f32 distances[]={0.f,1.f,2.f,2.5f,3.f,4.5f,5.f,5.5f,6.f};
static const f32 scaled_limits[]={2147483520.f,2147483648.f,4294967040.f};
for(player=0;player<256;player++)for(c=0;c<12;c++)for(mode=0;mode<2;mode++){
    for(i=0;i<64;i++)owner[i]=expected[i]=0xA5;
    for(i=0;i<sizeof(p);i++)((u8 *)&p)[i]=0xA5;
    p.x=4.f;p.y=6.f;p.z=8.f;p.inner=2.f;p.width=3.f;p.inverseWidth=1.f/3.f;p.player=player;
    if(c>=9){p.inner=0.f;p.width=2.f;p.inverseWidth=1.f-scaled_limits[c-9]/8.f;}
    saved=p;origin[0]=1.f;origin[1]=2.f;origin[2]=3.f;distance=c<9?distances[c]:1.f;calls=error=0;
    wanted[0]=mode?10.f:3.f;wanted[1]=mode?11.f:4.f;wanted[2]=mode?14.f:5.f;
    inner=mode?1.f:p.inner;width=mode?8.f:p.width;inverse=mode?.125f:p.inverseWidth;
    if(distance<inner)level=1.f;else if(inner+width<distance)level=0.f;
    else level=1.f-(distance-inner)*inverse;
    scaled=level*8.f;if(!(scaled>=0.f&&scaled<4294967296.f))return 4;
    expected[18]=(u32)scaled;
    if(mode){saved.x=11.f;saved.y=13.f;saved.z=17.f;saved.inner=1.f;saved.width=8.f;saved.inverseWidth=.125f;}
    invoke(owner,&p);if(error||calls!=2)return 1;
    for(j=0;j<64;j++)if(owner[j]!=expected[j])return 2;
    for(j=0;j<sizeof(p);j++)if(((u8 *)&p)[j]!=((u8 *)&saved)[j])return 3;
    if(origin[0]!=1.f||origin[1]!=2.f||origin[2]!=3.f)return 5;
    count++;
}
if(count!=6144)return 6;
''')
        self.receipt('native',dict(cases=6144,players=256,configurations=12,mutation_modes=2,
            actual_complete_C_through_volatile_pointer=True,pointer_int_bytes=4,parameter_size=28,
            all_owner_parameter_origin_canaries_checked=True,defined_finite_nonnegative_u32_casts_only=True))

    def test_05_profiles_and_effective_compiled_negatives(self):
        forms=[('profile-'+p,screen.SELECTED,p) for p in PROFILES]
        forms += [(name,body,'o2g3') for name,body in (
            ('negative-player',screen.SELECTED.replace('parameters->player','(s8)parameters->player')),
            ('negative-output',screen.SELECTED.replace('owner[0x12]','owner[0x13]')),
            ('negative-scale',screen.SELECTED.replace('level * 8.0f','level * 7.0f')),
            ('negative-inner-gate',screen.SELECTED.replace('distance < parameters->inner','distance <= parameters->inner')),
            ('negative-outer-gate',screen.SELECTED.replace('parameters->width < distance','parameters->width <= distance')),
            ('negative-signed-cast',screen.SELECTED.replace('(u32)(level','(s32)(level')))]
        records,ordinary,negatives=[],0,0
        for name,body,profile in forms:
            record,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record)
            equal=[]
            for player,case in itertools.product((0,255),(BOUNDARIES[0],BOUNDARIES[6],SPECIAL[1],SPECIAL[8],SPECIAL[19])):
                distance,inner,width,inverse=map(rounded,case)
                memory=fixture(player,(4.,6.,8.,inner,width,inverse))
                model=DistanceOracle(words,memory,distance=distance).run()
                expected=reference(memory,(OWNER,PARAMETERS),distance)
                # Positive alternate profiles need public equivalence, not private schedule identity.
                equal.append((public(model.memory),model.calls)==expected[:2])
                ordinary+=not name.startswith('negative-')
            if name.startswith('negative-'):
                self.assertFalse(all(equal),name)
                negatives+=1
            else:
                self.assertTrue(all(equal),name)
        self.receipt('controls',dict(forms=len(records),ordinary_executions=ordinary,
                                    effective_negatives=negatives,measurements=records))

    def test_06_copied_owner_padder_and_independent_links(self):
        source=(self.root/SOURCE).read_text()
        if screen.SELECTED in source:
            source=source.replace(screen.SELECTED,screen.ORIGINAL)
        if screen.DECLARATIONS not in source:
            source=source.replace('s32 func_151D8C00();',screen.DECLARATIONS+
                '\nvoid func_151D8C00(u8 *owner, RecordDistanceLevel *parameters);')
            source=source.replace('func_151D8C00(record, record + 0x18);',
                'func_151D8C00(record, (RecordDistanceLevel *)(record + 0x18));')
        self.assertEqual(source.count(screen.ORIGINAL),1)
        objects=[]
        for name,body in (('baseline',source),('selected',source.replace(screen.ORIGINAL,screen.SELECTED))):
            obj,warnings=compile_owner(self.root,self.out,body,'owner-'+name)
            self.assertEqual(warnings,[])
            processed=self.out/('owner-'+name+'-postprocessed.o')
            shutil.copyfile(obj,processed)
            subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+name+'.c')).relative_to(self.root/'conker')),'--post-process',
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
        self.assertEqual(text[target['value']:target['value']+348],isolated[:348])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+348},isolated_rel)
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/205C90.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_205C90')
        start=assembly.index('.type %s, @function'%screen.FUNCTION)
        end=assembly.index('.size %s, . - %s'%(screen.FUNCTION,screen.FUNCTION),start)
        end=assembly.index('\n',end)+1
        self.assertNotIn('.space',assembly[end:assembly.find('.type ',end)])
        asm,obj=self.out/'padded.s',self.out/'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n'%screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        _,functions,relocations=parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'],348)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        bindings=[(screen.ENTRY,LOOKUP,MAGNITUDE),(screen.ENTRY+0x1000004,LOOKUP,MAGNITUDE),
                  (screen.ENTRY,LOOKUP+4,MAGNITUDE),(screen.ENTRY,LOOKUP,MAGNITUDE+4),
                  (screen.ENTRY,0x10000000,0x1FFFFFFC)]
        cases=0
        for index,(entry,lookup,magnitude) in enumerate(bindings):
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            symbols={'func_15144B34':lookup,'func_15143E64':magnitude}
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>87I',sections(elf)['.text'][1]))
            expected=self.words.copy()
            for offset,target in ((4,lookup),(19,magnitude)):
                expected[offset]=expected[offset]&0xFC000000|target>>2&0x3FFFFFF
            self.assertEqual(words,expected)
            for player,case in ((0,BOUNDARIES[0]),(255,BOUNDARIES[6]),(128,SPECIAL[8])):
                distance,inner,width,inverse=map(rounded,case)
                memory=fixture(player,(4.,6.,8.,inner,width,inverse))
                model=DistanceOracle(words,memory,distance=distance,entry=entry,symbols=symbols).run()
                self.assertEqual((public(model.memory),model.calls,public_events(model)),
                                 reference(memory,(OWNER,PARAMETERS),distance))
                cases+=1
        self.receipt('owner-padder',dict(unchanged_neighbors=len(current)-1,strict_diagnostics=0,
            unchanged_pools_and_relative_relocations=True,generated_padding_data=0,
            independent_links=len(bindings),rebased_executions=cases))

    def test_07_complete_actual_wrapper_helper_connection(self):
        wrapper=list(struct.unpack_from('>8I',self.rom,WRAPPER_ROM))
        cases=0
        for player,case,phase,mode in itertools.product((0,127,128,255),
                                                       (BOUNDARIES[0],BOUNDARIES[6],SPECIAL[8]),(0,8),(0,1)):
            distance,inner,width,inverse=map(rounded,case)
            memory=fixture(player,(4.,6.,8.,inner,width,inverse),OWNER+0x18)
            models=[]
            for words in (self.words,self.retail):
                code=dict(zip(range(screen.ENTRY,screen.ENTRY+348,4),words))
                model=DistanceOracle(wrapper,memory,args=(OWNER,),distance=distance,mode=mode,
                    phase=phase,entry=WRAPPER,connected=code).run()
                expected=reference(memory,(OWNER,OWNER+0x18),distance,mode,phase,frame=0x50)
                self.assertEqual((public(model.memory),model.calls[1:],public_events(model)),expected)
                self.assertEqual(model.calls[0],(screen.ENTRY,OWNER,OWNER+0x18))
                models.append(model)
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                             (models[1].r,models[1].f,models[1].events,models[1].memory))
            cases+=1
        self.receipt('connected',dict(cases=cases,actual_wrapper_words=8,complete_helper_words=87,
            unsigned_players=4,SP_phases=2,controlled_lookup_magnitude_interfaces=True,
            whole_caller_gameplay_actual_callees_and_hardware_not_claimed=True))

    def test_08_installed_or_original_and_guard_history(self):
        source=(self.root/SOURCE).read_text()
        installed=screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertFalse(any(row['function']==screen.FUNCTION for row in guards))
        functions,_,addresses=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION],functions[screen.FUNCTION]),(screen.ENTRY,self.retail))


if __name__=='__main__':
    unittest.main()
