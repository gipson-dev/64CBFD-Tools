"""Setup defaults: ordered stores, independent draws, aliases, and the retail ABI."""
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_setup_byte_defaults_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_random_selector_outputs_match as prior
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_indexed_state_save_match import external,events
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

ROOT=Path(__file__).resolve().parents[2]
RANDOM=0x150ADA20
CALLER,CALLER_ROM,CALLER_WORDS=0x1518D6E0,0x1BAB90,750
WINDOW,WINDOW_END,TABLE,FACTORY=0x1518DEA4,0x1518DF54,0x8008D620,0x1513D524
OWNER,NODES=0x33000,0x40000

def reference(memory,arguments,randoms,mode=0,mutation=0,random_address=RANDOM):
    m=dict(memory);trace=[];calls=[];number=0
    def read(address,size):
        value=int.from_bytes(bytes(m[address+i]for i in range(size)),'big')
        trace.append(('R',address,size,value));return value
    def write(address,value,size):
        prior.put(m,address,value,size)
        trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def random():
        nonlocal number
        calls.append((random_address,prior.snapshot(m)));trace.append(('CALL',random_address))
        if mode==2:
            value=prior.next_seed(read(prior.SEED,8));write(prior.SEED,value,8)
        else:
            value=randoms[number]
            for address,word,size in prior.changes(arguments,number,mutation):write(address,word,size)
        number+=1;return value&0xFFFFFFFF
    write(arguments[1],2,1)
    if random()&1:write(arguments[1],read(arguments[1],1)|1,1)
    value=random();write(arguments[0],0x14 if value&1 else 0x13,1)
    for address in arguments[2:5]:write(address,0,1)
    write(arguments[5],255,1);write(arguments[6],0x301,2)
    return external(m),trace,calls,value

class SetupOracle(prior.RandomOutputsOracle):
    def __init__(self,words,memory,arguments,randoms=(),mode=0,mutation=0,phase=0,
                 entry=source.ENTRY,random_address=RANDOM,random_words=(),fault=None,connected=None):
        self.in_instruction=False;self.current_pc=None;self.delay_of=None;self.root_accesses=0
        self.root_fault=fault;self.root_entry=entry;self.dispatched_word=0
        code=dict(connected or {})
        if mode==2:code.update({random_address+i*4:w for i,w in enumerate(random_words)})
        TriangleOracle.__init__(self,words,memory,entry=entry,arguments=arguments,phase=phase,connected=code)
        self.outputs,self.randoms,self.mutation,self.number=arguments,randoms,mutation,0
        self.random_address=random_address;self.hi=self.lo=0
        self.code=faults.TrackedCode(self.code,self)

    def execute(self,word):
        self.dispatched_word=word;self.in_instruction=True
        try:return super().execute(word)
        finally:self.in_instruction=False

    def access(self):
        if self.in_instruction and self.current_pc is not None and self.root_entry<=self.current_pc<self.root_entry+source.SIZE:
            if self.root_accesses==self.root_fault:raise faults.AccessBoundary
            self.root_accesses+=1

    def get(self,address,size):
        self.access();return super().get(address,size)

    def put(self,address,value,size):
        self.access();return super().put(address,value,size)

    def record_call(self,target):
        assert target==self.random_address
        self.calls.append((target,prior.snapshot(self.memory)));self.events.append(('CALL',target))

    def hook(self,target):
        assert target==self.random_address
        value=self.randoms[self.number]
        for address,word,size in prior.changes(self.outputs,self.number,self.mutation):self.put(address,word,size)
        self.number+=1
        for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.r[2]=value;self.f[:20]=[0xA5000000+i for i in range(20)]

class WindowBoundary(Exception):pass

class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==WINDOW_END:raise WindowBoundary
        return super().__getitem__(pc)

