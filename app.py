import streamlit as st
import pandas as pd
import time
from google import genai
from google.genai import types

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# ==========================================
st.set_page_config(page_title="Portal de Estudos Fator", page_icon="🎓", layout="wide")

# Inicializar o estado da sessão para manter as notas salvas entre as páginas
if "medias_finais" not in st.session_state:
    st.session_state.medias_finais = {
        "Língua Portuguesa": 0.0, "Matemática": 0.0, "Biologia": 0.0, 
        "Educação Física": 0.0, "Filosofia": 0.0, "Física": 0.0, 
        "Geografia": 0.0, "História": 0.0, "Inglês": 0.0, "Química": 0.0
    }
if "meta_desejada" not in st.session_state: st.session_state.meta_desejada = 7.0
if "trilha_escolhida" not in st.session_state: st.session_state.trilha_escolhida = "Trilha das Palavras (Português/Redação)"
if "tarefas" not in st.session_state: st.session_state.tarefas = []

# Inicializar estados de memória para as respostas da IA
if "resposta_cronograma" not in st.session_state: st.session_state.resposta_cronograma = None
if "resposta_flashcards" not in st.session_state: st.session_state.resposta_flashcards = None
if "resposta_quiz" not in st.session_state: st.session_state.resposta_quiz = None

# Puxando a chave de API de forma segura a partir dos Secrets do Streamlit
CHAVE_API_GEMINI = st.secrets["CHAVE_API_GEMINI"]

