# Simulador de Geração de Caixas - Versão Consolidada 3D

import streamlit as st
import pandas as pd
import io

# --- Configuração inicial ---
st.set_page_config(page_title="Simulador de Caixas", page_icon="📦", layout="wide")
st.title("📦 Simulador de Caixas por Loja e Braço")

# --- Controle de estado ---
if "df_resultado_3d" not in st.session_state:
    st.session_state.df_resultado_3d = None
if "arquivo_atual" not in st.session_state:
    st.session_state.arquivo_atual = None
if "volume_maximo" not in st.session_state:
    st.session_state.volume_maximo = 37.0
if "peso_maximo" not in st.session_state:
    st.session_state.peso_maximo = 20.0

# --- Parâmetros ---
col1, col2= st.columns(2)
with col1:
    peso_temp = st.number_input("⚖️ Peso máximo por caixa (KG)", value=st.session_state.peso_maximo, step=0.1)
with col2:
    arquivo = st.file_uploader("📂 Selecionar arquivo (.xlsx)", type=["xlsx"])

col4, col5 = st.columns(2)
with col4:
    ignorar_braco = st.checkbox("🔃 Ignorar braço ao agrupar caixas", value=False)
with col5:
    converter_pac_para_un = st.checkbox("🔄 Converter PAC para UN para otimização", value=False)

# --- Parâmetros 3D ---
st.markdown("---")
st.subheader("📦 Parâmetros do Empacotamento 3D")
col6, col7, col8, col9 = st.columns(4)
with col6:
    comprimento_caixa = st.number_input("📏 Comprimento da caixa 3D (cm)", value=40.0, step=1.0)
with col7:
    largura_caixa = st.number_input("📏 Largura da caixa 3D (cm)", value=30.0, step=1.0)
with col8:
    altura_caixa = st.number_input("📏 Altura da caixa 3D (cm)", value=25.0, step=1.0)
with col9:
    ocupacao_maxima = st.number_input("🔲 % de ocupação máxima (3D)", value=100.0, step=1.0, min_value=1.0, max_value=100.0)

# Detecta troca de arquivo
if arquivo is not None and arquivo != st.session_state.arquivo_atual:
    st.session_state.arquivo_atual = arquivo
    st.session_state.df_resultado_3d = None

# --- Função Empacotar 3D Corrigida ---
def empacotar_3d(df_base, df_mestre, comprimento_caixa, largura_caixa, altura_caixa, peso_max, ocupacao_percentual):
    volume_caixa_litros = (comprimento_caixa * largura_caixa * altura_caixa * (ocupacao_percentual / 100)) / 1000
    resultado = []
    caixa_id = 1

    # Junta a base com o mestre para pegar as dimensões corretas
    df_join = pd.merge(df_base, df_mestre, how='left', left_on=['ID_Produto', 'Unidade med.altern.'], right_on=['Produto', 'UM alternativa'])
    
    # Aviso se o merge não trouxe resultados
    if df_join.empty:
        st.warning("⚠️ Atenção: Não houve correspondência no merge. Verifique se os campos 'ID_Produto' e 'UM alternativa' estão corretos.")

    # Filtra registros que têm dimensões válidas
    df_join = df_join.dropna(subset=['Comprimento', 'Largura', 'Altura'])
    
    itens = []
    for _, row in df_join.iterrows():
        qtd = int(row["Qtd.prev.orig.UMA"])
        volume_un = (row["Comprimento"] * row["Largura"] * row["Altura"]) / 1000
        peso_bruto = row.get("Peso bruto", 0) or 0
        unidade_peso = str(row.get("Unidade de peso", "")).upper()
        
        peso_un = (peso_bruto / 1000) if unidade_peso == "G" else peso_bruto

        for _ in range(qtd):
            itens.append({
                "ID_Produto": row["ID_Produto"],
                "ID_Loja": row["ID_Loja"],
                "Braço": row["Braço"] if not ignorar_braco else "Todos",
                "Volume": volume_un,
                "Peso": peso_un,
                "Descricao": row["Descrição_produto"]
            })

    caixas = []
    for item in sorted(itens, key=lambda x: x["Volume"], reverse=True):
        colocado = False
        for cx in caixas:
            if (cx["volume"] + item["Volume"] <= volume_caixa_litros) and (cx["peso"] + item["Peso"] <= peso_max) and (cx["ID_Loja"] == item["ID_Loja"]) and (cx["Braço"] == item["Braço"]):
                cx["volume"] += item["Volume"]
                cx["peso"] += item["Peso"]
                cx["produtos"].append(item)
                colocado = True
                break
        if not colocado:
            caixas.append({
                "ID_Caixa": f"CX3D_{caixa_id}",
                "ID_Loja": item["ID_Loja"],
                "Braço": item["Braço"],
                "volume": item["Volume"],
                "peso": item["Peso"],
                "produtos": [item]
            })
            caixa_id += 1

    for cx in caixas:
        for prod in cx["produtos"]:
            resultado.append({
                "ID_Caixa": cx["ID_Caixa"],
                "ID_Loja": cx["ID_Loja"],
                "Braço": cx["Braço"],
                "ID_Produto": prod["ID_Produto"],
                "Descrição_produto": prod["Descricao"],
                "Volume_item(L)": prod["Volume"],
                "Peso_item(KG)": prod["Peso"],
                "Volume_caixa_total(L)": cx["volume"],
                "Peso_caixa_total(KG)": cx["peso"]
            })

    return pd.DataFrame(resultado)

