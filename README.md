# AutoAgenda com Google ADK - Documentação

## Visão Geral

Este projeto implementa um agente de agendamento de manutenção automotiva utilizando o Google Agent Development Kit (ADK). O agente é capaz de:

1. Consultar o histórico de manutenção de veículos em uma planilha do Google Sheets
2. Verificar horários disponíveis no Google Calendar
3. Agendar novas manutenções, registrando na planilha e criando eventos no calendário
4. Este projeto atende a demanda de um cliente específico, mas pode ser adaptado para outros casos de uso
5. O agente foi encomendado pela AutoMecânica Glavão de Ponta Grossa - PR
6. O projeto foi desenvolvido por [Itamar Iliuk](https://github.com/ItamarIliuk) e é parte do meu portfólio de projetos.
7. O projeto foi desenvolvido com o apoio do Google Cloud e do Google AI Studio, utilizando a API Gemini para processamento de linguagem natural.
8. O projeto é uma demonstração de como integrar serviços do Google Cloud com um agente conversacional, utilizando o Google ADK para facilitar a construção e implementação do agente.
9. O projeto é uma prova de conceito e pode ser expandido para incluir mais funcionalidades, como integração com outros serviços de agendamento ou suporte a múltiplos idiomas

## Estrutura do Projeto

```
autoagenda_adk/
├── __init__.py        # Importação do módulo agent
├── agent.py           # Implementação principal do agente
├── requirements.txt   # Dependências do projeto
└── .env               # Arquivo para configurações e chaves de API (não versionado)
```

## Requisitos

- Python 3.9+
- Conta Google com APIs habilitadas:
  - Google Calendar API
  - Google Sheets API
  - Gemini API (Google AI Studio ou Vertex AI)
- Arquivo de credenciais de Service Account com permissões para Calendar e Sheets

## Instalação

1. Clone o repositório ou copie os arquivos para sua máquina
2. Crie e ative um ambiente virtual:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```
3. Instale as dependências:
   ```
   pip install -r autoagenda_adk/requirements.txt
   ```
4. Configure o arquivo `.env` na pasta `autoagenda_adk/`:
   ```
   SERVICE_ACCOUNT_FILE_PATH=/caminho/para/seu-arquivo-credenciais.json
   GOOGLE_SHEET_ID=seu_id_da_planilha
   GOOGLE_API_KEY=sua_chave_api_gemini  # Se usar Google AI Studio
   GOOGLE_GENAI_USE_VERTEXAI=FALSE      # Mude para TRUE se usar Vertex AI
   ```

## Configuração do Google Workspace

### Google Sheets
1. Crie uma planilha no Google Sheets com as seguintes colunas:
   - CustomerID
   - ClientName (nome_cliente)
   - ContactInfo (contato)
   - VehiclePlate (placa_veiculo)
   - VehicleModel (modelo_veiculo)
   - VehicleYear (ano_veiculo)
   - CurrentKM (km_atual)
   - AppointmentDate (data_agendamento)
   - AppointmentTime (hora_agendamento)
   - ServiceRequested (servico_agendado)
   - Notes (observacoes)
   - LogTimestamp
2. Compartilhe a planilha com o email da sua Service Account com permissão de Editor

### Google Calendar
1. Compartilhe seu calendário com o email da Service Account com permissão para fazer alterações nos eventos

## Funcionalidades Implementadas

### 1. Busca de Histórico de Manutenção
- Função: `buscar_historico_cliente(placa_veiculo)`
- Descrição: Busca registros de manutenção anteriores com base na placa do veículo
- Retorno: Dicionário com status e dados do histórico ou mensagem de erro

### 2. Verificação de Disponibilidade
- Função: `verificar_disponibilidade_agenda(data_iso, duracao_minutos=60)`
- Descrição: Verifica horários disponíveis em uma data específica
- Retorno: Dicionário com status e lista de horários disponíveis ou mensagem de erro

### 3. Registro de Manutenção
- Função: `registrar_manutencao_planilha(nome_cliente, contato, placa_veiculo, modelo_veiculo, ano_veiculo, km_atual, data_agendamento, hora_agendamento, servico_agendado, observacoes="")`
- Descrição: Registra um novo agendamento de manutenção na planilha
- Retorno: Dicionário com status e mensagem de confirmação ou erro

### 4. Criação de Evento
- Função: `criar_evento_agenda(titulo, data_iso, hora_inicio, duracao_minutos, descricao="", email_convidado=None)`
- Descrição: Cria um evento no Google Calendar
- Retorno: Dicionário com status, detalhes do evento criado ou mensagem de erro

## Uso do Agente

### Modo Interativo
Para executar o agente em modo interativo via console:

```python
from autoagenda_adk.agent import run_interactive

run_interactive()
```

### Integração em Aplicações
Para integrar o agente em suas próprias aplicações:

```python
from autoagenda_adk.agent import get_runner

# Inicializa o runner
runner = get_runner()

# Cria uma sessão
session = runner.create_session("user_id", "session_id")

# Envia mensagens para o agente
response = runner.send_message(session, "Qual o histórico da placa ABC1234?")
print(response.text)
```

## A implementação com Google ADK apresenta as seguintes melhorias:

1. **Estrutura Modular**: Organização mais clara e modular do código
2. **Retornos Padronizados**: Todas as funções retornam dicionários com status e dados consistentes
3. **Melhor Tratamento de Erros**: Tratamento mais robusto de exceções e erros
4. **Instruções Detalhadas**: O agente possui instruções mais detalhadas sobre como usar as ferramentas
5. **Sessões Persistentes**: Suporte a sessões para manter o contexto da conversa

## Personalização

Para personalizar o agente:

1. **Modelo**: Altere o `MODEL_ID` no arquivo `agent.py` para usar um modelo diferente
2. **Instruções**: Modifique o texto em `instruction` na definição do `autoagenda_agent` para ajustar o comportamento
3. **Fuso Horário**: Ajuste a constante `TIMEZONE` para seu fuso horário local
4. **Horário de Trabalho**: Modifique `start_time_of_day` e `end_time_of_day` na função `verificar_disponibilidade_agenda`

## Solução de Problemas

### Erros de Autenticação
- Verifique se o arquivo de credenciais da Service Account está correto
- Confirme se as APIs necessárias estão habilitadas no projeto do Google Cloud
- Verifique se a planilha e o calendário foram compartilhados com o email da Service Account

### Erros ao Adicionar Convidados
- A Service Account pode não ter permissão para adicionar convidados diretamente
- Considere configurar a delegação de domínio para a Service Account ou criar eventos sem convidados

### Erros de Formato de Data/Hora
- Certifique-se de usar o formato ISO para datas (YYYY-MM-DD)
- Use o formato 24h para horários (HH:MM)
