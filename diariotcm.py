import os
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

# Nome da sua planilha no Colab
PLANILHA_PATH = "Processos_doe.xlsx"

if not os.path.exists(PLANILHA_PATH):
    print(f"ERRO: Ficheiro '{PLANILHA_PATH}' não foi encontrado.")
    print("Por favor, faça o upload da sua planilha no menu de Ficheiros (ícone de pasta à esquerda).")
else:
    print(f"Ficheiro '{PLANILHA_PATH}' localizado. A ler processos...")
    df = pd.read_excel(PLANILHA_PATH, dtype={'processo': str})
    processos_busca = [str(p).strip().lower() for p in df['processo'].dropna().tolist()]
    print(f"Processos a monitorizar ({len(processos_busca)}): {processos_busca}")

    async def executar_automacao():
        async with async_playwright() as p:
            print("\nA iniciar o navegador em modo headless no Colab...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            print("A aceder ao site do TCM-BA (https://egbanet.egba.ba.gov.br/tcm)...")
            await page.goto("https://egbanet.egba.ba.gov.br/tcm")
            await page.wait_for_load_state("networkidle")

            # 3. Clica no botão do PDF para abrir a edição
            btn_pdf = page.locator("a:has-text('PDF'), span:has-text('PDF')").first
            if await btn_pdf.is_visible():
                await btn_pdf.click()
                await page.wait_for_load_state("networkidle")
            else:
                print("ERRO: Não foi possível localizar o botão do PDF.")
                await browser.close()
                return

            # 4. Localiza o seletor de páginas (<select class=\"select-pagina\">)
            seletor_pagina = page.locator("select.select-pagina")

            if await seletor_pagina.is_visible():
                opcoes_paginas = await page.eval_on_selector_all(
                    "select.select-pagina option",
                    "elements => elements.map(el => el.value)"
                )
                print(f"Edição do dia carregada! Total de páginas: {len(opcoes_paginas)}")

                processo_encontrado = False
                processo_detectado = ""
                pagina_detectada = ""

                # Varre página por página
                for num_pagina in opcoes_paginas:
                    await seletor_pagina.select_option(value=num_pagina)
                    await page.wait_for_timeout(800) # Aguarda o carregamento do texto da página

                    texto_pagina = (await page.content()).lower()

                    for proc in processos_busca:
                        if proc in texto_pagina:
                            processo_detectado = proc
                            pagina_detectada = num_pagina
                            processo_encontrado = True
                            break

                    if processo_encontrado:
                        break

                # 5. Se encontrar algum processo, clica no botão de download da edição completa
                if processo_encontrado:
                    print(f"\nSUCESSO! O processo '{processo_detectado}' foi encontrado na PÁGINA {pagina_detectada}!")
                    print("A descarregar a edição completa do diário...")

                    btn_download = page.locator("#baixar-diario-completo, a.full-download")

                    if await btn_download.is_visible():
                        async with page.expect_download() as download_info:
                            await btn_download.click()

                        download = await download_info.value
                        caminho_destino = "Edicao_Completa_Diario.pdf"
                        await download.save_as(caminho_destino)
                        print(f"Download concluído! O PDF foi salvo na barra lateral do Colab como: '{caminho_destino}'")
                    else:
                        print("ERRO: Botão de download da edição completa não foi localizado.")
                else:
                    print("\nNenhum dos processos da sua planilha foi localizado na edição do diário de hoje.")
            else:
                print("ERRO: Menu suspenso de páginas (<select class='select-pagina'>) não foi localizado.")

            await browser.close()
            print("\nExecução finalizada.")

    # Executa a tarefa assíncrona de forma segura dentro do ambiente Jupyter
    await executar_automacao()
