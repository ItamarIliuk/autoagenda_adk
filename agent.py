"""
AutoAgenda Agent - Implementação com Google ADK
Este módulo contém a implementação do agente de agendamento de manutenção automotiva
utilizando o Google Agent Development Kit (ADK).
"""

import os
import json
import datetime
import pytz
from typing import Optional, Dict, List, Any

# Importações do Google ADK
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Importações para autenticação e APIs do Google
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from googleapiclient.errors import HttpError

# Constantes e configurações
APP_NAME = "autoagenda_agent"
USER_ID = "user1234"
SESSION_ID = "session1234"
MODEL_ID = "gemini-2.0-flash"  # Usando o modelo mais recente do Gemini
TIMEZONE = 'America/Sao_Paulo'  # Fuso horário para operações de data/hora

# Configuração de autenticação
SERVICE_ACCOUNT_FILE_PATH = os.environ.get('SERVICE_ACCOUNT_FILE_PATH', '/path/to/service-account-key.json')
SHEET_ID = os.environ.get('GOOGLE_SHEET_ID', '')
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/spreadsheets']

# Inicialização das credenciais e serviços
def initialize_services():
    """
    Inicializa os serviços do Google (Calendar e Sheets) usando as credenciais do Service Account.
    
    Returns:
        tuple: (calendar_service, gspread_client) ou (None, None) em caso de erro
    """
    try:
        # Autenticação usando o arquivo de credenciais do Service Account
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE_PATH,
            scopes=SCOPES
        )
        
        # Inicializa o serviço do Google Calendar
        calendar_service = build('calendar', 'v3', credentials=creds)
        
        # Inicializa o cliente gspread para Google Sheets
        gc = gspread.authorize(creds)
        
        return calendar_service, gc
    except Exception as e:
        print(f"Erro ao inicializar serviços: {e}")
        return None, None

# Inicializa os serviços
calendar_service, gc = initialize_services()

# Definição das ferramentas (tools) do agente

def buscar_historico_cliente(placa_veiculo: str) -> Dict[str, Any]:
    """
    Busca o histórico de manutenção de um veículo na planilha do Google Sheets.
    
    Args:
        placa_veiculo (str): Número da placa do veículo a ser pesquisado.
        
    Returns:
        dict: Dicionário contendo status da operação ('success' ou 'error') e 
              os dados do histórico ou mensagem de erro.
    """
    if not gc or not SHEET_ID:
        return {
            "status": "error",
            "error_message": "Serviço do Google Sheets não configurado ou ID da planilha ausente."
        }
    
    try:
        sheet = gc.open_by_key(SHEET_ID).sheet1
        all_data = sheet.get_all_records()
        
        history = []
        plate_column_header = 'placa_veiculo'
        date_column_header = 'data_agendamento'
        km_column_header = 'km_atual'
        service_column_header = 'servico_realizado'
        notes_column_header = 'observacoes'
        
        if not all_data or plate_column_header not in all_data[0]:
            return {
                "status": "error",
                "error_message": f"Não foi possível encontrar a coluna '{plate_column_header}' na planilha ou a planilha está vazia."
            }
        
        for record in all_data:
            # Comparação case-insensitive e sem espaços extras
            if str(record.get(plate_column_header, '')).strip().upper() == placa_veiculo.strip().upper():
                entry = {
                    "Data": record.get(date_column_header, "N/A"),
                    "KM": record.get(km_column_header, "N/A"),
                    "Servico": record.get(service_column_header, "N/A"),
                    "Observacoes": record.get(notes_column_header, "")
                }
                history.append(entry)
        
        if not history:
            return {
                "status": "success",
                "message": f"Nenhum histórico encontrado para a placa {placa_veiculo}.",
                "data": []
            }
        else:
            # Retorna as últimas 3 entradas (assumindo que as mais recentes estão no final)
            last_three = history[-3:]
            return {
                "status": "success",
                "message": f"Histórico encontrado para a placa {placa_veiculo}.",
                "data": last_three
            }
    
    except gspread.exceptions.APIError as e:
        return {
            "status": "error",
            "error_message": f"Erro ao acessar a API do Google Sheets: {e}. Verifique as permissões."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Erro ao buscar histórico no Google Sheets: {e}"
        }

