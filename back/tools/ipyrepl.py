"""Public API
==========
run_python(code: str, *, session: str | None = None, timeout: int = 30) -> dict
    • If *session* is None ⇒ stateless (identical to the non‑persistent version).
    • Otherwise, the kernel for that session is reused until `reset_session(sess)`
      or the process exits.
reset_session(session: str) -> None
    Kills the kernel + client and frees resources.

Notes
-----
• Uses jupyter_client (kernel_manager) so we stay pure‑Python – no "jupyter" CLI
  required at runtime.
• Each session communicates over in‑proc zmq channels; still protected by the
  outer `multiprocessing` timeout + kill guard.
• We still capture Matplotlib figures & PIL images by inspecting the kernel
  user_ns via `%who` + `get_ipython().user_ns` executed inside the kernel.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import datetime
import json
import base64
import traceback
from io import BytesIO, StringIO
from typing import Optional, Dict, Tuple
from jupyter_client.manager import KernelManager
from jupyter_client.blocking.client import BlockingKernelClient
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from contextlib import redirect_stdout, redirect_stderr

# Kernel startup helper ---------------------------------------------------------

def start_new_kernel(kernel_name: str = "python3") -> tuple[KernelManager, BlockingKernelClient] | None:
    """Start a new kernel and return (KernelManager, BlockingKernelClient) pair."""
    try:
        km = KernelManager(kernel_name=kernel_name)
        km.start_kernel()
        kc = km.blocking_client()
        kc.wait_for_ready()
        return km, kc
    except Exception:
        return None

_sessions: dict[str, tuple[KernelManager, BlockingKernelClient]] = {}

# Helper: base64 encode images --------------------------------------------------

def _b64_png(buf: bytes) -> str:
    return base64.b64encode(buf).decode()


def _extract_images(ns):
    if plt is None or Image is None:
        return []

    imgs = []
    for num in plt.get_fignums():
        fig = plt.figure(num)
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        imgs.append(_b64_png(buf.getvalue()))
        plt.close(fig)
    for obj in ns.values():
        if isinstance(obj, Image.Image):
            buf = BytesIO()
            obj.save(buf, format="PNG")
            imgs.append(_b64_png(buf.getvalue()))
    return imgs

# Worker -----------------------------------------------------------------------

def _worker(code: str, session: Optional[str], timeout: int, q: mp.Queue):
    out, err = StringIO(), StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            if session:
                km, kc = _sessions.get(session, (None, None))
                if km is None or kc is None or not km.is_alive():
                    kernel_pair = start_new_kernel(kernel_name="python3")
                    if kernel_pair is None:
                        raise RuntimeError("Failed to start kernel")
                    km, kc = kernel_pair
                    _sessions[session] = (km, kc)
            else:
                kernel_pair = start_new_kernel(kernel_name="python3")
                if kernel_pair is None:
                    raise RuntimeError("Failed to start kernel")
                km, kc = kernel_pair

            kc.execute(code)
            kc.wait_for_ready(timeout=timeout)
            reply = kc.get_shell_msg(timeout=timeout)["content"]
            status = reply.get("status")
            if status == "error":
                raise RuntimeError("\n".join(reply.get("traceback", [])))
            # fetch last result via _ in user_ns
            kc.execute("import json, inspect, matplotlib.pyplot as plt, sys")
            kc.execute("_last = locals().get('_', None)")
            kc.execute("import dill, base64, types, builtins")
            kc.execute("print(repr(_last))")
            # user namespace images
            kc.execute("import inspect, matplotlib.pyplot as plt")
            ns_imgs_code = (
                "import json, base64, io, matplotlib.pyplot as plt, sys;"
                "from PIL import Image;"
                "def _cap():\n"
                " imgs=[]\n"
                " import builtins, gc;ns=globals();\n"
                " for num in plt.get_fignums():\n"
                "  fig=plt.figure(num);b=io.BytesIO();fig.savefig(b,format='png');b.seek(0);\n"
                "  imgs.append(base64.b64encode(b.read()).decode());plt.close(fig)\n"
                " for v in ns.values():\n"
                "  from PIL import Image as _Image;\n"
                "  if isinstance(v,_Image):b=io.BytesIO();v.save(b,format='PNG');b.seek(0);imgs.append(base64.b64encode(b.read()).decode())\n"
                " print(json.dumps(imgs))\n"
            )
            msg_id = kc.execute(ns_imgs_code)
            images = []
            if session:
                while True:
                    msg = kc.get_iopub_msg(timeout=timeout)
                    if msg["msg_type"] == "stream" and msg["content"].get("name") == "stdout":
                        try:
                            images = json.loads(msg["content"]["text"].strip())
                        except json.JSONDecodeError:
                            pass
                    elif msg["msg_type"] == "status" and msg["content"].get("execution_state") == "idle":
                        break

        data = dict(stdout=out.getvalue(), stderr=err.getvalue(), images=images)
    except Exception as e:
        data = dict(error="".join(traceback.format_exception(None, e, e.__traceback__)),
                    stdout=out.getvalue(), stderr=err.getvalue(), images=[])
    q.put(data)

# Public API --------------------------------------------------------------------

def run_python(code: str, *, session: str | None = None, timeout: int = 30) -> dict:
    """Execute code, optionally in a persistent *session*.

    Returns `{stdout, stderr, images, error?}` dict.
    """
    q: mp.SimpleQueue = mp.SimpleQueue()
    p = mp.Process(target=_worker, args=(code, session, timeout, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.kill(); p.join()
        return {"error": "Execution timed out", "images": []}
    return q.get() if not q.empty() else {"stdout": ""}


def reset_session(session: str) -> None:
    pair = _sessions.pop(session, None)
    if pair is None:
        return

    km, kc = pair
    kc.shutdown()
    km.shutdown_kernel(now=True)