class CallerOracle(SetupOracle):
    def __init__(self,caller,target,memory,randoms,phase=0,selection=0,count=1,mode=0,rng=(),mutation=0):
        connected={source.ENTRY+i*4:w for i,w in enumerate(target)}
        SetupOracle.__init__(self,caller,memory,(),randoms,mode,mutation,phase,
            entry=CALLER,random_words=rng,connected=connected)
        self.entry=WINDOW;self.root_entry=source.ENTRY;self.caller_sp=self.r[29]
        self.outputs=tuple(self.caller_sp+n for n in(0x10C,0xAE,0x11C,0x11D,0x11E,0x11F,0x10E))
        self.r[2]=selection;self.r[17]=NODES;self.r[22]=OWNER;self.r[30]=count-1
        self.code=WindowCode(dict(self.code),self);self.dispatches=[];self.factory=[]

    def execute(self,word):
        op,rs,rt,rd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
        if op==0 and fn==27:
            left,right=self.r[rs]&0xFFFFFFFF,self.r[rt]&0xFFFFFFFF
            assert right!=0,'Unqualified zero-divisor caller path'
            self.lo,self.hi=left//right,left%right;return
        if op==0 and fn==16:
            self.r[rd]=self.hi;return
        return super().execute(word)

    def frame_snapshot(self):
        return bytes(self.memory[self.caller_sp+i]for i in range(0xA0,0x152))

    def record_call(self,target):
        if target==source.ENTRY:
            args=self.arguments(7);self.dispatches.append(args)
            self.calls.append((target,args));self.events.append(('CALL',target,args))
        elif target==FACTORY:
            args=self.arguments(9);self.factory.append((args,self.frame_snapshot(),self.r[29],self.r[17],self.r[22]))
            self.calls.append((target,args));self.events.append(('CALL',target,args))
        else:
            assert target==RANDOM
            self.calls.append((target,self.frame_snapshot(),prior.snapshot(self.memory)))
            self.events.append(('CALL',target))

    def hook(self,target):
        if target!=FACTORY:return super().hook(target)
        for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.r[2]=0;self.f[:20]=[0xA5000000+i for i in range(20)]