# ==========================================
# 2. MENU LATERAL DE NAVEGAÇÃO
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/education.png", width=80)
    st.title("Portal Fator")
    st.markdown("---")
    
    menu_opcao = st.radio(
        "Navegar para:",
        [
            "🧮 Simulador de Notas (Fator)", 
            "🏠 Painel de Controlo Geral", 
            "🧠 Mentor Pedagógico IA", 
            "🎯 Espaço de Foco & Produtividade"
        ]
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Configurações Rápidas")
    st.session_state.meta_desejada = st.number_input("🎯 Meta de Nota:", min_value=0.0, max_value=10.0, value=st.session_state.meta_desejada, step=0.1)
    st.session_state.trilha_escolhida = st.radio(
        "🛤️ Trilha Ativa:",
        ["Trilha das Palavras (Português/Redação)", "Trilha dos Números (Matemática/Física)"],
        index=0 if "Palavras" in st.session_state.trilha_escolhida else 1
    )

# ==========================================
# FUNÇÕES AUXILIARES DE CÁLCULO (COM MEMÓRIA DO TIMESTAMPS)
# ==========================================
def calcular_subdivisao_bloco_a(id_chave, nome_exibicao):
    st.write(f"**{nome_exibicao}**")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Adicionado o st.session_state para puxar e salvar a nota em tempo real
    with c1: ava = st.number_input("AVA (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_ava")
    with c2: avt = st.number_input("AVT (Até 6.0)", min_value=0.0, max_value=6.0, step=0.1, key=f"mem_{id_chave}_avt")
    with c3: projeto = st.number_input("Projeto (Até 2.0)", min_value=0.0, max_value=2.0, step=0.1, key=f"mem_{id_chave}_proj")
    with c4: itinerario = st.number_input("Nota Itinerário (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_itin")
    with c5: bonus = st.number_input("Bónus Extra (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_bonus")
    
    nota_parcial = ava + avt + projeto + itinerario + bonus
    if nota_parcial > 10.0: nota_parcial = 10.0
    nota_final = nota_parcial
    
    if nota_parcial < 7.0:
        st.caption(f"⚠️ *{nome_exibicao} abaixo de 7.0. AVR disponível.*")
        avr = st.number_input("Nota da AVR (Até 10.0)", min_value=0.0, max_value=10.0, step=0.1, key=f"mem_{id_chave}_avr")
        if avr > 0:
            nova_avt = (avt + avr) / 2
            if nova_avt > 6.0: nova_avt = 6.0  
            nota_final = ava + nova_avt + projeto + itinerario + bonus
            if nota_final > 10.0: nota_final = 10.0
    return nota_final

def calcular_nota_materia_regular(id_chave, nome_exibicao):
    st.write(f"**{nome_exibicao}**")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1: ava = st.number_input("AVA (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_ava")
    with c2: avt = st.number_input("AVT (Até 6.0)", min_value=0.0, max_value=6.0, step=0.1, key=f"mem_{id_chave}_avt")
    with c3: projeto = st.number_input("Projeto (Até 2.0)", min_value=0.0, max_value=2.0, step=0.1, key=f"mem_{id_chave}_proj")
    with c4: itinerario = st.number_input("Nota Itinerário (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_itin")
    with c5: bonus = st.number_input("Bónus Extra (Até 1.0)", min_value=0.0, max_value=1.0, step=0.1, key=f"mem_{id_chave}_bonus")
    
    nota_parcial = ava + avt + projeto + itinerario + bonus
    if nota_parcial > 10.0: nota_parcial = 10.0
    nota_final = nota_parcial
    
    if nota_parcial < 7.0:
        st.caption(f"⚠️ *{nome_exibicao} abaixo de 7.0. AVR disponível.*")
        avr = st.number_input("Nota da AVR (Até 10.0)", min_value=0.0, max_value=10.0, step=0.1, key=f"mem_{id_chave}_avr")
        if avr > 0:
            nova_avt = (avt + avr) / 2
            if nova_avt > 6.0: nova_avt = 6.0
            nota_final = ava + nova_avt + projeto + itinerario + bonus
            if nota_final > 10.0: nota_final = 10.0
    return nota_final


# ==========================================
# LÓGICA DAS PÁGINAS DO MENU
# ==========================================

# --- MENU 1: SIMULADOR DE NOTAS ---
if menu_opcao == "🧮 Simulador de Notas (Fator)":
    st.title("🧮 Simulador de Notas Oficial - Colégio Fator")
    st.markdown("Lança aqui os teus componentes para alimentar os gráficos do teu painel geral.")
    st.markdown("---")
    
    st.header("📚 Bloco A: Matérias com Subdivisões")
    
    st.subheader("▶️ Componente: Língua Portuguesa")
    col_g, col_r = st.columns(2)
    with col_g: nota_final_gram = calcular_subdivisao_bloco_a("gram", "Subdivisão 1: Gramática")
    with col_r: nota_final_red = calcular_subdivisao_bloco_a("red", "Subdivisão 2: Produção de Texto (Redação)")
    
    media_portugues_final = (nota_final_gram + nota_final_red) / 2
    st.session_state.medias_finais["Língua Portuguesa"] = media_portugues_final
    
    if media_portugues_final >= 7.0:
        st.success(f"📈 **Média Final de Língua Portuguesa: {media_portugues_final:.2f}** (Aprovado)")
    else:
        st.error(f"❌ **Média Final de Língua Portuguesa: {media_portugues_final:.2f}** (Abaixo da média global)")
    
    st.markdown("---")
    
    st.subheader("▶️ Componente: Matemática")
    col_m1, col_m2 = st.columns(2)
    with col_m1: nota_final_mat1 = calcular_subdivisao_bloco_a("mat1", "Subdivisão 1: Matemática 1")
    with col_m2: nota_final_mat2 = calcular_subdivisao_bloco_a("mat2", "Subdivisão 2: Matemática 2")
    
    media_matematica_final = (nota_final_mat1 + nota_final_mat2) / 2
    st.session_state.medias_finais["Matemática"] = media_matematica_final
    
    if media_matematica_final >= 7.0:
        st.success(f"📈 **Média Final de Matemática: {media_matematica_final:.2f}** (Aprovado)")
    else:
        st.error(f"❌ **Média Final de Matemática: {media_matematica_final:.2f}** (Abaixo da média global)")
    
    st.markdown("---")
    st.header("📘 Bloco B: Matérias Regulares")
    materias_regulares = ["Biologia", "Educação Física", "Filosofia", "Física", "Geografia", "História", "Inglês", "Química"]
    
    for mat in materias_regulares:
        with st.expander(f"📖 {mat}"):
            nota_mat = calcular_nota_materia_regular(mat.lower().replace(" ", "_"), mat)
            st.session_state.medias_finais[mat] = nota_mat
            st.caption(f"Nota Final Registada: **{nota_mat:.2f}**")
            
    st.success("🔄 Notas guardadas com sucesso! Podes navegar livremente pelas abas.")


# --- MENU 2: PAINEL DE CONTROLO GERAL ---
elif menu_opcao == "🏠 Painel de Controlo Geral":
    st.title("🏠 Painel de Controlo Geral Académico")
    st.markdown("Acompanha o teu rendimento completo e métricas de desempenho estatístico.")
    st.markdown("---")
    
    df_notas = pd.DataFrame(list(st.session_state.medias_finais.items()), columns=["Matéria", "Nota Final"]).set_index("Matéria")
    
    media_geral = df_notas["Nota Final"].mean()
    melhor_materia = df_notas["Nota Final"].idxmax()
    nota_maxima = df_notas["Nota Final"].max()
    pior_materia = df_notas["Nota Final"].idxmin()
    nota_minima = df_notas["Nota Final"].min()
    
    col_est1, col_est2, col_est3 = st.columns(3)
    with col_est1: st.metric(label="🌍 Tua Média Geral Global", value=f"{media_geral:.2f}")
    with col_est2: st.metric(label="🚀 Teu Maior Desempenho", value=f"{nota_maxima:.2f}" if nota_maxima > 0 else "0.00", delta=melhor_materia if nota_maxima > 0 else "Nenhuma")
    with col_est3: st.metric(label="⚠️ Maior Ponto de Atenção", value=f"{nota_minima:.2f}" if nota_minima > 0 else "0.00", delta=pior_materia if nota_minima > 0 else "Nenhuma", delta_color="inverse")
    
    st.markdown("---")
    st.subheader("📉 Gráfico Analítico de Médias por Disciplina")
    st.bar_chart(df_notas, y_label="Notas", x_label="Disciplinas")
    
    st.markdown("---")
    st.subheader("🎯 Estado das Metas")
    criticas = [f"{m} ({n:.2f})" for m, n in st.session_state.medias_finais.items() if n < st.session_state.meta_desejada and n > 0]
    
    if not criticas or media_geral == 0:
        st.success(f"🎉 Excelente! Estás a cumprir a tua meta de {st.session_state.meta_desejada} em todas as frentes lançadas ou ainda não preencheste dados.")
    else:
        st.warning(f"⚠️ Atenção: Estás abaixo da tua meta em: {', '.join(criticas)}. Usa a aba do **Mentor Pedagógico IA** para te ajudar.")


# --- MENU 3: MENTOR PEDAGÓGICO IA ---
elif menu_opcao == "🧠 Mentor Pedagógico IA":
    st.title("🧠 Mentor Pedagógico com Inteligência Artificial")
    st.markdown("Gera planos de estudo, flashcards e quizes dinâmicos focados nas tuas dificuldades.")
    st.markdown("---")
    
    # Descobre quais matérias têm notas maiores que zero, porém abaixo da meta
    materias_criticas = [f"{m}: {n:.2f}" for m, n in st.session_state.medias_finais.items() if n < st.session_state.meta_desejada and n > 0]
    
    if not materias_criticas:
        st.info("💡 Não tens matérias críticas abaixo da meta neste momento! Vai ao simulador, adiciona algumas notas baixas para simular o cenário e regressa aqui para ativar a IA.")
    else:
        st.warning(f"⚠️ Matérias detetadas com necessidade de suporte: {', '.join(materias_criticas)}")
        
        # Criação das Sub-Abas internas do Mentor
        sub_cronograma, sub_flashcards, sub_quiz = st.tabs(["📅 Cronograma Semanal", "📇 Flashcards de Revisão", "📝 Quiz Interativo"])
        
        # --- SUB-ABA 1: CRONOGRAMA ---
        with sub_cronograma:
            st.subheader("📅 Plano e Cronograma de Estudos Customizado")
            estilo_estudo = st.selectbox("Como preferes estudar?", ["Vídeos e Aulas Práticas", "Resumos Escritos e Teoria", "Fazer Muitos Exercícios e Testes"])
            
            if st.button("🧠 Gerar o meu Cronograma"):
                with st.spinner("O Mentor IA está a estruturar as tuas metas..."):
                    try:
                        client = genai.Client(api_key=CHAVE_API_GEMINI)
                        instrucoes_IA = (
                            "Tu és o Mentor Pedagógico do Web App do Colégio Fator. "
                            f"O aluno tem como meta a nota {st.session_state.meta_desejada}. A média da escola é 7.0. "
                            f"Ele prefere focar em: {estilo_estudo}. Cria estratégias e um cronograma focado apenas nas matérias em crise."
                        )
                        resposta = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"Minhas matérias em risco: {str(materias_criticas)}. Monte o meu cronograma.",
                            config=types.GenerateContentConfig(system_instruction=instrucoes_IA, temperature=0.7)
                        )
                        st.session_state.resposta_cronograma = resposta.text
                    except Exception as e:
                        st.error(f"Erro: {e}")
            
            if st.session_state.resposta_cronograma:
                st.markdown("---")
                st.success("📝 **Teu Cronograma:**")
                st.write(st.session_state.resposta_cronograma)
                
        # --- SUB-ABA 2: FLASHCARDS ---
        with sub_flashcards:
            st.subheader("📇 Flashcards Rápidos de Memorização Ativa")
            st.markdown("Deixe que a IA crie perguntas e respostas rápidas para testar o teu cérebro.")
            
            if st.button("📇 Construir meus Flashcards"):
                with st.spinner("Compilando conceitos cruciais..."):
                    try:
                        client = genai.Client(api_key=CHAVE_API_GEMINI)
                        instrucoes_IA = (
                            "Tu és um professor do Colégio Fator especialista em memorização ativa. "
                            "Gere uma lista de 4 Flashcards de revisão estruturados estritamente no formato:\n"
                            "**CARD X - PERGUNTA:** [Escreva a pergunta sobre tópicos essenciais destas matérias]\n"
                            "**RESPOSTA:** [Escreva de forma curta e objetiva a resposta para o aluno validar]\n"
                            f"Foque estritamente em conteúdos fundamentais destas disciplinas: {str(materias_criticas)}."
                        )
                        resposta = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents="Gere os meus flashcards com base nas minhas matérias críticas.",
                            config=types.GenerateContentConfig(system_instruction=instrucoes_IA, temperature=0.7)
                        )
                        st.session_state.resposta_flashcards = resposta.text
                    except Exception as e:
                        st.error(f"Erro: {e}")
                        
            if st.session_state.resposta_flashcards:
                st.markdown("---")
                st.info("💡 **Dica:** Tenta responder mentalmente a pergunta antes de ler a resposta abaixo!")
                st.write(st.session_state.resposta_flashcards)

        # --- SUB-ABA 3: QUIZ DE TESTE ---
        with sub_quiz:
            st.subheader("📝 Mini-Simulado de Múltipla Escolha")
            st.markdown("Responda ao teste gerado pela IA e receba correção e explicação instantâneas.")
            
            if st.button("🎲 Solicitar Novo Teste à IA"):
                with st.spinner("Escrevendo questões exclusivas..."):
                    try:
                        client = genai.Client(api_key=CHAVE_API_GEMINI)
                        instrucoes_IA = (
                            "Tu és a banca examinadora de testes do Colégio Fator. "
                            f"Gere um teste de 2 perguntas de múltipla escolha cobrindo as matérias: {str(materias_criticas)}. "
                            "Gere as opções (A, B, C, D). "
                            "Logo abaixo do teste, adicione uma seção chamada 'GABARITO COMENTADO' escondendo as respostas corretas e explicando a lógica de cada uma de forma pedagógica."
                        )
                        resposta = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents="Gere o meu simulado de múltipla escolha com gabarito no final.",
                            config=types.GenerateContentConfig(system_instruction=instrucoes_IA, temperature=0.6)
                        )
                        st.session_state.resposta_quiz = resposta.text
                    except Exception as e:
                        st.error(f"Erro: {e}")
            
            if st.session_state.resposta_quiz:
                st.markdown("---")
                st.markdown("### 📝 Teu Teste:")
                st.write(st.session_state.resposta_quiz)


