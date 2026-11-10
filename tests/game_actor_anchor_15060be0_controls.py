"""Semantic controls need complete, valid-domain observable witnesses."""
import json
from tools.tests import game_actor_anchor_15060be0_oracle as g
from tools.experiments import game_actor_anchor_15060be0_match as p
def mutants(source):
 changes={'always-fallback':('(actor->id != 0xFF)','(0)'),'ignore-id-sentinel':('(actor->id != 0xFF)','(1)'),'ignore-disable-gate':('(D_800C3E90 == 0)','(1)'),'unsigned-model-distance':('*(s16 *)model->pad14','*(u16 *)model->pad14'),'ignore-actor-scale':('* actor->y_scale','* 1.0f'),'always-zero-displacement':('if (y != 0.0f)','if (0)'),'missing-square-root':('sqrtf(direction_x * direction_x + direction_y * direction_y + direction_z * direction_z)','(direction_x * direction_x + direction_y * direction_y + direction_z * direction_z)'),'missing-z-norm':('+ direction_z * direction_z','+ 0.0f'),'multiply-normalizer':('length = y / length;','length = y * length;'),'divide-x-component':('x = direction_x * length;','x = direction_x / length;'),'wrong-zero-value':('z = y = x = 0.0f;','z = y = x = 1.0f;'),'wrong-fallback-x':('(s16)(s32)actor->x_position','(s16)(s32)actor->z_position'),'missing-fallback':('if (updated == 0)','if (0)'),'wrong-y-output':('((s16 *)&actor->pad1BC)[1]','((s16 *)&actor->pad1BC)[0]'),'inverted-zero-norm-gate':('if (length != 0.0f)','if (length == 0.0f)')}
 result={}
 for label,(a,b)in changes.items():assert a in source;result[label]=source.replace(a,b)
 cached=source.replace('    f32 direction_z;','    f32 direction_z;\n    f32 origin_x;\n    f32 origin_y;\n    f32 origin_z;').replace('        ((s16 *)&actor->pad1BC)[0]','        origin_x = transform[12];\n        origin_y = transform[13];\n        origin_z = transform[14];\n        ((s16 *)&actor->pad1BC)[0]',1)
 for i,name in enumerate(('origin_x','origin_y','origin_z'),12):cached=cached.replace('(transform['+str(i)+'] +','('+name+' +')
 result['cached-transform-origins']=cached
 x='        ((s16 *)&actor->pad1BC)[0] = (s16)(s32)(transform[12] + x);\n';y='        ((s16 *)&actor->pad1BC)[1] = (s16)(s32)(transform[13] + y);\n';assert x+y in source;result['reversed-xy-stores']=source.replace(x+y,y+x)
 return result
def main():
 source=p.BASE;old=(p.out/'frozen'/p.SOURCE).read_text();report={};hints={'ignore-id-sentinel':g.Case(identity=255),'ignore-disable-gate':g.Case(disabled=1),'unsigned-model-distance':g.Case(distance=-1),'ignore-actor-scale':g.Case(scale=g.bits(2.)),'missing-z-norm':g.Case(direction=(g.bits(3.),g.bits(4.),g.bits(5.))),'wrong-zero-value':g.Case(distance=0),'wrong-fallback-x':g.Case(identity=255),'missing-fallback':g.Case(identity=255),'cached-transform-origins':g.Case(alias=2),'reversed-xy-stores':g.Case(alias=2)}
 for label,mutant in mutants(source).items():
  owner=p.proposal(old,mutant).replace('s32 func_15060BE0(struct127 *);','void func_15060BE0(struct127 *);');obj,_=p.compile_owner(p.root,p.out,owner,'negative-'+label);ws=g.words(obj)
  for i,c in enumerate([hints.get(label,g.Case())]+g.cases()):
   if c.sparse:continue
   expected,normal,*_=g.reference(g.fixture(c),c)
   if not normal:continue
   m=g.Oracle(ws,g.fixture(c),c,entry=g.ENTRY+0x20000);m.track_roles=False
   try:m.run()
   except g.InvalidConversionPrefix:continue
   if g.public(m.memory)!=g.public(expected):report[label]=dict(case=i,normal_completion=True,execution_errors=0);break
  assert label in report,('No valid-domain normal witness',label);print(label,json.dumps(report[label]),flush=True)
 result=dict(controls=len(report),effective_compiled_controls=report,invalid_conversion_prefixes_not_counted=True);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':main()
