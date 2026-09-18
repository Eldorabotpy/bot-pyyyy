import ast,copy,types,unittest
from pathlib import Path
class ProgressTests(unittest.TestCase):
 def run_progress(self,concurrent=False,progress=0,total=10):
  state={'guild_missions':{'ativas':{'m':{'status':'ativa','progresso':progress}}}}
  class Collection:
   def __init__(self):self.reads=0
   def find_one(self,*args):
    self.reads+=1; snapshot=copy.deepcopy(state)
    if concurrent and self.reads==2:state['guild_missions']['ativas']['m']['progresso']+=1
    return snapshot
   def update_one(self,q,u):
    mission=state['guild_missions']['ativas']['m']
    for key,val in u.get('$inc',{}).items():mission[key.split('.')[-1]]+=val
    for key,val in u.get('$set',{}).items():mission[key.split('.')[-1]]=val
    return types.SimpleNamespace(modified_count=1)
  tree=ast.parse((Path(__file__).resolve().parents[1]/'modules/guild_missions/guild_mission_manager.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='registrar_abate')
  mission={'id':'m','nome':'Teste','escopo':'individual','tipo':'pessoal','modo':'solo','objetivo':{'tipo':'matar','regiao':'floresta','mob_ids':['slime'],'quantidade':total}}
  ns={'users_collection':Collection(),'_object_id':lambda v:v,'_obter_estado':lambda doc:doc['guild_missions'],'obter_missao':lambda _:mission,'_limpar_cache':lambda _:None,'_agora':lambda:'now','STATUS_ATIVA':'ativa','STATUS_PRONTA_ENTREGA':'pronta_entrega','ESCOPO_INDIVIDUAL':'individual','OBJETIVO_MATAR_MOB':'matar','TIPO_CLA':'cla','MODO_SOLO':'solo','MODO_GRUPO':'grupo'}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<progress>','exec'),ns)
  result=ns['registrar_abate']('hero','slime','floresta')
  return state['guild_missions']['ativas']['m'],result,ns['users_collection'].reads
 def test_concurrent_increment_is_not_overwritten(self):
  mission,_,reads=self.run_progress(concurrent=True)
  self.assertEqual(mission['progresso'],2);self.assertEqual(reads,2)
 def test_last_kill_marks_ready(self):
  mission,result,_=self.run_progress(progress=9)
  self.assertEqual(mission['status'],'pronta_entrega');self.assertEqual(mission['progresso'],10);self.assertEqual(result[0]['status'],'pronta_entrega')
if __name__=='__main__':unittest.main(verbosity=2)
