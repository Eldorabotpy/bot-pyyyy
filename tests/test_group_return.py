import importlib.util,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'modules/combat/group_combat_manager.py'
spec=importlib.util.spec_from_file_location('group_test',path);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class GroupReturnTests(unittest.TestCase):
 def setUp(self):
  g.batalhas_grupo_ativas.clear()
  self.s=g.criar_cacada_grupo(equipe_herois=[{'id':'leader','current_hp':100},{'id':'member','current_hp':100}],mob_vivo={'id':'slime','hp_atual':10},regiao='forest',spawn_id='spawn',lider_id='leader')
 def test_no_return_while_fighting(self):
  for state in [g.ESTADO_AGUARDANDO,g.ESTADO_EM_ANDAMENTO]:
   self.s['estado']=state
   with self.assertRaises(ValueError):g.retornar_grupo_ao_mapa(self.s['sala_id'],'leader')
 def test_only_leader_can_return(self):
  self.s['estado']=g.ESTADO_VITORIA
  for uid in ['member','outsider',None]:
   with self.assertRaises(ValueError):g.retornar_grupo_ao_mapa(self.s['sala_id'],uid)
 def test_return_retained_for_reconnection_and_repeat(self):
  self.s['estado']=g.ESTADO_VITORIA
  for _ in range(2):
   packet=g.retornar_grupo_ao_mapa(self.s['sala_id'],'leader');self.assertTrue(packet['retorno_mapa']);self.assertEqual(packet['membros_ids'],['leader','member'])
  self.assertTrue(g.pacote_estado_sala(self.s['sala_id'])['retorno_mapa'])
 def test_broadcast_only_participants(self):
  sent=[]
  class Socket:
   def emit(self,event,payload,to):sent.append(to)
  g.emitir_para_membros(Socket(),self.s['sala_id'],'grupoRetornouMapa',{}, {'a':{'char_id':'leader'},'b':{'char_id':'member'},'c':{'char_id':'outsider'}})
  self.assertEqual(sent,['a','b'])
 def test_defeat_and_no_raid_changes(self):
  self.s['estado']=g.ESTADO_DERROTA;g.retornar_grupo_ao_mapa(self.s['sala_id'],'leader')
  self.s['tipo']=g.TIPO_RAID
  with self.assertRaises(ValueError):g.retornar_grupo_ao_mapa(self.s['sala_id'],'leader')
 def test_socket_uses_connected_identity_not_payload(self):
  import ast,types
  tree=ast.parse((path.parents[2]/'main.py').read_text(encoding='utf-8-sig'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='retornar_grupo_mapa');node.decorator_list=[]
  sent=[]
  class Socket:
   def emit(self,*a,**kw):sent.append(kw['to'])
  ns={'gcm':g,'request':types.SimpleNamespace(sid='member-session'),'jogadores_online':{'member-session':{'char_id':'member'},'leader-session':{'char_id':'leader'}},'socketio':Socket()}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<socket>','exec'),ns)
  self.s['estado']=g.ESTADO_VITORIA
  result=ns['retornar_grupo_mapa']({'sala_id':self.s['sala_id'],'user_id':'leader'})
  self.assertFalse(result['success']);self.assertEqual(sent,[])
  ns['request'].sid='leader-session'
  self.assertTrue(ns['retornar_grupo_mapa']({'sala_id':self.s['sala_id']})['success']);self.assertEqual(set(sent),{'member-session','leader-session'})
if __name__=='__main__':unittest.main(verbosity=2)
