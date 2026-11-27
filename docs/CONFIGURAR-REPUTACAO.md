# Configurar os provedores de reputação do Spectra

O Spectra consulta fontes externas para verificar se uma URL aparece em listas de ameaças. As três integrações são independentes. Você pode ativar uma por vez.

| Provedor | Variável de ambiente |
| --- | --- |
| Google Safe Browsing | `SPECTRA_GSB_API_KEY` |
| VirusTotal | `SPECTRA_VT_API_KEY` |
| PhishTank | `SPECTRA_PHISHTANK_APP_KEY` |

## Obter as credenciais

### Google Safe Browsing

1. Crie ou selecione um projeto no Google Cloud Console.
2. Em **APIs e serviços → Biblioteca**, habilite **Safe Browsing API**.
3. Em **APIs e serviços → Credenciais**, selecione **Criar credenciais → Chave de API**.
4. Na configuração da chave, restrinja o acesso à **Safe Browsing API**. Use a chave desse projeto na variável `SPECTRA_GSB_API_KEY`.

O Spectra usa a API v4, cujo uso é destinado a projetos não comerciais. [Configuração da API](https://developers.google.com/safe-browsing/v4/get-started) · [Condições de uso](https://developers.google.com/safe-browsing/v4/usage-limits)

### VirusTotal

1. Crie uma conta na comunidade do VirusTotal e entre nela.
2. Abra **API Key** no menu do perfil.
3. Copie a chave para `SPECTRA_VT_API_KEY`.

A API pública tem cotas e restrições de uso comercial. [Minha chave no VirusTotal](https://www.virustotal.com/gui/my-apikey) · [Condições da API](https://docs.virustotal.com/docs/api-overview)

### PhishTank

Se você já tem uma conta, consulte a área de desenvolvedores para obter uma **Application Key** e configure `SPECTRA_PHISHTANK_APP_KEY`. Em 27 de novembro de 2026, a página de cadastro informava que novas contas estavam temporariamente desativadas. Se você ainda não tem acesso, deixe essa variável sem preencher. [Cadastro do PhishTank](https://phishtank.org/register.php) · [Informações para desenvolvedores](https://www.phishtank.org/developer_info.php)

## Configurar no Render

1. Abra o serviço **Spectra** no painel do Render e entre em **Environment**.
2. Selecione **Add Environment Variable** para cada provedor que quiser ativar. Em **Key**, coloque o nome exato da tabela. Em **Value**, cole a chave correspondente.
3. Selecione **Save, rebuild, and deploy**. Aguarde a publicação do backend.
4. Em **Deploys**, confirme que a revisão publicada inclui o commit `6ae2702`, que remove credenciais e URLs dos erros exibidos no laudo.

Guarde os valores nas variáveis do servidor. Mantenha as chaves fora do GitHub, do JavaScript do navegador e de capturas de tela. [Variáveis de ambiente no Render](https://render.com/docs/configure-environment-variables) · [Correção do Spectra](https://github.com/NickSantos18/Spectra_/commit/6ae2702981d6c1c62e1b405c0bb3474e79cd022b)

## Confirmar que funcionou

1. Abra [o estado do serviço](https://spectra-jo6j.onrender.com/api/saude) e procure o objeto `provedores`. `true` indica que o servidor carregou a chave. Se aparecer `false`, confira o nome da variável, o serviço selecionado e se o deploy terminou.
2. Analise `https://example.com` no modo online. No laudo, abra a seção de reputação. Um resultado como **limpo**, **malicioso** ou **desconhecido** mostra que houve retorno da fonte. **Desconhecido** indica ausência de registro naquela fonte.
3. Se aparecer **erro**, confira no laudo o código devolvido pelo provedor. Para `403`, confira as permissões da chave e a API habilitada. Para `429`, confira a cota. URLs com possíveis credenciais podem ter a consulta externa omitida para proteger seus dados.

Leia o resultado de reputação junto das demais evidências do laudo. Ausência de denúncia em uma lista não confirma a segurança do endereço.
