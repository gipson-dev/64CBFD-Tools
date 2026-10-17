"""Observe actual gate-value register reuse; reject a reload-only shape control."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_record_gate_expression_image as image
from tools.experiments import game_actor_record_gate_compiler_trace as target
from tools.experiments import game_text_measurer_frontend_trace as frontend
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-actor-record-gate-expression-reuse'
PREFIX='GATE_REUSE '
CONTROL_SHA='714d6725c2f8ba805cf3d1921e8f888ed21affa7b8864a78e6598aa10a14cd99'


def debugger_script(root,work):
    script=image.debugger_script(root,work)
    classes='''
reuse_probes=[]
reuse_active=[]
reuse_pending=0
def reuse_event(kind,**data):gdb.write('GATE_REUSE '+json.dumps(dict(kind=kind,**data))+'\\n')
def reuse_exit(event):
    if event.inferior.progspace.filename==uopt_program:
        for bp in reuse_probes:bp.delete()
        reuse_event('removed',active=reuse_active,pending=reuse_pending,probes=len(reuse_probes),
                    exit_code=getattr(event,'exit_code','unknown'))
gdb.events.exited.connect(reuse_exit)
class ReuseFinish(gdb.FinishBreakpoint):
    def __init__(self,base,event,address=0):
        global reuse_pending
        self.base,self.event,self.address=base,event,address
        reuse_pending+=1
        super().__init__(internal=True)
    def stop(self):
        global reuse_pending
        self.event['result']=int(gdb.parse_and_eval('$eax'))
        if self.address:self.event['color']=image_word(self.base,self.address)
        reuse_event('finish',**self.event)
        reuse_pending-=1
        return False
class ReuseProbe(gdb.Breakpoint):
    def __init__(self,address,kind):
        self.kind=kind
        super().__init__(address,internal=True)
    def stop(self):
        base=int(gdb.parse_and_eval('$rdi'))
        if not image_scope(base):return False
        args={r:int(gdb.parse_and_eval('$'+r)) for r in ('edx','ecx','r8d','r9d')}
        if self.kind=='search' and args['ecx'] in image_nodes:
            ReuseFinish(base,dict(call=self.kind,procedure=760,args=args,node=args['ecx'],caller=int(gdb.newest_frame().older().pc())))
        if self.kind=='inreg' and image_nodes and args['edx']==image_word(base,image_nodes[0]+20):
            ReuseFinish(base,dict(call=self.kind,procedure=760,args=args,caller=int(gdb.newest_frame().older().pc())),args['r8d'])
        return False
class ReuseEmitFinish(gdb.FinishBreakpoint):
    def __init__(self,node):
        global reuse_pending
        self.node=node
        reuse_pending+=1
        super().__init__(internal=True)
    def stop(self):
        global reuse_pending
        reuse_event('emit-end',procedure=760,node=self.node)
        if reuse_active.pop()!=self.node:raise gdb.GdbError('Mismatched emit nesting')
        reuse_pending-=1
        return False
class ReuseEmit(gdb.Breakpoint):
    def stop(self):
        base,node=int(gdb.parse_and_eval('$rdi')),int(gdb.parse_and_eval('$ecx'))
        if image_scope(base) and node in image_nodes:
            reuse_active.append(node)
            reuse_event('emit-start',procedure=760,node=node,words=image_words(base,node))
            ReuseEmitFinish(node)
        return False
class ReuseWrite(gdb.Breakpoint):
    def stop(self):
        if reuse_active:
            base,record=int(gdb.parse_and_eval('$rdi')),int(gdb.parse_and_eval('$edx'))
            if not image_scope(base):raise gdb.GdbError('Wrong gate emission procedure')
            reuse_event('write',procedure=760,node=reuse_active[-1],record=[image_word(base,record+i) for i in range(0,16,4)])
        return False
'''
    anchor='class LoadNode(gdb.Breakpoint):'
    if script.count(anchor)!=1:raise ValueError('Changed image debugger class anchor')
    script=script.replace(anchor,classes+'\n'+anchor,1)
    install='''if gdb.current_progspace().filename == uopt_program:
    reuse_probes.extend((ReuseProbe('*0x455fa0','search'),ReuseProbe('*0x41f0d0','inreg'),
        ReuseEmit('*0x438260',internal=True),ReuseWrite('*0x42bc00',internal=True)))
    reuse_event('installed',program=uopt_program,probes=len(reuse_probes))
'''
    anchor='if gdb.current_progspace().filename == program:\n'
    if script.count(anchor)!=2:raise ValueError('Changed image debugger exec anchors')
    return script.replace(anchor,install+anchor,1)


def facts(root,log,wire):
    before=image.facts(root,log,wire)
    rows=[];lines=log.splitlines()
    for line in lines:
        if line.startswith(PREFIX):
            try:row=json.loads(line[len(PREFIX):])
            except json.JSONDecodeError as error:raise ValueError('Malformed gate-reuse event') from error
            if not isinstance(row,dict):raise ValueError('Malformed gate-reuse event')
            rows.append(row)
    expected=('installed','finish','finish','emit-start','write','finish','write','emit-end',
        'emit-start','finish','write','emit-end','emit-start','finish','write','emit-end','removed')
    if tuple(r.get('kind') for r in rows)!=expected:raise ValueError('Missing/misordered gate-reuse probes')
    if rows[0]!=dict(kind='installed',program=str(root/'ido/ido5.3_recomp/uopt'),probes=4):
        raise ValueError('Wrong gate-reuse compiler binding')
    if rows[-1]!=dict(kind='removed',active=[],pending=0,probes=4,exit_code=0):
        raise ValueError('Incomplete gate-reuse cleanup')
    positions=[i for i,line in enumerate(lines) if line.startswith(PREFIX)]
    start=next(i for i,line in enumerate(lines) if line.startswith(frontend.PREFIX))
    end=lines.index('TRACE_EXIT inferior=3 code=0')
    output=next(i for i,line in enumerate(lines) if line.startswith(frontend.OPTIMIZER_PREFIX))
    if not start<positions[0]<positions[-2]<end<positions[-1]<output:
        raise ValueError('Gate-reuse probes outside owned UOPT lifetime')
    if any(r.get('procedure')!=760 for r in rows[1:-1]):raise ValueError('Wrong gate-reuse procedure')
    previous=image.events(log);reads=[previous[i] for i in (1,3)];nodes=[r['node'] for r in reads]
    common=before['common_image'];address_image=previous[2]['image_words'][5]
    for row,node in zip(rows[1:3],nodes):
        if row!=dict(kind='finish',call='search',procedure=760,args=dict(edx=148,ecx=node,r8d=address_image,r9d=0),
                node=node,caller=0x458a05,result=common):
            raise ValueError('Changed common-image lookup operands/result')
    for at,node in zip((3,8,12),(nodes[0],nodes[0],nodes[1])):
        row=rows[at]
        if set(row)!=set(('kind','procedure','node','words')) or row['node']!=node or image.words(row['words'],16)[5]!=common:
            raise ValueError('Changed expression emission identity')
        end_at=7 if at==3 else at+3
        if rows[end_at]!=dict(kind='emit-end',procedure=760,node=node):raise ValueError('Unbalanced expression emission')
    for at,node,record in ((4,nodes[0],[0x52800000,747,4,0]),(6,nodes[0],[0x7b600000,0,4,2]),
            (10,nodes[0],[0x52600000,0,4,2]),(14,nodes[1],[0x52600000,0,4,2])):
        if rows[at]!=dict(kind='write',procedure=760,node=node,record=record):
            raise ValueError('Changed memory load/register store/register reuse emission')
    for at,node,read,mode,caller in ((5,nodes[0],reads[0],0,0x438f4c),
            (9,nodes[0],reads[0],1,0x439289),(13,nodes[1],reads[1],1,0x439289)):
        row=rows[at]
        if set(row)!=set(('kind','call','procedure','args','caller','result','color')):
            raise ValueError('Malformed gate register-availability result')
        args=row['args']
        if (not isinstance(args,dict) or set(args)!=set(('edx','ecx','r8d','r9d')) or
                (args['edx'],args['ecx'],args['r9d'])!=(common,read['words'][4],mode) or
                row['call']!='inreg' or row['caller']!=caller or row['result']!=1 or row['color']!=1):
            raise ValueError('Changed gate register-availability lookup')
        image.pointer(args['r8d'])
    return dict(distinct_nodes=2,lookup_hash=148,same_address_operand_image=address_image,
        shared_image=common,observed_memory_loads=1,observed_register_stores=1,
        observed_register_reads=2,availability_color=1,emitted_hardware_GPR=2,
        both_predicates_reuse_the_materialized_value=True,original_retail_source_not_recovered=True)


def capture(root):
    root=Path(root).resolve();content=target.owner(root,'normal');out=root/BUILD;name='normal'
    with patch.object(frontend,'debugger_script',debugger_script),patch.object(frontend.trace,'screen',target.adapter(content,'normal')):
        wire=frontend.capture_frontend(root,out,name,content)
    work=out/name;log=(work/'debugger.txt').read_text()
    result=dict(facts=facts(root,log,wire),lifecycle=target.lifecycle(root,log),
        full_normal_object_unchanged=wire['code_unchanged'],installable=False,no_matching_credit=True)
    target.source.freeze(root,root/target.source.BUILD)
    (work/'reuse.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def reload_control(root):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    target.source.freeze(root,root/target.source.BUILD)
    before=(root/target.source.BUILD/'before-record_gate_owner').read_text()
    normal=target.source.recovered_owner(before)
    declaration='extern u8 *D_800CC5EC;'
    if normal.count(declaration)!=1:raise ValueError('Changed gate reload-control declaration')
    # A diagnostic-only forced reload, never a recovered historical qualifier.
    content=normal.replace(declaration,'extern u8 *volatile D_800CC5EC;',1)
    obj,diag=target.source.compile_owner(root,out,content,'reload-control')
    if diag:raise ValueError(diag)
    raw,_=target.source.parts(obj)
    if hashlib.sha256(raw).hexdigest()!=CONTROL_SHA:raise ValueError('Changed rejected reload control')
    baseline,diag=target.source.compile_owner(root,out,normal,'baseline')
    if diag:raise ValueError(diag)
    if same_functions(baseline,obj,(target.source.FUNCTION,))!=11 or normalized_pools(baseline)!=normalized_pools(obj):
        raise ValueError('Reload control changed copied neighbors/pools')
    words=target.source.linked(root,out,obj,'reload-control-linked')
    target.source.freeze(root,root/target.source.BUILD)
    return obj,words


if __name__=='__main__':print(json.dumps(capture(Path(__file__).resolve().parents[2]),indent=2),flush=True)