# --- Execução ---
if arquivo:
    try:
        df_base = pd.read_excel(arquivo, sheet_name="Base")
        df_mestre = pd.read_excel(arquivo, sheet_name="Dados.Mestre")

        if st.button("🚀 Gerar Caixas (3D)"):
            st.session_state.volume_maximo = volume_temp
            st.session_state.peso_maximo = peso_temp

            # 3D 
            st.session_state.df_resultado_3d = empacotar_3d(df_base.copy(), df_mestre.copy(), comprimento_caixa, largura_caixa, altura_caixa, peso_temp, ocupacao_maxima)

            total_3d = st.session_state.df_resultado_3d["ID_Caixa"].nunique()
            st.info(f"📦 Total de caixas geradas (3D): {total_3d}")

            df_caixas_3d = st.session_state.df_resultado_3d.drop_duplicates(subset=["ID_Caixa", "Volume_caixa_total(L)", "Peso_caixa_total(KG)"])
            media_volume_3d = (df_caixas_3d["Volume_caixa_total(L)"].mean() / ((comprimento_caixa * largura_caixa * altura_caixa)/1000)) * 100
            media_peso_3d = (df_caixas_3d["Peso_caixa_total(KG)"].mean() / peso_temp) * 100
            st.info(f"📈 Eficiência média das caixas 3D:\n• Volume: {media_volume_3d:.1f}%\n• Peso: {media_peso_3d:.1f}%")

            # Comparativo Loja / Braço 3D
            comparativo_sistema_3d = df_base.groupby(["ID_Loja", "Braço"]).agg(Caixas_Sistema=("ID_Caixa", "nunique")).reset_index()
            comparativo_gerado_3d = st.session_state.df_resultado_3d.drop_duplicates(subset=["ID_Loja", "Braço", "ID_Caixa"])
            comparativo_gerado_3d = comparativo_gerado_3d.groupby(["ID_Loja", "Braço"]).agg(Caixas_App=("ID_Caixa", "nunique")).reset_index()
            comparativo_3d = pd.merge(comparativo_sistema_3d, comparativo_gerado_3d, on=["ID_Loja", "Braço"], how="outer").fillna(0)
            comparativo_3d["Diferença"] = comparativo_3d["Caixas_App"] - comparativo_3d["Caixas_Sistema"]

            st.subheader("📊 Comparativo de Caixas por Loja e Braço (3D)")
            st.dataframe(comparativo_3d)

            st.markdown('<h3><img src="https://raw.githubusercontent.com/MySpaceCrazy/Simulador_Caixas_3D/refs/heads/main/caixa-aberta.ico" width="24" style="vertical-align:middle;"> Detalhe caixas 3D</h3>', unsafe_allow_html=True)
            st.dataframe(st.session_state.df_resultado_3d)

            # Download Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                st.session_state.df_resultado_3d.to_excel(writer, sheet_name="Resumo Caixas 3D", index=False)
            st.download_button("📥 Baixar Relatório Completo", data=buffer.getvalue(), file_name="Relatorio_Caixas_3D.xlsx")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