def native_harness(body):
    def offset(a):
        return a-prior.OUTPUT if a<prior.OUTPUT+64 else a-prior.SEED+80 if prior.SEED<=a<prior.SEED+8 else a-prior.TABLE+128
    layouts=','.join('{'+','.join(str(offset(a))for a in row)+'}'for row in prior.LAYOUTS)
    values=','.join('0x%08XU'%v for v in prior.RANDOM_WORDS)
    seeds=','.join('0x%016XULL'%v for v in prior.SEEDS)
    return '''typedef unsigned char u8;typedef short s16;typedef int s32;
typedef unsigned int u32;typedef unsigned long long u64;
static union{u64 align;u8 b[256];s16 half[128];u64 seed[32];}actual,expected;
static int mode,mutation,number,ac,ec,error,offsets[7];
static u32 draws[2];static u8 snapshots[2][256],wanted[2][256];
static u64 next(u64 s){u64 t=((s&1)<<32)|((s>>1)&0xFFFFFFFF);t^=(s&0xFFFFF)<<12;return t^((t>>20)&0xFFF);}
static u32 draw(int want){
 u8*p=want?expected.b:actual.b;int i,n=want?ec++:ac++;u32 value;
 if(n>=2){error=1;return 0;}
 for(i=0;i<256;i++)(want?wanted:snapshots)[n][i]=p[i];
 if(mode){u64 v=next(want?expected.seed[10]:actual.seed[10]);if(want)expected.seed[10]=v;else actual.seed[10]=v;value=(u32)v;}
 else{value=draws[number];if(mutation){if(!number)p[offsets[1]]=0x80;else p[offsets[0]]=0xA7;}}
 number++;return value;
}
s32 func_150ADA20(void){return(s32)draw(0);}
static void reference(void){u8*p=expected.b;
 p[offsets[1]]=2;if(draw(1)&1)p[offsets[1]]|=1;
 p[offsets[0]]=(draw(1)&1)?0x14:0x13;
 p[offsets[2]]=0;p[offsets[3]]=0;p[offsets[4]]=0;
 p[offsets[5]]=0xFF;expected.half[offsets[6]/2]=0x301;
}
'''+body+'\nstatic int layouts[][7]={'+layouts+'};static u32 values[]={'+values+'};static u64 seeds[]={'+seeds+'};\n'+'''
int run(void){int m,a,b,l,k,i,j,count=0;
 if(sizeof(void*)!=4||sizeof(s16)!=2||sizeof(actual)!=256)return 22;
 for(m=0;m<2;m++)for(a=0;a<(m?4108:8);a++)for(b=0;b<(m?1:8);b++)
 for(l=0;l<(m&&a>=12?1:16);l++)for(k=0;k<(m?1:2);k++){
  mode=m;mutation=k;draws[0]=values[a%8];draws[1]=values[b];
  for(i=0;i<256;i++)actual.b[i]=(u8)(i*17+count*83);
  actual.seed[10]=m&&a>=12?(u64)(a-12):seeds[a%12];
  for(i=0;i<7;i++)offsets[i]=layouts[l][i];
  for(i=0;i<256;i++)expected.b[i]=actual.b[i];
  number=ac=ec=error=0;reference();number=0;
  func_1518E524(actual.b+offsets[0],actual.b+offsets[1],actual.b+offsets[2],
   actual.b+offsets[3],actual.b+offsets[4],actual.b+offsets[5],&actual.half[offsets[6]/2]);
  if(error||ac!=2||ec!=2)return 23;
  for(i=0;i<256;i++)if(actual.b[i]!=expected.b[i])return 23;
  for(i=0;i<2;i++)for(j=0;j<256;j++)if(snapshots[i][j]!=wanted[i][j])return 23;
  count++;
 }
 if(count!=6336)return 24;return 0;
}
'''+START

def controls():
    body=source.SELECTED
    return dict(wrong_bit=body.replace('& 1','& 2',1),wrong_flags=body.replace('*flags = 2;','*flags = 0;'),
        wrong_kind=body.replace('*kind = 0x13;','*kind = 0x15;'),missing_flag=body.replace('*flags |= 1;','*flags |= 0;'),
        tail_order=body.replace('    *alpha = 0xFF;\n    *mode = 0x301;','    *mode = 0x301;\n    *alpha = 0xFF;'),
        one_draw=body.replace('    *flags = 2;','    s32 saved;\n    *flags = 2;\n    saved = func_150ADA20();').replace('func_150ADA20() & 1','saved & 1'))

class SetupByteDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD;cls.values=source.snapshot(cls.output)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.audit_inputs(ROOT,cls.output)if cls.installed else source.freeze(ROOT,cls.output)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>45I',cls.rom,source.ROM))
        linked,functions=source.link_owner(ROOT,cls.output,cls.output/'qualified-after-owner.o',source.OWNER)
        cls.words=list(struct.unpack_from('>45I',linked,functions[source.FUNCTION]['value']))
        cls.rng=list(struct.unpack_from('>18I',cls.rom,0xDAED0))
        cls.palette=cls.rom[0x2275E0+prior.TABLE-0x80082B20:0x2275E0+prior.TABLE-0x80082B20+60]
        cls.receipt={}

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')

    def test_01_direct_owner_Make_and_complete_word_binding_guards(self):
        source.checked_payload(*source.payload(self.output/'qualified-after-owner.o'))
        self.assertEqual(self.words,self.truth)
        q=json.loads((self.output/'qualification.json').read_text());m=json.loads((self.output/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(45,24,2,0,60))
        self.assertEqual(m['actual_Make_commands'],3)
        raw,bindings=source.payload(self.output/'qualified-after-owner.o')
        for i in range(45):
            bad=bytearray(raw);bad[4*i]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','unknown')]
            with self.assertRaises(ValueError):source.checked_payload(raw,bad)
        self.receipt.update(words=45,frame=24,bindings=2,new_guards=0,preserved_neighbors=60,word_controls=45,binding_controls=2,
            compiler_only=True,typed_void_seven_pointer_interface=True,inherited_owner_warnings=4)

    def compare(self,memory,layout,randoms=(),mode=0,mutation=0,phase=0,entry=source.ENTRY,random_address=RANDOM,images=None):
        expected=reference(memory,layout,randoms,mode,mutation,random_address)
        models=[SetupOracle(w,memory,layout,randoms,mode,mutation,phase,entry,random_address,self.rng).run()
            for w in(images or(self.truth,self.words))]
        for m in models:self.assertEqual((external(m.memory),events(m),m.calls,m.r[2]&0xFFFFFFFF),expected)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0].visits

    def test_02_guest_independent_draws_aliases_mutations_and_actual_rng(self):
        visits=set();opaque=connected=0
        for first,second,layout,mutation,phase in itertools.product(prior.RANDOM_WORDS,prior.RANDOM_WORDS,prior.LAYOUTS,(0,1),(0,8)):
            m=prior.memory_case(prior.SEEDS[9],opaque%3,self.palette)
            visits.update(self.compare(m,layout,(first,second),mutation=mutation,phase=phase));opaque+=1
        for seed,layout,phase in itertools.chain(itertools.product(prior.SEEDS,prior.LAYOUTS,(0,8)),itertools.product(range(4096),(prior.NORMAL,),(0,8))):
            m=prior.memory_case(seed,connected%3,self.palette)
            visits.update(self.compare(m,layout,mode=2,phase=phase));connected+=1
        self.assertEqual((opaque,connected),(4096,8576))
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+180,4))-{source.ENTRY+92,source.ENTRY+96}|set(range(RANDOM,RANDOM+72,4)))
        self.receipt.update(opaque_guest_phases=opaque,connected_RNG_guest_phases=connected,reachable_wrapper_words=43,
            retained_unreachable_switch_offsets=[92,96],all_18_rng_words_visited=True,complete_GPR_FPR_HI_LO_RAM_events=True,
            output_seed_table_alias_layouts=16,independent_draws_and_live_callback_writes=True)

    def test_03_native32_profiles_and_effective_controls(self):
        exits={}
        cases=[('O0','-O0',source.SELECTED,True),('O2','-O2',source.SELECTED,True),('O3','-O3',source.SELECTED,True)]
        cases.extend((n,'-O2',b,False)for n,b in controls().items())
        for label,opt,body,valid in cases:
            p=self.output/('native-qualified-'+label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('')
            a=subprocess.run([*native_command(opt,valid),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(a.returncode,0,a.stdout+a.stderr)
            a=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
            self.assertEqual(a.returncode,0 if valid else 23,(label,a.stdout,a.stderr));exits[label]=a.returncode
        self.receipt.update(native32=exits,native_cases_per_profile=6336,trap_UBSan=True,full_256_bytes_and_two_snapshots=True,
            explicit_native_stack_realign=True,declared_union_halfword_and_seed_views=True,
            portable_guest_alias_or_endian_equivalence_not_claimed=True)

    def test_04_actual_indirect_call_window_and_retained_rng(self):
        caller=list(struct.unpack_from('>750I',self.rom,CALLER_ROM))
        obj=source.original(ROOT,self.output,'func_1518D6E0')
        linked,fn=source.link_owner(ROOT,self.output,obj,source.OWNER)
        self.assertEqual(list(struct.unpack_from('>750I',linked,fn['func_1518D6E0']['value'])),caller)
        current,_,addresses=source.load_elf_functions(str(ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual(addresses['func_150ADA20'],RANDOM);self.assertEqual(current['func_150ADA20'],self.rng)
        from tools.check_game_data_layout import load_section
        at,data=load_section(self.output/'before-conker_build_conker.us.elf','.game_data')
        self.assertEqual(struct.unpack_from('>2I',data,TABLE-at),(source.ENTRY,0x1518E5D8))
        jal=0x0C000000|((source.ENTRY>>2)&0x03FFFFFF)
        self.assertEqual([i for i in range(0,len(self.rom)-3,4)if struct.unpack_from('>I',self.rom,i)[0]==jal],[])
        self.assertEqual([i for i in range(0,len(self.rom)-3,4)if struct.unpack_from('>I',self.rom,i)[0]==source.ENTRY],[0x2320E0])
        phases=0;visits=set()
        for count,selection,first,second,phase,mode,mutation in itertools.product((1,2,4),(0,1,3,0xFFFFFFFF),(0,1),(0,1),(0,8),(0,2),(0,1)):
            if mode and mutation:continue
            m=prior.memory_case(prior.SEEDS[9],phases%3,self.palette)
            m.update({prior.STACK+i:(i*17+phases)&255 for i in range(-0x600,0x300)})
            m.update({OWNER+i:(i*13+phases)&255 for i in range(0x60)})
            m[OWNER+0x3F]=0;m[OWNER+0x38]=7;m[OWNER+0x39]=0x80;m[OWNER+0x3A]=255
            for i in range(count):prior.put(m,NODES+i*0x20+0x14,NODES+(i+1)*0x20 if i+1<count else 0,4)
            prior.put(m,TABLE,source.ENTRY,4);prior.put(m,TABLE+4,0x1518E5D8,4)
            models=[CallerOracle(caller,w,m,(first,second),phase,selection,count,mode,self.rng,mutation)for w in(self.truth,self.words)]
            for model in models:
                with self.assertRaises(WindowBoundary):model.run()
                model.visits.discard(WINDOW_END)
                csp=prior.STACK+phase;args=tuple(csp+n for n in(0x10C,0xAE,0x11C,0x11D,0x11E,0x11F,0x10E))
                self.assertEqual(model.dispatches,[args]);self.assertEqual(len(model.factory),1)
                seed=int.from_bytes(bytes(m[prior.SEED+i]for i in range(8)),'big')
                if mode:
                    seed=prior.next_seed(seed);one=seed&1;seed=prior.next_seed(seed);two=seed&1
                else:one,two=first,second
                flags=(0x80 if mutation else 2)|(1 if one else 0)
                self.assertEqual(model.memory[csp+0xAE],flags)
                self.assertEqual(model.memory[csp+0x10C],0x14 if two else 0x13)
                self.assertEqual(bytes(model.memory[csp+i]for i in range(0x11C,0x120)),bytes((0,0,0,255)))
                self.assertEqual(bytes(model.memory[csp+i]for i in(0x10E,0x10F)),b'\x03\x01')
                self.assertEqual(model.memory[csp+0x10D],m[csp+0x10D])
                self.assertEqual(bytes(model.memory[csp+i]for i in range(0x110,0x11C)),bytes(m[csp+i]for i in range(0x110,0x11C)))
                self.assertEqual(model.factory[0][0],(csp+0x10C,7,0x80,0,255,flags,0x58,255,0))
                self.assertEqual(model.factory[0][2:],(csp,NODES+(selection%count)*0x20,OWNER))
                self.assertIn(0x1518DF1C,model.visits);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(actual_dispatch_window_phases=phases,full_original_caller_words_locked=750,
            caller_window=[WINDOW,WINDOW_END],seven_pointer_ABI=True,two_entry_table_slot=0,
            actual_factory_submission_ABI_observed=True,retained_caller_stub_unmodified_uncredited=True,
            complete_original_caller_entry_return_or_gameplay_acceptance_claimed=False)

    def rebased(self,obj,entry,random_address,label):
        text,fn,rel=source.parse_object(obj);symbols={'func_150ADA20':random_address}
        assembly,unknown=emit_function(text,fn[source.FUNCTION],rel,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.output/label;p.with_suffix('.s').write_text(assembly)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            '--defsym=func_150ADA20=0x%X'%random_address,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>45I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_05_independent_GNU_links_and_fired_target_fault_prefixes(self):
        objects=(source.original(ROOT,self.output),self.output/'qualified-padded.o',self.output/'make-shadow/src/game/generated_1BA1D0.c.o')
        phases=cuts=aliases=0
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            random_address=RANDOM if not i else entry+0x10004
            images=[self.rebased(obj,entry,random_address,'gnu-%d-%d'%(i,j))for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for first,second,phase in itertools.product((0,1,0xFFFFFFFF),(0,1,0xFFFFFFFF),(0,8)):
                m=prior.memory_case(1,phases%3,self.palette)
                self.compare(m,prior.LAYOUTS[phases%16],(first,second),mutation=1,phase=phase,entry=entry,
                    random_address=random_address,images=images[:2]);phases+=1
        for which,first,phase in itertools.product((1,5),(0,1),(0,8)):
            m=prior.memory_case(1,2,self.palette);layout=list(prior.NORMAL)
            layout[which]=prior.STACK+phase+(4 if which==1 else 0x18)
            if which==5:
                prior.put(m,0xFF020006,0xA5A5,2)
            models=[SetupOracle(w,m,tuple(layout),(first,0),phase=phase).run()for w in(self.truth,self.words)]
            self.assertEqual(complete(models[0]),complete(models[1]))
            if which==5:
                self.assertEqual(bytes(models[0].memory[0xFF020006+i]for i in range(2)),b'\x03\x01')
                self.assertEqual(bytes(models[0].memory[prior.NORMAL[6]+i]for i in range(2)),bytes(m[prior.NORMAL[6]+i]for i in range(2)))
            aliases+=1
        for layout,randoms,phase in itertools.product((prior.NORMAL,prior.LAYOUTS[1],prior.LAYOUTS[-1]),((0,0),(1,1)),(0,8)):
            m=prior.memory_case(1,2,self.palette)
            count=SetupOracle(self.truth,m,layout,randoms,mutation=1,phase=phase).run().root_accesses
            for cut in range(count):
                models=[SetupOracle(w,m,layout,randoms,mutation=1,phase=phase,fault=cut)for w in(self.truth,self.words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of,models[0].dispatched_word),
                    (models[1].current_pc,models[1].delay_of,models[1].dispatched_word));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebased_phases=phases,guest_argument_home_alias_phases=aliases,
            fired_target_access_fault_prefixes=cuts,
            target_relocations_are_only_R_MIPS_26=True,portable_C_fault_MMU_or_hardware_acceptance_claimed=False)

    def test_06_strict_full_image_and_frozen_input_controls(self):
        values=source.snapshot(self.output);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
        actual=(self.output/'first-linked.elf').read_bytes();source.check_image(before,actual,truth)
        at=source.elf_slot_offset(before,source.ENTRY,source.SIZE)
        symbol=next(off for off,name,fields,_ in source.symbol_rows(before)if name==source.FUNCTION and fields[1]==source.ENTRY)
        for offset in(0,at,at+179,at+180,len(actual)-1,symbol+8):
            bad=bytearray(actual);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,actual+b'\0',truth)
        with self.assertRaises(ValueError):source.checked_payload(*source.payload(self.output/'before-padded.o'))
        for name in(source.SOURCE,source.OBJECT,source.ASM,'conker/asm/data/2320A0.rodata.s',
                'conker/retail_word_patches.us.csv','conker/src/game_DAE50.c'):
            target=self.output/('before-'+name.replace('/','_'));original=Path.read_bytes
            def changed(p):
                data=original(p);return bytes([data[0]^1])+data[1:]if p==target else data
            with patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):source.snapshot(self.output)
        self.receipt.update(strict_image_controls=7,frozen_input_controls=6,old_stub_rejected=True,metadata_exclusions=0)
