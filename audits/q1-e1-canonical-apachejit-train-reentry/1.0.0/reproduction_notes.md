# Reproduction scope

The script consumes the frozen preflight and canonical_inventory_input.json captured during the single authorized inventory. It refuses to overwrite an existing output package. Source snapshots can be verified in place with verify_snapshot; the finite inventory must not be repeated as another recovery sprint. Reproduction in an isolated checkout requires the same pinned parent packages and canonical TRAIN prefix. The full archive was not freshly hashed; its digest is inherited from frozen lineage. Validation logs and the safe regression selector/node list are included.
