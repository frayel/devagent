import os

# Evita crash do parser de proxy do httpx quando NO_PROXY contém [::1] (Invalid port: ':1]')
for _var in ("NO_PROXY", "no_proxy"):
    _val = os.environ.get(_var)
    if _val and "[::1]" in _val:
        os.environ[_var] = (
            _val.replace(",[::1]", "").replace("[::1],", "").replace("[::1]", "")
        )
