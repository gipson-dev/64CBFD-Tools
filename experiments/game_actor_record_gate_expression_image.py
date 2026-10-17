"""Observe the two opening loads' expression images in a normal owned compile."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_record_gate_compiler_trace as target
from tools.experiments import game_text_measurer_frontend_trace as frontend

FRONTEND_SCRIPT=frontend.debugger_script
BUILD='conker/build/game-actor-record-gate-expression-image'
PREFIX='GATE_IMAGE '
STAGES=('patchvectors','copypropagate','codemotion','reemit')
PROBES=(('read','0x485a60'),('image','0x458080'),
    *zip(STAGES,('0x4522a0','0x468fb0','0x47bd10','0x448a80')))


def debugger_script(root,work):
    script=FRONTEND_SCRIPT(root,work)
    classes='''
image_probes=[]
image_nodes=[]
image_pending=0
def image_event(kind,**data):
    gdb.write('GATE_IMAGE '+json.dumps(dict(kind=kind,**data))+'\\n')
def image_word(base,address):
    return int.from_bytes(gdb.selected_inferior().read_memory(base+address,4).tobytes(),'little')
def image_scope(base):
    proc=image_word(base,0x10021c74)
    return proc and image_word(base,proc)==760
def image_words(base,node):
    return [image_word(base,node+i) for i in range(0,64,4)]
def image_top(base):
    return image_word(base,image_word(base,0x1001c4a8))
def image_exit(event):
    if event.inferior.progspace.filename==uopt_program:
        for probe in image_probes:probe.delete()
        image_event('removed',pending=image_pending,probes=len(image_probes),
                    exit_code=getattr(event,'exit_code','unknown'))
gdb.events.exited.connect(image_exit)
class GateReadFinish(gdb.FinishBreakpoint):
    def __init__(self,base,inputs):
        global image_pending
        self.base,self.inputs=base,inputs
        image_pending+=1
        super().__init__(internal=True)
    def stop(self):
        global image_pending
        node=image_top(self.base)
        image_nodes.append(node)
        image_event('read',procedure=760,input=self.inputs,node=node,words=image_words(self.base,node))
        image_pending-=1
        return False
class GateRead(gdb.Breakpoint):
    def stop(self):
        base=int(gdb.parse_and_eval('$rdi'))
        if not image_scope(base):return False
        inputs=[image_word(base,0x10011ff0+i) for i in range(0,16,4)]
        if inputs[0]>>24==82 and inputs[1]==747:
            GateReadFinish(base,inputs)
        return False
class GateImageFinish(gdb.FinishBreakpoint):
    def __init__(self,base,node):
        global image_pending
        self.base,self.node=base,node
        self.before=image_words(base,node)
        image_pending+=1
        super().__init__(internal=True)
    def stop(self):
        global image_pending
        image=int(gdb.parse_and_eval('$eax'))
        image_event('image',procedure=760,node=self.node,before=self.before,image=image,
            image_words=[image_word(self.base,image+i) for i in range(0,40,4)],
            after=image_words(self.base,self.node))
        image_pending-=1
        return False
class GateImage(gdb.Breakpoint):
    def stop(self):
        base,node=int(gdb.parse_and_eval('$rdi')),int(gdb.parse_and_eval('$edx'))
        if image_scope(base) and node in image_nodes:GateImageFinish(base,node)
        return False
class GateStage(gdb.Breakpoint):
    def __init__(self,address,stage):
        self.stage=stage
        super().__init__(address,internal=True)
    def stop(self):
        base=int(gdb.parse_and_eval('$rdi'))
        if image_scope(base):
            image_event('stage',procedure=760,stage=self.stage,
                nodes=[dict(node=n,words=image_words(base,n)) for n in image_nodes])
        return False
'''
    anchor='class LoadNode(gdb.Breakpoint):'
    if script.count(anchor)!=1:raise ValueError('Changed qualified debugger class anchor')
    script=script.replace(anchor,classes+'\n'+anchor,1)
    install='''if gdb.current_progspace().filename == uopt_program:
    image_probes.extend((GateRead('*0x485a60',internal=True),GateImage('*0x458080',internal=True)))
    for stage,address in '''+repr(PROBES[2:])+''':
        image_probes.append(GateStage('*'+address,stage))
    image_event('installed',program=uopt_program,probes=len(image_probes))
'''
    anchor='if gdb.current_progspace().filename == program:\n'
    if script.count(anchor)!=2:raise ValueError('Changed qualified debugger exec anchors')
    return script.replace(anchor,install+anchor,1)


def words(value,count):
    if (not isinstance(value,list) or len(value)!=count or
            any(type(w) is not int or not 0<=w<=0xffffffff for w in value)):
        raise ValueError('Malformed expression-image raw words')
    return value


def pointer(value):
    if type(value) is not int or not 0<value<=0xffffffff or value%4:
        raise ValueError('Malformed expression-image identity')
    return value


def events(log):
    result=[]
    for line in log.splitlines():
        if line.startswith(PREFIX):
            try:row=json.loads(line.removeprefix(PREFIX))
            except json.JSONDecodeError as error:raise ValueError('Malformed expression-image event') from error
            if not isinstance(row,dict):raise ValueError('Malformed expression-image event')
            result.append(row)
    return result


def facts(root,log,wire):
    rows=events(log)
    expected=('installed','read','image','read','image',*('stage' for _ in STAGES),'removed')
    if tuple(r.get('kind') for r in rows)!=expected:raise ValueError('Missing/misordered expression-image probes')
    if rows[0]!=dict(kind='installed',program=str(root/'ido/ido5.3_recomp/uopt'),probes=6):
        raise ValueError('Changed expression-image compiler binding')
    if rows[-1]!=dict(kind='removed',pending=0,probes=6,exit_code=0):
        raise ValueError('Incomplete expression-image probe cleanup')
    lines=log.splitlines()
    positions=[i for i,line in enumerate(lines) if line.startswith(PREFIX)]
    removed=next(i for i,line in enumerate(lines) if line.startswith(PREFIX) and json.loads(line[len(PREFIX):])['kind']=='removed')
    start=next(i for i,line in enumerate(lines) if line.startswith(frontend.PREFIX))
    ended=lines.index('TRACE_EXIT inferior=3 code=0')
    if not start<positions[0]<positions[-2]<ended<removed<next(i for i,line in enumerate(lines) if line.startswith(frontend.OPTIMIZER_PREFIX)):
        raise ValueError('Expression-image probes not removed before next compiler child')
    if any(row.get('procedure')!=target.PROCEDURE for row in rows[1:-1]):
        raise ValueError('Wrong expression-image procedure')
    reads=[rows[i] for i in (1,3)];nodes=[pointer(row.get('node')) for row in reads]
    if nodes[0]==nodes[1]:raise ValueError('Opening read nodes are not distinct')
    for row in reads:
        if set(row)!=set(('kind','procedure','input','node','words')) or words(row['input'],4)!=[0x52800000,747,4,0]:
            raise ValueError('Changed opening static load identity or width')
        raw=words(row['words'],16)
        if raw[0]>>24!=4 or raw[8]>>24!=54 or raw[5]!=0:
            raise ValueError('Opening read is not an initially unimaged indirect-load node')
        pointer(raw[9])
    if reads[0]['words'][9]!=reads[1]['words'][9]:raise ValueError('Opening read address operands differ')
    images=[rows[i] for i in (2,4)]
    image=pointer(images[0].get('image'))
    for row,node,read in zip(images,nodes,reads):
        if set(row)!=set(('kind','procedure','node','before','image','image_words','after')) or row['node']!=node or pointer(row['image'])!=image:
            raise ValueError('Opening loads do not share one observed expression image')
        before,after,raw=words(row['before'],16),words(row['after'],16),words(row['image_words'],10)
        if before[5]!=0 or after[5]!=image or before[9]!=read['words'][9] or after[9]!=before[9]:
            raise ValueError('Changed image association or address operand')
        if raw[1]!=0x00940000 or raw[2]!=nodes[0]:raise ValueError('Changed common image identity/representative')
    for row,stage in zip(rows[5:-1],STAGES):
        if set(row)!=set(('kind','procedure','stage','nodes')) or row['stage']!=stage or not isinstance(row['nodes'],list) or len(row['nodes'])!=2:
            raise ValueError('Changed expression-image stage order or scope')
        for item,node in zip(row['nodes'],nodes):
            if not isinstance(item,dict) or set(item)!=set(('node','words')) or item['node']!=node or words(item['words'],16)[5]!=image:
                raise ValueError('Changed expression-image association at stage boundary')
    wire_facts=target.wire_facts(wire['records'],wire['optimizer_records'])
    return dict(procedure=target.PROCEDURE,distinct_read_nodes=2,common_image=image,
        raw_image_tag=0x00940000,shared_before=list(STAGES),
        initial_global_loads=wire_facts['initial_global_loads'],
        shared_image_exists_before_global_passes=True,
        exact_elimination_decision_and_original_source_not_observed=True,
        unknown_raw_fields_not_interpreted=True)


def capture(root):
    root=Path(root).resolve();content=target.owner(root,'normal');out=root/BUILD;name='normal'
    with patch.object(frontend,'debugger_script',debugger_script),patch.object(frontend.trace,'screen',target.adapter(content,'normal')):
        complete=frontend.capture_frontend(root,out,name,content)
    work=out/name;log=(work/'debugger.txt').read_text()
    result=dict(facts=facts(root,log,complete),lifecycle=target.lifecycle(root,log),
        full_normal_object_unchanged=complete['code_unchanged'],
        log_sha256=hashlib.sha256(log.encode()).hexdigest(),installable=False,no_matching_credit=True)
    target.source.freeze(root,root/target.source.BUILD)
    (work/'expression-image.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(capture(Path(__file__).resolve().parents[2]),indent=2),flush=True)
