"""Minimal logging reverse proxy: localhost:11435 -> localhost:11434. Logs request/response summaries to proxy.log."""
import http.server, json, time, urllib.request, sys, socketserver
LOG = open("proxy.log", "a", buffering=1)
UP = "http://127.0.0.1:11434"

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _proxy(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        t0 = time.time()
        summary = {"t": time.strftime("%H:%M:%S"), "m": self.command, "path": self.path}
        if body:
            try:
                j = json.loads(body)
                summary.update({k: j.get(k) for k in ("model","stream","reasoning_effort","max_tokens","temperature","tool_choice","response_format","think") if k in j})
                summary["keys"] = sorted(j.keys())
                if "messages" in j: summary["n_messages"] = len(j["messages"]); summary["roles"] = [m.get("role") for m in j["messages"]][-6:]; summary["sys_chars"] = sum(len(str(m.get("content",""))) for m in j["messages"] if m.get("role")=="system")
                if "tools" in j: summary["n_tools"] = len(j["tools"]); summary["tool_names"] = [t["function"]["name"] for t in j["tools"]][:40]
                if "extra_body" in j: summary["extra_body"] = j["extra_body"]
                for k in j:
                    if k not in ("model","messages","tools","stream","reasoning_effort","max_tokens","temperature","tool_choice","response_format","think","stream_options","user"):
                        summary.setdefault("other", {})[k] = j[k]
            except Exception as e:
                summary["body_err"] = str(e); summary["raw"] = body[:300].decode(errors="replace")
        req = urllib.request.Request(UP + self.path, data=body, method=self.command, headers={k:v for k,v in self.headers.items() if k.lower() not in ("host","content-length")})
        try:
            with urllib.request.urlopen(req, timeout=3600) as r:
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding","content-length","connection"): self.send_header(k, v)
                self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
                total = b""; reasoning = 0; content = 0; toolcalls = 0
                while True:
                    chunk = r.read(4096)
                    if not chunk: break
                    total += chunk
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk)); self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                summary["status"] = r.status
        except urllib.error.HTTPError as e:
            data = e.read(); summary["status"] = e.code; summary["err_body"] = data[:500].decode(errors="replace")
            self.send_response(e.code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); total = b""
        summary["secs"] = round(time.time() - t0, 1)
        # response summary
        try:
            txt = total.decode(errors="replace")
            if txt.startswith("data:") or "\ndata:" in txt:
                r_len = c_len = tc = 0; finish = None
                for line in txt.splitlines():
                    if line.startswith("data:") and line[5:].strip() not in ("", "[DONE]"):
                        d = json.loads(line[5:]); ch = (d.get("choices") or [{}])[0]; delta = ch.get("delta", {})
                        r_len += len(delta.get("reasoning") or delta.get("reasoning_content") or ""); c_len += len(delta.get("content") or "")
                        tc += len(delta.get("tool_calls") or []); finish = ch.get("finish_reason") or finish
                        if "usage" in d and d["usage"]: summary["usage"] = d["usage"]
                summary.update({"resp_reasoning_chars": r_len, "resp_content_chars": c_len, "resp_toolcall_deltas": tc, "finish": finish})
            elif txt:
                d = json.loads(txt)
                if "choices" in d:
                    m = d["choices"][0].get("message", {}); summary.update({"resp_reasoning_chars": len(m.get("reasoning") or ""), "resp_content_chars": len(m.get("content") or ""), "resp_tool_calls": [t["function"]["name"] for t in (m.get("tool_calls") or [])], "finish": d["choices"][0].get("finish_reason"), "usage": d.get("usage")})
                else: summary["resp_keys"] = list(d.keys())[:8]
        except Exception as e:
            summary["resp_parse_err"] = str(e)[:100]
        LOG.write(json.dumps(summary, ensure_ascii=False) + "\n")
    do_GET = do_POST = do_DELETE = do_HEAD = _proxy

class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
S(("127.0.0.1", 11435), H).serve_forever()
