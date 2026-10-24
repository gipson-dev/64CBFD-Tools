"""Signed lifetime ramps, literal multiply state and both original dispatch windows."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest

from tools.experiments import game_envelope_gates_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
EFFECT=0x30000
TIMES=(-32768,-32767,-1024,-256,-129,-128,-1,0,1,127,128,255,256,1024,32766,32767)
PRESETS=((0,0,0,0,0,0,0,0,0,0),
    (257,123,-100,-3,456,32767,-32768,17,-32768,-19),
    (1,-123,32767,513,-456,-100,-32768,-17,-32768,19),
    (9,7,-32768,11,13,-32768,32767,-32768,32767,32767),
    (3,123,0,7,456,0,-32768,1,-32768,1),
    (2,321,32767,13,654,32767,0,23,0,-29),
    (-32768,32767,-32768,32767,-32768,-32768,32767,-32768,32767,32767),
    (32767,-32768,32767,-32768,32767,32767,-1,32767,1,-32768))


@dataclass(frozen=True)
class Case:
    time:int=0
    parameters:tuple=PRESETS[0]
    layout:int=0
    seed:int=0


def owner_address(c,phase=0):
    return(EFFECT,EFFECT+2,STACK+phase-0x50,STACK+phase-0x38)[c.layout]


def half(memory,address):
    return(read(memory,address,2)^0x8000)-0x8000


def fixture(c,phase=0):
    owner=owner_address(c,phase)
    memory={STACK+phase+i:(i*17+0xA5)&255 for i in range(-256,512)}
    memory.update({owner+i:(i*13+c.seed+0x5A)&255 for i in range(-16,0xC0)})
    put(memory,owner+0x38,c.time,2)
    for i,value in enumerate(c.parameters):put(memory,owner+0x50+i*2,value,2)
    return memory


def reference(initial,owner):
    memory=dict(initial);time=half(memory,owner+0x38)
    parameter=lambda index:half(memory,owner+0x50+index*2)
    if parameter(2)<time:
        value=(parameter(1)-time)*parameter(0);put(memory,owner+0x3F,value,1)
    if parameter(5)<time:
        value=(parameter(4)-time)*parameter(3)
        put(memory,owner+0x36,value,2);put(memory,owner+0x34,value,2)
    if time<parameter(6):put(memory,owner+0x3F,time*parameter(7),1)
    if time<parameter(8):
        value=time*parameter(9)
        put(memory,owner+0x36,value,2);put(memory,owner+0x34,value,2)
    return memory


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __init__(self,code,model,end):
        super().__init__(code,model);self.end=end
    def __getitem__(self,pc):
        if pc==self.end:raise WindowBoundary
        return super().__getitem__(pc)


class EnvelopeOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,targets=(),observed=0x38):
        owner=owner_address(c,phase)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(owner,),connected=connected)
        self.owner,self.targets,self.observed=owner,set(targets),observed
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        assert target==source.ENTRY or target in self.targets,hex(target)
        args=self.arguments(1)
        assert args==(self.owner,),args
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in self.targets and target!=source.ENTRY
        put(self.memory,self.owner+self.observed,0x1357,2)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.hi,self.lo=0x87654321,0x12345678


def corpus():
    for time,parameters,layout,phase in itertools.product(TIMES,PRESETS,range(4),(0,8)):
        yield Case(time,parameters,layout,(time+layout)&255),phase
    for time,mask,coefficients,layout,phase in itertools.product((-32767,-1,0,1,32766),range(16),(1,-32768),range(4),(0,8)):
        parameters=(coefficients,123,time-1 if mask&1 else time,
            -coefficients if coefficients==1 else 32767,-456,time-1 if mask&2 else time,
            time+1 if mask&4 else time,coefficients,time+1 if mask&8 else time,32767)
        yield Case(time,parameters,layout,mask),phase
    for time,parameters in itertools.product(range(-128,128),PRESETS):yield Case(time,parameters),0


def controls():
    body=source.SELECTED
    return dict(first_inclusive=body.replace('parameters[2] < time','parameters[2] <= time'),
        second_inclusive=body.replace('parameters[5] < time','parameters[5] <= time'),
        third_inclusive=body.replace('time < parameters[6]','time <= parameters[6]'),
        fourth_inclusive=body.replace('time < parameters[8]','time <= parameters[8]'),
        first_scale=body.replace('parameters[0] *','parameters[3] *'),
        pair_scale=body.replace('parameters[3] *','parameters[0] *'),
        missing_byte=body.replace('effect[0x3F] = parameters[0] * (parameters[1] - time);',''),
        missing_pair=body.replace('*(s16 *)(effect + 0x34) = ',''),
        first_wins=body.replace('if (time < parameters[6])','else if (time < parameters[6])').replace('if (time < parameters[8])','else if (time < parameters[8])'),
        unsigned_threshold=body.replace('parameters[2] < time','(u16)parameters[2] < time'),
        wrong_timer=body.replace('effect + 0x38','effect + 0x98'),
        wrong_remaining=body.replace('parameters[1] - time','time - parameters[1]'))


def native_harness(table):
    text=source.HEADERS+'''
typedef void(*Handler)(u8*);
typedef char ABI[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4)?1:-1];
static u8 *arena,*expected,*active;
static u32 calls,error,observed;
static Handler handlers[22];
static void provider(u8*p){if(p!=active)error=1;calls++;*(s16*)(void*)(p+observed)=0x1357;}
'''
    for label,body in dict(selected=source.SELECTED,**controls()).items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective envelope control: '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    text+='static const s16 presets[8][10]='+repr(PRESETS).replace('(','{').replace(')','}')+';\n'
    text+='static const u8 present[22]={'+','.join('1'if value else'0'for value in table)+'};\n'
    text+='''
static void expected_update(u8*p){
 s32 time=*(s16*)(void*)(p+0x38),value;u32 stage;s16*q=(s16*)(void*)(p+0x50);
 for(stage=0;stage<4;stage++){
  if(stage<2){if(q[stage*3+2]>=time)continue;value=(q[stage*3+1]-time)*q[stage*3];}
  else{if(time>=q[stage==2?6:8])continue;value=time*q[stage==2?7:9];}
  if((stage&1)==0)p[0x3F]=(u8)value;
  else{*(s16*)(void*)(p+0x36)=(s16)value;*(s16*)(void*)(p+0x34)=(s16)value;}
 }
}
static int one(Handler fn,u32 bits,u32 preset,u32 alignment,u32 window,s32 index){
 u32 i;u8*p=arena+alignment,*q=expected+alignment;s32 selector;
 for(i=0;i<0x100;i++)arena[i]=(u8)(i*13+preset*7+0x5A);
 *(s16*)(void*)(p+0x38)=(s16)bits;
 for(i=0;i<10;i++)((s16*)(void*)(p+0x50))[i]=presets[preset][i];
 if(window)p[window==1?0x2F:0xB2]=(u8)index;
 for(i=0;i<0x100;i++)expected[i]=arena[i];
 active=p;calls=error=0;observed=window==1?0x38:0x98;
 if(!window){expected_update(q);fn(p);}
 else{
  selector=(s8)p[window==1?0x2F:0xB2];
  if(selector!=-1&&present[selector]){
   if(selector==17)expected_update(q);else *(s16*)(void*)(q+observed)=0x1357;
  }
  for(i=0;i<22;i++)handlers[i]=!present[i]?0:i==17?fn:provider;
  if(selector!=-1&&handlers[selector])handlers[selector](p);
  if(calls!=(u32)(selector!=-1&&present[selector]&&selector!=17))return 23;
  if(*(s16*)(void*)(p+observed)!=*(s16*)(void*)(q+observed))return 23;
 }
 if(error)return 23;
 for(i=0;i<0x100;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){
 u32 t,p,a;static const s16 short_times[]={-32768,-32767,-1,0,1,127,256,32767};
 for(t=0;t<(full?65536u:8u);t++)for(p=0;p<8;p++)for(a=0;a<2;a++)
  if(one(fn,full?t:(u16)short_times[t],p,a*2,0,0))return 23;
 return 0;
}
static void*allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 t,p,a,w;s32 index;arena=allocate(0x200);if(!arena)return 97;expected=arena+0x100;
'''
    for i,label in enumerate(dict(selected=source.SELECTED,**controls())):
        text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected'else 23,i+1)
    text+='''
 for(t=0;t<8;t++)for(p=0;p<8;p++)for(a=0;a<2;a++)for(w=1;w<3;w++)for(index=-1;index<22;index++)
  if(one(selected,(u16)((s16[]){-32768,-32767,-1,0,1,127,256,32767})[t],p,a*2,w,index))return 80;
 return 0;}
'''
    return text+START


class EnvelopeGatesTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>45I',cls.rom,source.ROM))
        cls.table=struct.unpack_from('>22I',cls.rom,source.TABLE_ROM)
        cls.raw=list(struct.unpack('>45I',source.payload(cls.out/'after-owner.o',source.FUNCTION)[0]))
        data,functions=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>45I',data,functions[source.FUNCTION]['value']))
    def compare(self,c=Case(),phase=0,images=None,entry=source.ENTRY):
        initial=fixture(c,phase);expected=reference(initial,owner_address(c,phase));models=[]
        for words in images or(self.truth,self.words,self.raw):
            model=EnvelopeOracle(words,initial,c,phase,entry).run()
            self.assertEqual(model.memory,expected,c);self.assertEqual(model.calls,[]);models.append(model)
        for model in models[1:]:self.assertEqual(complete(models[0]),complete(model))
        return models[0]
    def test_01_literal_owner_Make_registry_and_parent_ABI(self):
        self.assertEqual(self.words,self.truth)
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['body_words'],q['alignment_words'],q['frame'],q['bindings'],q['new_guards']),(45,0,0,0,2))
        self.assertEqual(mk['commands'],5);self.assertTrue(mk['complete_padded_object_equal'])
        self.assertEqual(q['preserved_global_asm'],6);self.assertTrue(mk['global_asm_pre_post_processing'])
        self.assertEqual(self.table[17],source.ENTRY)
        self.assertEqual([i for i,value in enumerate(self.table)if not value],[3,4,8])
        old=self.values['conker/build/conker.us.elf']
        self.assertEqual(struct.unpack_from('>22I',old,source.elf_slot_offset(old,source.TABLE,88)),self.table)
        pointers=[];calls=[];jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        for i in range(0,len(self.rom)-3,4):
            value=struct.unpack_from('>I',self.rom,i)[0]
            if value==source.ENTRY:pointers.append(i)
            if value==jal:calls.append(i)
        self.assertEqual((pointers,calls),([0x2314CC],[]))
        for row,parent in((5,0x15167E0C),(14,0x15168870),(59,0x15167E0C),(66,0x15167E0C)):
            self.assertEqual(struct.unpack_from('>I',self.rom,0x22FF68+row*52)[0],parent)
        caller=self.values['conker/src/game_1944C0.c'].decode()
        for parent in('func_15167E0C','func_15168870'):
            lo,hi=source.function_span(caller,parent);self.assertIn('return 0;',caller[lo:hi])
        self.receipt['owner']=dict(body_words=45,frame=0,bindings=0,guards=2,neighbors=q['preserved_neighbors'],
            Make_commands=5,preserved_global_asm=6,registry_index=17,registry_entries=22,literal_sites=pointers,direct_sites=calls,
            canonical_target_ABI='void(u8*)',original_parent_class_rows=[5,14,59,66],parent_C_stubs_uncredited=True)
    def test_02_signed_boundaries_priority_and_literal_private_state(self):
        count=0;visits=set()
        for c,phase in corpus():
            model=self.compare(c,phase);visits.update(model.visits);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+180,4)))
        self.receipt['guest']=dict(cases=count,reachable_words=45,layouts=4,phases=2,
            signed_halfword_boundaries=True,all_feasible_gate_masks=True,raw_and_fitted_full_private_state_equal=True)
    def run_window(self,which,c,index=17,phase=0,dead=0,words=None,child=None,initial=None):
        entry,end,rom,selector,observed,frame=source.WINDOWS[which]
        memory=fixture(c,phase)if initial is None else dict(initial);owner=owner_address(c,phase)
        memory[owner+selector]=index&255
        for i,value in enumerate(self.table):put(memory,source.TABLE+i*4,value)
        original=list(struct.unpack_from('>%dI'%((end-entry)//4),self.rom,rom))
        connected={source.ENTRY+i*4:word for i,word in enumerate(self.truth if child is None else child)}
        model=EnvelopeOracle(original if words is None else words,memory,c,phase,entry,connected,self.table,observed)
        model.r[29]=STACK+phase-frame;model.r[7]=dead
        model.code=WindowCode(model.code,model,end)
        with self.assertRaises(WindowBoundary):model.run()
        return model,memory
    def test_03_both_original_signed_selector_windows(self):
        count=0;visits=[set(),set()]
        for which,index,time,layout,phase,dead in itertools.product(range(2),range(-1,22),(-1,0,127),range(4),(0,8),(0,1)):
            # The unrelated provider contract must not overwrite its own saved owner.
            if which==0 and layout==3 and index not in(-1,3,4,8,17):continue
            c=Case(time,PRESETS[(time+index)%8],layout,index&255);owner=owner_address(c,phase)
            pair=[]
            for child in(self.truth,self.words):
                model,initial=self.run_window(which,c,index,phase,dead,child=child)
                expected=dict(initial);value=self.table[index]if index!=-1 else 0
                if value:
                    put(expected,STACK+phase,owner)
                    if which==0:put(expected,STACK+phase-5,dead,1)
                    if index==17:expected=reference(expected,owner)
                    else:put(expected,owner+source.WINDOWS[which][4],0x1357,2)
                self.assertEqual(model.memory,expected,(which,c,index))
                self.assertEqual(model.calls,[(value,(owner,))]if value else[])
                observed=half(expected,owner+source.WINDOWS[which][4])&0xFFFFFFFF
                self.assertEqual(model.r[10 if which==0 else 24],observed)
                self.assertEqual(model.r[4],owner)
                if which==0:self.assertEqual(model.r[7],dead)
                visits[which].update(model.visits);pair.append(model)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for which,(entry,end,*_)in enumerate(source.WINDOWS):self.assertTrue(set(range(entry,end,4))<=visits[which])
        self.receipt['callers']=dict(cases=count,original_window_words=[17,13],all_22_slots_and_minus_one=True,
            saved_owner_homes=True,late_observed_reloads=True,stack_home_input_aliases=True,whole_parent_C_or_gameplay_claimed=False)
    def test_04_native32_all_timer_bits_and_effective_controls(self):
        text=native_harness(self.table)
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native-'+opt[1:]+'.c');path.write_text(text);binary=path.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],target_cases_per_profile=65536*8*2,
            dispatcher_cases_per_profile=8*8*2*2*23,effective_controls=len(controls()),trap_UBSan=True,
            all_timer_bit_patterns=True,heap_backed_typeless_storage=True,canonical_function_pointer_interface=True)
    def test_05_fault_prefixes_and_inactive_parameter_negative(self):
        count=0
        for time,parameters,layout in itertools.product((-32768,-1,0,1,32767),(PRESETS[1],PRESETS[3],PRESETS[6]),(0,2)):
            c=Case(time,parameters,layout);initial=fixture(c);model=self.compare(c)
            for cut in range(model.root_accesses):
                pair=[]
                for words in(self.truth,self.words,self.raw):
                    x=EnvelopeOracle(words,initial,c);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                for x in pair[1:]:self.assertEqual((complete(pair[0]),pair[0].current_pc,pair[0].delay_of),
                    (complete(x),x.current_pc,x.delay_of))
                count+=1
        c=Case();initial=fixture(c)
        for offset in(0x34,0x36,0x3F,0x50,0x52,0x56,0x58,0x5E,0x62):
            for byte in range(1 if offset==0x3F else 2):initial.pop(EFFECT+offset+byte,None)
        for words in(self.truth,self.words,self.raw):EnvelopeOracle(words,initial,c).run()
        bad=source.SELECTED.replace('    s32 time = *(s16 *)(effect + 0x38);',
            '    s32 time = *(s16 *)(effect + 0x38);\n    (void)*(volatile s16 *)parameters;')
        obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+bad,'negative-early-parameter');self.assertFalse(diag)
        raw,bindings=source.payload(obj,source.FUNCTION);self.assertFalse(bindings)
        with self.assertRaisesRegex(AssertionError,'unmapped read'):EnvelopeOracle(list(struct.unpack('>%dI'%(len(raw)//4),raw)),initial,c).run()
        self.receipt['faults']=dict(prefix_pairs=count,inactive_coefficients_and_outputs_unmapped=True,
            actual_compiled_MIPS_early_read_negative_effective=True,emitted_guest_access_order_only=True)
    def test_06_checked_guards_real_padder_and_independent_links(self):
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for i in range(45):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        for bad in({0:[('R_MIPS_26','unexpected')]},):
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        with self.assertRaises(ValueError):source.normalized(raw[:-4],{})
        old=self.values['conker/retail_word_patches.us.csv']
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n',raw,{})
        guard=(self.out/'qualified-guards.csv').read_bytes();self.assertTrue(guard.startswith(old))
        self.assertEqual(guard[len(old):].count(b'\n'),2)
        path=self.out/'negative-real-padder.csv';path.write_bytes(guard[:len(old)]+guard[len(old):].replace(b'0x03030019',b'0x03030018',1))
        with self.assertRaises((ValueError,RuntimeError)):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        fitted,bindings=source.normalized(raw,{})
        asm,missing=emit_function(fitted,dict(value=0,size=180),bindings,source.FUNCTION,{})
        self.assertFalse(missing);path=self.out/'independent-fitted.s';path.write_text(asm);obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(path)],capture_output=True,check=True)
        links=0
        for i,entry in enumerate((source.ENTRY,source.ENTRY+0x200000,source.ENTRY+0x500000)):
            images=[]
            for j,object_ in enumerate((source.original(ROOT,self.out),obj)):
                script=self.out/('rebase-%d-%d.ld'%(i,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>45I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(),Case(-1,PRESETS[1]),Case(127,PRESETS[6])):self.compare(c,images=images,entry=entry)
        self.receipt['guards_links']=dict(raw_word_controls=45,unexpected_binding_controls=1,extent_controls=1,history_controls=1,
            real_padder_controls=1,independent_GNU_links=links,layouts=3,bindings=0,position_independent_body=True)
    def test_07_strict_full_image_and_frozen_inputs(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+180]
        predicted=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        report=json.loads((self.out/'first-link.json').read_text())
        self.assertEqual((report['metadata_bytes'],report['exclusions']),(1,0));self.assertGreater(report['code_bytes'],0)
        symbol=next(at for at,name,_,_ in source.symbol_rows(before)if name==source.FUNCTION)
        positions=(0,len(predicted)-1,source.elf_slot_offset(predicted,source.ENTRY,180),
            source.elf_slot_offset(predicted,source.ENTRY+176,4),symbol+8,
            source.elf_slot_offset(predicted,source.WINDOWS[0][0],68),source.elf_slot_offset(predicted,source.TABLE,88))
        for at in positions:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['strict']=dict(changed_bytes=report['changed_bytes'],code_bytes=report['code_bytes'],metadata_bytes=1,
            exclusions=0,corruptions=len(positions),focused_inputs=len(self.values))
    def test_08_caller_sentinel_and_late_reload_controls(self):
        fired=0
        for which,(entry,end,rom,selector,observed,frame)in enumerate(source.WINDOWS):
            c=Case(127,PRESETS[1]);owner=owner_address(c)
            original=list(struct.unpack_from('>%dI'%((end-entry)//4),self.rom,rom))
            initial=fixture(c);initial[owner+selector]=255
            # No table mapping is necessary for the signed -1 sentinel.
            model=EnvelopeOracle(original,initial,c,entry=entry,targets=self.table,observed=observed)
            model.r[29]=STACK-frame;model.code=WindowCode(model.code,model,end)
            with self.assertRaises(WindowBoundary):model.run()
            self.assertEqual(model.calls,[])
            bad=list(original);bad[0]^=4<<26
            model=EnvelopeOracle(bad,initial,c,entry=entry,targets=self.table,observed=observed)
            model.r[29]=STACK-frame;model.code=WindowCode(model.code,model,end)
            with self.assertRaisesRegex(AssertionError,'unmapped read'):model.run()
            fired+=1
            baseline,_=self.run_window(which,c,index=0)
            bad=list(original);bad[-1]=0
            broken,_=self.run_window(which,c,index=0,words=bad)
            self.assertNotEqual(baseline.r[10 if which==0 else 24],broken.r[10 if which==0 else 24]);fired+=1
        self.receipt['caller_controls']=dict(effective_unsigned_selector_and_missing_reload_controls=fired,
            sentinel_needs_no_table_mapping=True,bounded_original_windows_only=True)


if __name__=='__main__':unittest.main()
