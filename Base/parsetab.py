
# parsetab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'COLON COMMA FALSE FLOAT INTEGER LIST_BEGIN LIST_END NULL OBJECT_BEGIN OBJECT_END STRING TRUE\n        object : OBJECT_BEGIN OBJECT_END\n        \n        object : OBJECT_BEGIN tuples OBJECT_END\n        \n        tuples : tuple COMMA tuples\n        \n        tuples : tuple COMMA\n               | tuple\n        \n        tuple : STRING COLON element\n        \n        list : LIST_BEGIN commalist LIST_END\n        \n        commalist : element COMMA commalist\n        \n        commalist : element COMMA\n                  | element\n        \n        element : object\n                | list\n        \n        element : NULL\n        \n        element : TRUE\n        \n        element : FALSE\n        \n        element : FLOAT\n        \n        element : INTEGER\n        \n        element : STRING\n        '

_lr_action_items = {'OBJECT_BEGIN':([0,9,20,24,],[2,2,2,2,]),'$end':([1,3,7,],[0,-1,-2,]),'OBJECT_END':([2,3,4,5,7,8,10,11,12,13,14,15,16,17,18,19,23,],[3,-1,7,-5,-2,-4,-3,-18,-6,-11,-12,-13,-14,-15,-16,-17,-7,]),'STRING':([2,8,9,20,24,],[6,6,11,11,11,]),'COMMA':([3,5,7,11,12,13,14,15,16,17,18,19,22,23,],[-1,8,-2,-18,-6,-11,-12,-13,-14,-15,-16,-17,24,-7,]),'LIST_END':([3,7,11,13,14,15,16,17,18,19,21,22,23,24,25,],[-1,-2,-18,-11,-12,-13,-14,-15,-16,-17,23,-10,-7,-9,-8,]),'COLON':([6,],[9,]),'NULL':([9,20,24,],[15,15,15,]),'TRUE':([9,20,24,],[16,16,16,]),'FALSE':([9,20,24,],[17,17,17,]),'FLOAT':([9,20,24,],[18,18,18,]),'INTEGER':([9,20,24,],[19,19,19,]),'LIST_BEGIN':([9,20,24,],[20,20,20,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'object':([0,9,20,24,],[1,13,13,13,]),'tuples':([2,8,],[4,10,]),'tuple':([2,8,],[5,5,]),'element':([9,20,24,],[12,22,22,]),'list':([9,20,24,],[14,14,14,]),'commalist':([20,24,],[21,25,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> object","S'",1,None,None,None),
  ('object -> OBJECT_BEGIN OBJECT_END','object',2,'p_object_empty','ExtendedJsonParser.py',126),
  ('object -> OBJECT_BEGIN tuples OBJECT_END','object',3,'p_object','ExtendedJsonParser.py',132),
  ('tuples -> tuple COMMA tuples','tuples',3,'p_tuples_tuple_comma_tuples','ExtendedJsonParser.py',142),
  ('tuples -> tuple COMMA','tuples',2,'p_tuples_tuple_comma_or_tuple','ExtendedJsonParser.py',149),
  ('tuples -> tuple','tuples',1,'p_tuples_tuple_comma_or_tuple','ExtendedJsonParser.py',150),
  ('tuple -> STRING COLON element','tuple',3,'p_tuple','ExtendedJsonParser.py',156),
  ('list -> LIST_BEGIN commalist LIST_END','list',3,'p_list','ExtendedJsonParser.py',162),
  ('commalist -> element COMMA commalist','commalist',3,'p_commalist_element_comma_commalist','ExtendedJsonParser.py',172),
  ('commalist -> element COMMA','commalist',2,'p_commalist_element_comma_or_element','ExtendedJsonParser.py',179),
  ('commalist -> element','commalist',1,'p_commalist_element_comma_or_element','ExtendedJsonParser.py',180),
  ('element -> object','element',1,'p_element_object_or_list','ExtendedJsonParser.py',196),
  ('element -> list','element',1,'p_element_object_or_list','ExtendedJsonParser.py',197),
  ('element -> NULL','element',1,'p_element_NULL','ExtendedJsonParser.py',203),
  ('element -> TRUE','element',1,'p_element_TRUE','ExtendedJsonParser.py',209),
  ('element -> FALSE','element',1,'p_element_FALSE','ExtendedJsonParser.py',215),
  ('element -> FLOAT','element',1,'p_element_FLOAT','ExtendedJsonParser.py',221),
  ('element -> INTEGER','element',1,'p_element_INTEGER','ExtendedJsonParser.py',227),
  ('element -> STRING','element',1,'p_element_STRING','ExtendedJsonParser.py',233),
]
