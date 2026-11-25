"""Safe outcome envelope around the unchanged C.1 decoder; stdin only."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import base64
import json
import zlib
from src.governance import e1_code_candidate as c


def main():
    sys.addaudithook(c.deny_io)
    try:
        request=sys.stdin.buffer.read(c.REQUEST_LIMIT+1)
        c.need(len(request)<=c.REQUEST_LIMIT,'IPC_REQUEST_LIMIT')
        obj=c.parse(request)
        ids=c.Identities(**{k:tuple(v) for k,v in obj['ids'].items()})
        payload=base64.b64decode(obj['payload'],validate=True)
        raw,counts=c.decode(payload,obj['expected'],ids)
        response=json.dumps({'output':base64.b64encode(raw).decode(),'output_sha256':c.sha(raw),
                             'source_sha256':c.sha(payload),'transport':counts},separators=(',',':')).encode()
        c.need(len(response)<=c.RESPONSE_LIMIT,'IPC_RESPONSE_LIMIT')
    except (KeyboardInterrupt,SystemExit,MemoryError):
        sys.stdout.write('{"status":"INCONCLUSIVE","reason":"INTERRUPTION_OR_RESOURCE"}');return 2
    except (c.Rejected,ValueError,TypeError,KeyError,zlib.error):
        sys.stdout.write('{"status":"FAIL","reason":"VALIDATION_REJECTED"}');return 2
    except BaseException:
        sys.stdout.write('{"status":"INCONCLUSIVE","reason":"UNEXPECTED_STATE"}');return 2
    sys.stdout.buffer.write(response);return 0

if __name__=='__main__':raise SystemExit(main())
