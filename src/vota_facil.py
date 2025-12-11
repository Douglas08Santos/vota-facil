import streamlit as st
import pandas as pd
import qrcode
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import time

BLOQUEIO_SEGUNDOS = 10  # ajuste como quiser

def botoes_bloqueados():
    agora = time.time()
    return (agora - st.session_state.ultima_acao) < BLOQUEIO_SEGUNDOS

# --------------------------
# CONFIGURAÇÕES
# --------------------------
st.set_page_config(page_title='Vota Fácil', layout='centered')

OPCOES = ['Alumia', 'Lumia', 'Luzia']
DESCRICAO = {
    'Alumia': 'Um termo regionalizado, muito presente na fala do nosso povo, que lembra o verbo “alumiar”, de iluminar, clarear o que está obscuro – exatamente o que se espera do controle externo sobre as informações governamentais.',
    'Lumia': 'Remete a “lumen”, do latim, e a termos de línguas modernas associados à claridade.',
    'Luzia': 'Um nome feminino, que humaniza a tecnologia e aproxima o sistema das pessoas. “Luzia” evoca também Santa Luzia, tradicionalmente associada à visão, à capacidade de enxergar com clareza, dialogando com a missão de ver melhor as contas públicas e ampliar a transparência.',
}
SPREADSHEET_ID = st.secrets['sheets']['SPREADSHEET_ID']

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS = Credentials.from_service_account_info(
    st.secrets['gcp_service_account'], scopes=SCOPES
)
# --------------------------
# GOOGLE SHEETS
# --------------------------

def get_sheet_service():
    return build('sheets', 'v4', credentials=CREDS)

def registrar_voto(opcao):
    service = get_sheet_service()
    body = {
        'values': [[pd.Timestamp.now().isoformat(), opcao]]
    }
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='A:B',
        valueInputOption='RAW',
        body=body
    ).execute()

def carregar_votos():
    service = get_sheet_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='A:B'
    ).execute()

    values = result.get('values', [])

    if not values or len(values) <= 1:
        return pd.DataFrame(columns=['timestamp', 'opcao'])

    return pd.DataFrame(values[1:], columns=['timestamp', 'opcao'])


# --------------------------
# QR CODE
# --------------------------
def gerar_qrcode(url):
    img = qrcode.make(url)
    path = 'qrcode.png'
    img.save(path)
    return path


# --------------------------
# INTERFACE
# --------------------------

st.subheader('Nome do projeto - Validação PNTP TCE/RN')

# Variável de estado para controlar a opção escolhida
if 'opcao_selecionada' not in st.session_state:
    st.session_state.opcao_selecionada = None

if "ultima_acao" not in st.session_state:
    st.session_state.ultima_acao = 0
# --------------------------
# DIALOG DE CONFIRMAÇÃO
# --------------------------
@st.dialog('Confirmar voto')
def confirmar_voto_dialog():
    opcao = st.session_state.opcao_selecionada
    
    st.markdown('### Você escolheu: **{}**'.format(opcao))
    st.markdown('{}'.format(DESCRICAO[opcao]))
    st.markdown('Caso esteja certo, confirme seu voto abaixo.')
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✔️ Confirmar", use_container_width=True):
            registrar_voto(opcao)
            st.session_state.ultima_acao = time.time()  # ← ativa o bloqueio
            st.session_state.opcao_selecionada = None
            st.success(f"Voto confirmado para **{opcao}**!")
            st.rerun()

    with col2:
        if st.button('❌ Escolher outra', use_container_width=True):
            st.session_state.opcao_selecionada = None
            st.rerun()

# --------------------------
# BOTÕES DE OPÇÕES
# --------------------------
st.subheader("Escolha sua opção:")

bloqueado = botoes_bloqueados()

if bloqueado:
    restante = BLOQUEIO_SEGUNDOS - int(time.time() - st.session_state.ultima_acao)
    #st.info(f"Aguarde {restante} segundos para votar novamente.")
    st.info(f"Voto registrado, atualize a página se deseja votar novamente.")

st.markdown("""
    <style>
    button {
        height: 70px !important; 
        padding-top: 10px !important; 
        padding-bottom: 10px !important; 
    }
    </style>
    """, unsafe_allow_html=True)

for opcao in OPCOES:
    if st.button(opcao, use_container_width=True, disabled=bloqueado):
        st.session_state.opcao_selecionada = opcao
        confirmar_voto_dialog()

for opcao in DESCRICAO.keys():
    st.write('**{}**:{}'.format(opcao, DESCRICAO[opcao]))
st.divider()
df = carregar_votos()
st.subheader('Resultado Parcial - {} participantes'.format(len(df)))
df = carregar_votos()
if not df.empty:
    contagem = df['opcao'].value_counts().reindex(OPCOES, fill_value=0)
    st.bar_chart(contagem, )
else:
    st.write('Ainda sem votos.')


st.divider()


url_app = ('https://consulta-publica.streamlit.app')
qr_path = gerar_qrcode(url_app)

# --------------------------
# POP-UP (MODAL) DE QR CODE
# --------------------------
@st.dialog('QR Code para Votação')
def mostrar_qrcode():
    st.markdown('### 📱 Aponte a câmera do celular para votar')
    st.image(qr_path, use_container_width=True)
    st.write('Clique fora do diálogo para fechar.')


#st.subheader('Compartilhe com o público')
#if st.button('Mostrar QR Code em Tela Cheia', type='primary', use_container_width=True):
#    mostrar_qrcode()
