# Liberados x Montados — Dashboard

Dashboard em Streamlit para comparar pedidos **Liberados** (aguardando montagem)
com pedidos **Montados** (já roteirizados/expedidos), por estado: AM, BA, DF,
MG/ES, SP e SP-WFS.

## Como funciona a comparação

Os dois arquivos **não representam o mesmo pedido em dois momentos** — um
pedido sai da lista de Liberados quando é montado. Por isso a comparação é
feita por **volume e ritmo por estado**, não pedido a pedido:

- **Backlog**: quantos pedidos/peso/valor estão liberados e ainda pendentes
- **Aging**: há quanto tempo cada pedido pendente está liberado (faixas de 0-2h, 2-6h, 6-12h, 12-24h, 24h+)
- **Corte**: se o estado tem horário de corte configurado, marca como "atrasado"
  todo pedido liberado antes do corte e que ainda não foi montado
- **Histórico intradiário**: cada snapshot salvo (botão na aba "Histórico do dia")
  vira uma linha no Google Sheets, permitindo ver a evolução do backlog ao longo do dia

## Limitação conhecida

O arquivo de Montados só tem a **data** de término (`Data de término`), sem
horário. Isso significa que o tempo exato entre liberação e montagem só pode
ser estimado em nível de dia, não de hora — a não ser que o time de
roteirização passe a exportar um campo de hora/minuto de finalização também.

## Estrutura do projeto

```
.
├── app.py                  # App Streamlit principal
├── config/
│   └── estados.py          # Estados suportados + configuração padrão de corte
├── src/
│   ├── etl.py               # Leitura e normalização dos arquivos
│   ├── metricas.py           # Cálculo de backlog, aging, corte, comparativo
│   └── gsheets.py            # Histórico e configuração via Google Sheets
├── requirements.txt
└── .streamlit/
    └── secrets.toml.example  # Modelo de configuração de secrets
```

## 1. Configurar o Google Sheets (histórico)

Isso é opcional — o app funciona sem, só não guarda histórico entre sessões.

1. Crie uma planilha nova no Google Sheets (pode ficar em branco, as abas
   `HISTORICO` e `CONFIG_CORTE` são criadas automaticamente pelo app).
2. Acesse o [Google Cloud Console](https://console.cloud.google.com/), crie um
   projeto (ou use um existente).
3. Ative as APIs **Google Sheets API** e **Google Drive API** no projeto.
4. Vá em **IAM & Admin > Service Accounts** e crie uma conta de serviço.
5. Nessa conta de serviço, gere uma **chave JSON** e baixe o arquivo.
6. Copie o valor de `client_email` do JSON e **compartilhe a planilha** do
   passo 1 com esse e-mail (permissão de Editor).
7. Pegue o ID da planilha (o trecho da URL entre `/d/` e `/edit`).

## 2. Configurar os secrets

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e
preencha com os dados da chave JSON gerada e o ID da planilha.
**Esse arquivo nunca deve ser commitado no GitHub** (já está no `.gitignore`).

Para rodar local:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 3. Subir no GitHub

```bash
git add .
git commit -m "Dashboard Liberados x Montados"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

## 4. Deploy no Streamlit Community Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub.
2. Clique em "New app", selecione o repositório e o arquivo `app.py`.
3. Em **Advanced settings > Secrets**, cole o conteúdo do seu
   `.streamlit/secrets.toml` (com os dados reais).
4. Deploy. A cada `git push` na branch main o app atualiza automaticamente.

## Uso no dia a dia

1. Extraia os arquivos LIBERADOS_*.xls e MONTADOS_*.xlsx dos seus sistemas.
2. Suba todos de uma vez no app (a caixa de upload aceita múltiplos arquivos).
3. Confirme o estado/tipo detectado de cada arquivo.
4. Veja os indicadores na tela.
5. Clique em "Salvar snapshot no histórico" para registrar esse momento e
   acompanhar a evolução ao longo do dia.

## Próximos passos sugeridos

- Validar e ajustar os horários de corte reais por estado na barra lateral
  (hoje estão como valores de exemplo/sugestão)
- Automatizar a extração dos arquivos (se os sistemas de origem tiverem API
  ou exportação agendada), eliminando o upload manual
- Adicionar autenticação simples no app se for usado por várias pessoas