def registrar_manutencao_planilha(
    nome_cliente: str, 
    contato: str, 
    placa_veiculo: str, 
    modelo_veiculo: str,
    ano_veiculo: str, 
    km_atual: str, 
    data_agendamento: str,
    hora_agendamento: str, 
    servico_agendado: str, 
    observacoes: str = ""
) -> Dict[str, Any]:
    """
    Registra um novo agendamento de manutenção na planilha do Google Sheets.
    
    Args:
        nome_cliente (str): Nome do cliente.
        contato (str): Informações de contato do cliente.
        placa_veiculo (str): Placa do veículo.
        modelo_veiculo (str): Modelo do veículo.
        ano_veiculo (str): Ano do veículo.
        km_atual (str): Quilometragem atual do veículo.
        data_agendamento (str): Data do agendamento (formato YYYY-MM-DD).
        hora_agendamento (str): Hora do agendamento (formato HH:MM).
        servico_agendado (str): Descrição do serviço agendado.
        observacoes (str, opcional): Observações adicionais.
        
    Returns:
        dict: Dicionário contendo status da operação ('success' ou 'error') e 
              mensagem de confirmação ou erro.
    """
    if not gc or not SHEET_ID:
        return {
            "status": "error",
            "error_message": "Serviço do Google Sheets não configurado ou ID da planilha ausente."
        }
    
    try:
        sheet = gc.open_by_key(SHEET_ID).sheet1
        
        # Define o fuso horário desejado
        target_timezone = pytz.timezone(TIMEZONE)
        
        # Obtém a hora atual em UTC (timezone-aware)
        utc_now = datetime.datetime.now(pytz.utc)
        
        # Converte a hora UTC para o fuso horário local
        local_time = utc_now.astimezone(target_timezone)
        
        # Formata a hora local para a string desejada (sem info de fuso no final)
        local_timestamp_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Cria a nova linha para adicionar à planilha
        # IMPORTANTE: Esta ordem DEVE corresponder EXATAMENTE à ordem das colunas do Google Sheet
        new_row = [
            "",  # CustomerID (ou outro valor)
            nome_cliente,
            contato,
            placa_veiculo,
            modelo_veiculo,
            ano_veiculo,
            km_atual,
            data_agendamento,
            hora_agendamento,
            servico_agendado,
            observacoes,
            local_timestamp_str  # Timestamp local formatado
        ]
        
        sheet.append_row(new_row)
        
        return {
            "status": "success",
            "message": f"Agendamento para {nome_cliente} (placa {placa_veiculo}) registrado com sucesso na planilha."
        }
    
    except gspread.exceptions.APIError as e:
        return {
            "status": "error",
            "error_message": f"Erro ao acessar a API do Google Sheets: {e}. Verifique as permissões."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Erro ao registrar manutenção no Google Sheets: {e}"
        }

def verificar_disponibilidade_agenda(data_iso: str, duracao_minutos: int = 60) -> Dict[str, Any]:
    """
    Verifica a disponibilidade de horários na agenda do Google Calendar para uma data específica.
    
    Args:
        data_iso (str): Data no formato ISO (YYYY-MM-DD).
        duracao_minutos (int, opcional): Duração do compromisso em minutos. Padrão é 60 minutos.
        
    Returns:
        dict: Dicionário contendo status da operação ('success' ou 'error'),
              lista de horários disponíveis ou mensagem de erro.
    """
    if not calendar_service:
        return {
            "status": "error",
            "error_message": "Serviço do Google Calendar não configurado."
        }
    
    try:
        # Configuração de fuso horário e horário de trabalho
        time_zone = TIMEZONE
        start_time_of_day = datetime.time(9, 0)  # 9:00 AM
        end_time_of_day = datetime.time(18, 0)   # 6:00 PM
        
        # Converte a data ISO para objeto datetime
        start_date = datetime.datetime.fromisoformat(data_iso)
        
        # Cria os timestamps para a consulta de disponibilidade
        time_min_dt = datetime.datetime.combine(start_date, start_time_of_day).isoformat() + 'Z'
        time_max_dt = datetime.datetime.combine(start_date, end_time_of_day).isoformat() + 'Z'
        
        # Corpo da requisição para a API do Google Calendar
        body = {
            "timeMin": time_min_dt,
            "timeMax": time_max_dt,
            "timeZone": time_zone,
            "items": [{"id": "primary"}]  # Verifica o calendário primário
        }
        
        # Executa a consulta de disponibilidade
        events_result = calendar_service.freebusy().query(body=body).execute()
        busy_slots = events_result.get('calendars', {}).get('primary', {}).get('busy', [])
        
        # Calcula os horários disponíveis
        available_slots = []
        current_check_time = datetime.datetime.combine(start_date, start_time_of_day)
        end_of_work_dt = datetime.datetime.combine(start_date, end_time_of_day)
        slot_duration = datetime.timedelta(minutes=duracao_minutos)
        
        while current_check_time + slot_duration <= end_of_work_dt:
            is_free = True
            slot_end_time = current_check_time + slot_duration
            
            # Verifica sobreposição com horários ocupados
            for busy in busy_slots:
                busy_start = datetime.datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                busy_end = datetime.datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                
                # Converte para comparação
                current_check_time_aware = datetime.datetime.fromisoformat(f"{current_check_time.strftime('%Y-%m-%dT%H:%M:%S')}")
                slot_end_time_aware = datetime.datetime.fromisoformat(f"{slot_end_time.strftime('%Y-%m-%dT%H:%M:%S')}")
                
                # Verifica se o slot proposto [start, end) se sobrepõe ao slot ocupado [busy_start, busy_end)
                if max(current_check_time_aware, busy_start.replace(tzinfo=None)) < min(slot_end_time_aware, busy_end.replace(tzinfo=None)):
                    is_free = False
                    # Move o tempo de verificação para o final deste slot ocupado
                    current_check_time = busy_end.replace(tzinfo=None)
                    break
            
            if is_free:
                # Formata HH:MM usando o datetime original
                available_slots.append(current_check_time.strftime("%H:%M"))
                # Move para o próximo horário potencial
                current_check_time += slot_duration
            # Se não estiver livre, current_check_time já foi avançado além do slot ocupado
        
        if not available_slots:
            return {
                "status": "success",
                "message": f"Nenhum horário disponível encontrado para {data_iso} com duração de {duracao_minutos} minutos entre {start_time_of_day.strftime('%H:%M')} e {end_time_of_day.strftime('%H:%M')}.",
                "available_slots": []
            }
        else:
            return {
                "status": "success",
                "message": f"Horários disponíveis para {data_iso} (duração de {duracao_minutos} min).",
                "available_slots": available_slots
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Erro ao verificar disponibilidade no Google Calendar: {e}"
        }