# --- MENU 4: ESPAÇO DE FOCO & PRODUTIVIDADE ---
elif menu_opcao == "🎯 Espaço de Foco & Produtividade":
    st.title("🎯 Espaço de Foco & Produtividade")
    st.markdown("Usa estas ferramentas para gerir o teu tempo e organizar os temas do Colégio Fator.")
    st.markdown("---")
    
    col_pom, col_todo = st.columns([1, 1])
    
    with col_pom:
        st.subheader("⏱️ Temporizador Pomodoro Fator")
        modo_relogio = st.checkbox("⏩ Modo de Teste Rápido (Acelerar cronómetro para demonstração)")
        tempo_total_segundos = 25 * 60 if not modo_relogio else 10
        
        container_timer = st.empty()
        barra_progresso = st.progress(0)
        
        if st.button("🚀 Iniciar Ciclo de Foco"):
            for t in range(tempo_total_segundos, -1, -1):
                mins, secs = divmod(t, 60)
                container_timer.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                percentagem = 1.0 - (t / tempo_total_segundos)
                barra_progresso.progress(percentagem)
                time.sleep(1.0 if not modo_relogio else 0.2)
                
            st.balloons()
            st.success("⏰ Tempo esgotado! Excelente trabalho de foco. Hora de uma pausa de 5 minutos.")
        else:
            container_timer.markdown("<h1 style='text-align: center; font-size: 80px; color: gray;'>25:00</h1>", unsafe_allow_html=True)
            
    with col_todo:
        st.subheader("📝 Lista de Trabalhos e Avaliações")
        nova_tarefa = st.text_input("Adicionar novo trabalho ou data de teste:")
        if st.button("➕ Adicionar Trabalho"):
            if nova_tarefa:
                st.session_state.tarefas.append(nova_tarefa)
                st.rerun()
                
        if st.session_state.tarefas:
            st.markdown("### 📌 O que tens para entregar:")
            for index, tarefa in enumerate(st.session_state.tarefas):
                c_tar, c_btn = st.columns([4, 1])
                with c_tar: st.write(f"- {tarefa}")
                with c_btn: 
                    if st.button("✔️ Done", key=f"btn_{index}"):
                        st.session_state.tarefas.pop(index)
                        st.rerun()
        else:
            st.info("Estás livre de tarefas pendentes por agora!")
