import re

with open("app/services/gemini_modelo.py", "r") as f:
    content = f.read()

nova_funcao = """

async def laco_validacao() -> None:
    import asyncio
    from app.collectors import sistema as monitor_sistema

    while True:
        if not monitor_sistema.monitor_ligado():
            await asyncio.sleep(60)
            continue

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                await asyncio.to_thread(_listar_modelos, api_key)
            except Exception:
                pass

        await asyncio.sleep(6 * 3600)
"""

if "async def laco_validacao" not in content:
    content = content + nova_funcao

with open("app/services/gemini_modelo.py", "w") as f:
    f.write(content)

with open("app/main.py", "r") as f:
    content_main = f.read()

main_patch = """
    if monitor_sistema.monitor_ligado():
        tarefas.append(asyncio.create_task(monitor_sistema.laco_do_monitor()))
        from app.services import gemini_modelo
        tarefas.append(asyncio.create_task(gemini_modelo.laco_validacao()))
"""

content_main = content_main.replace(
    "    if monitor_sistema.monitor_ligado():\n        tarefas.append(asyncio.create_task(monitor_sistema.laco_do_monitor()))",
    main_patch
)

with open("app/main.py", "w") as f:
    f.write(content_main)
