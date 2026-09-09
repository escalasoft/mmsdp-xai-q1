import ast,json
from pathlib import Path
names=['canonical_identity_representation_linkage','population_representation_provenance_resolution','input_provenance_eligibility']
nodes=[]
for name in names:
 p=Path('tests/evaluation/test_q1_e1_'+name+'.py')
 for node in ast.parse(p.read_text()).body:
  if isinstance(node,ast.FunctionDef) and node.name.startswith('test_') and not ({a.arg for a in node.args.args}&{'evidence','result'}):
   nodes.append(str(p)+'::'+node.name)
nodes += ['tests/evaluation/test_q1_xai_reconstruction_equivalence_protocol.py::'+n.name for n in ast.parse(Path('tests/evaluation/test_q1_xai_reconstruction_equivalence_protocol.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_') and n.name != 'test_package_manifest_and_sealed_sprint54_references_verify']
Path('/tmp/s56br3-safe-nodes.json').write_text(json.dumps(nodes,indent=2)+'\n')
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider']+nodes))
