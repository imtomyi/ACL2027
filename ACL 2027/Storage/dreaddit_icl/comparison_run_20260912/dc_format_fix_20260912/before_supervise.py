"""Sequential persistent local queue; no automatic configuration changes on failure."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from comparison import RUN, METHODS, atomic, table


def main():
    os.umask(0o077)
    RUN.mkdir(parents=True,exist_ok=True)
    lock=(RUN/'queue.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # If the base evaluation was launched during preparation, let it finish first.
    existing=RUN/'base.pid'
    if existing.exists():
        pid=int(existing.read_text())
        while True:
            try:
                os.kill(pid,0)
            except ProcessLookupError:
                break
            atomic(RUN/'queue.json',dict(status='running',method='base',pid=pid,supervisor_pid=os.getpid()))
            time.sleep(10)
    outcomes={}
    for method in METHODS:
        state=RUN/method/'state.json'
        if state.exists() and json.loads(state.read_text()).get('status')=='complete':
            outcomes[method]='complete'
            continue
        with (RUN/(method+'.log')).open('a') as log:
            child=subprocess.Popen([sys.executable,'-u',str(Path(__file__).with_name('comparison.py')),method],
                                   stdout=log,stderr=subprocess.STDOUT)
            atomic(RUN/'queue.json',dict(status='running',method=method,pid=child.pid,
                                         supervisor_pid=os.getpid(),outcomes=outcomes))
            code=child.wait()
        outcomes[method]='complete' if code==0 else 'failed'
        if code!=0:
            atomic(RUN/'queue.json',dict(status='failed',method=method,exit_code=code,outcomes=outcomes))
            table()
            return code
    atomic(RUN/'queue.json',dict(status='complete',outcomes=outcomes,finished_at=time.time()))
    table()
    return 0


if __name__=='__main__':
    sys.exit(main())