def criar_evento_agenda(
    titulo: str, 
    data_iso: str, 
    hora_inicio: str, 
    duracao_minutos: int,
    descricao: str = "", 
    email_convidado: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria um evento no Google Calendar.
    
    Args:
        titulo (str): Título do evento.
        data_iso (str): Data no formato ISO (YYYY-MM-DD).
        hora_inicio (str): Hora de início no formato HH:MM.
        duracao_minutos (int): Duração do evento em minutos.
        descricao (str, opcional): Descrição do evento.
        email_convidado (str, opcional): Email do convidado para o evento.
        
    Returns:
        dict: Dicionário contendo status da operação ('success' ou 'error'),
              detalhes do evento criado ou mensagem de erro.
    """
    if not calendar_service:
        return {
            "status": "error",
            "error_message": "Serviço do Google Calendar não configurado."
        }
    
    try:
        # Converte a data e hora para objetos datetime
        start_datetime = datetime.datetime.fromisoformat(f"{data_iso}T{hora_inicio}:00")
        end_datetime = start_datetime + datetime.timedelta(minutes=duracao_minutos)
        
        # Configuração de fuso horário
        time_zone = TIMEZONE
        
        # Cria o corpo do evento
        event = {
            'summary': titulo,
            'location': 'Oficina',  # Opcional: define um local padrão
            'description': descricao,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': time_zone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': time_zone,
            },
            'reminders': {'useDefault': True},
        }
        
        # Adiciona convidados se especificado
        attendees = []
        if email_convidado:
            attendees.append({'email': email_convidado})
            event['attendees'] = attendees
            send_notifications = True
        else:
            send_notifications = False
        
        # Cria o evento no Google Calendar
        created_event = calendar_service.events().insert(
            calendarId='primary',
            body=event,
            sendNotifications=send_notifications
        ).execute()
        
        return {
            "status": "success",
            "message": f"Evento '{created_event.get('summary')}' criado com sucesso em {data_iso} às {hora_inicio}.",
            "event_id": created_event.get('id'),
            "event_link": created_event.get('htmlLink')
        }
    
    except HttpError as e:
        error_details = json.loads(e.content).get('error', {})
        reason = error_details.get('errors', [{}])[0].get('reason')
        message = error_details.get('message')
        
        if e.resp.status == 403 and reason == 'forbiddenForServiceAccounts':
            error_msg = (
                "Erro: Falha ao criar evento. A conta de serviço pode não ter permissão "
                f"para adicionar convidados ('{email_convidado}') ou enviar notificações. "
                "Tente criar o evento sem um email de convidado, ou verifique as configurações de delegação de domínio do Google Workspace."
            )
            return {
                "status": "error",
                "error_message": error_msg
            }
        else:
            # Erro HTTP genérico
            return {
                "status": "error",
                "error_message": f"Erro ao criar evento no Google Calendar (HTTP {e.resp.status}): {message or e}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Erro geral ao criar evento no Google Calendar: {e}"
        }

# Criação das ferramentas (FunctionTools) para o ADK
buscar_historico_tool = FunctionTool(func=buscar_historico_cliente)
registrar_manutencao_tool = FunctionTool(func=registrar_manutencao_planilha)
verificar_disponibilidade_tool = FunctionTool(func=verificar_disponibilidade_agenda)
criar_evento_tool = FunctionTool(func=criar_evento_agenda)

# Definição do agente principal
autoagenda_agent = Agent(
    name="autoagenda_agent",
    model=MODEL_ID,
    description="Agente para agendar manutenções de veículos e consultar histórico de serviços.",
    instruction="""
    Você é um assistente especializado em agendamento de manutenção de veículos.
    
    Suas principais funções são:
    1. Consultar o histórico de manutenção de veículos usando a placa como identificador
    2. Verificar horários disponíveis na agenda para novas manutenções
    3. Agendar novas manutenções e registrá-las na planilha de controle
    
    Você tem acesso às seguintes ferramentas:
    
    - buscar_historico_cliente: Use esta ferramenta quando o usuário quiser consultar o histórico de manutenção de um veículo. Você precisa da placa do veículo para fazer a consulta.
      - Se o status retornado for "success", apresente os dados do histórico de forma organizada.
      - Se o status for "error", informe o erro ao usuário e peça informações adicionais se necessário.
    
    - verificar_disponibilidade_agenda: Use esta ferramenta quando o usuário quiser verificar horários disponíveis para agendamento. Você precisa da data (formato YYYY-MM-DD) e opcionalmente da duração em minutos (padrão é 60 minutos).
      - Se o status retornado for "success", apresente os horários disponíveis de forma organizada.
      - Se não houver horários disponíveis, sugira datas alternativas.
      - Se o status for "error", informe o erro ao usuário.
    
    - registrar_manutencao_planilha: Use esta ferramenta para registrar um novo agendamento na planilha. Você precisa coletar todas as informações necessárias do cliente e do veículo antes de usar esta ferramenta.
      - Se o status retornado for "success", confirme o registro ao usuário.
      - Se o status for "error", informe o erro ao usuário e tente novamente se possível.
    
    - criar_evento_agenda: Use esta ferramenta para criar um evento no Google Calendar após registrar a manutenção na planilha. Você precisa do título, data, hora de início e duração.
      - Se o status retornado for "success", confirme a criação do evento ao usuário.
      - Se o status for "error", informe o erro ao usuário, mas garanta que o registro na planilha foi feito.
    
    Fluxo de trabalho recomendado para agendamento:
    1. Colete informações do cliente e do veículo
    2. Verifique a disponibilidade na agenda para a data desejada
    3. Confirme o horário escolhido com o cliente
    4. Registre a manutenção na planilha
    5. Crie o evento no calendário
    6. Confirme o agendamento completo ao cliente
    
    Seja sempre cordial e profissional. Forneça informações claras e precisas.
    """,
    tools=[
        buscar_historico_tool,
        registrar_manutencao_tool,
        verificar_disponibilidade_tool,
        criar_evento_tool
    ],
)

# Configuração do runner para execução do agente
def get_runner():
    """
    Cria e retorna um runner para execução do agente.
    
    Returns:
        Runner: Instância configurada do runner para o agente.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=autoagenda_agent,
        session_service=session_service
    )
    return runner

# Função principal para executar o agente em modo interativo
def run_interactive():
    """
    Executa o agente em modo interativo via console.
    """
    runner = get_runner()
    session = runner.create_session(USER_ID, SESSION_ID)
    
    print("=" * 50)
    print("   AutoAgenda - Agente de Agendamento de Manutenção   ")
    print("=" * 50)
    print("\nOlá! Como posso ajudar com o agendamento ou verificação do histórico do seu veículo hoje?")
    print("Exemplos: 'Qual o histórico da placa ABC1234?', 'Agendar troca de óleo para amanhã'.")
    print("Digite 'sair' a qualquer momento para encerrar.")
    print("-" * 50)
    
    while True:
        user_input = input("\nVocê: ")
        if user_input.lower() == 'sair':
            print("\nAgente: Entendido. Até logo!")
            break
        
        print("Agente: Processando...")
        response = runner.send_message(session, user_input)
        print(f"\nAgente: {response.text}")

# Ponto de entrada para execução direta do script
if __name__ == "__main__":
    run_interactive()
