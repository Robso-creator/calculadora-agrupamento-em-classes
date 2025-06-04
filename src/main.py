import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

st.set_page_config(
    page_title="Calculadora Estatística",
    layout="wide",
    menu_items={
        'About': "# Calculadora de Estatística para Dados Agrupados\n"
                 "Esta aplicação permite calcular estatísticas descritivas para dados agrupados em classes."
    }
)


def main():
    st.title("Calculadora de Estatística para Dados Agrupados")

    # Adicionar informações sobre a aplicação
    with st.expander("Sobre esta aplicação", expanded=False):
        st.markdown("""
        ### Sobre
        Esta aplicação permite calcular estatísticas descritivas para dados agrupados em classes, incluindo:
        - Média
        - Mediana
        - Moda bruta (incluindo múltiplas modas)
        - Moda de Czuber (incluindo múltiplas modas)
        - Variância
        - Desvio padrão
        - Coeficiente de variação

        ### Desenvolvido por
        Aplicação desenvolvida com Streamlit, Pandas, NumPy e Matplotlib.
        """)

    st.markdown("""
    Esta aplicação permite calcular estatísticas descritivas para dados agrupados em classes.

    ### Instruções:
    1. Insira os dados na tabela abaixo
    2. Para cada classe, você pode inserir:
       - Intervalo de classe (ex: "8-10", "10-12", "8 a 10", "10 até 12")
       - Frequência simples (fi)
       - Frequência acumulada (faq)
    3. A aplicação calculará automaticamente os valores faltantes e as estatísticas
    """)

    # Inicializar dados na sessão apenas uma vez
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame({
            'Classe': ['15-19', '19-23', '23-27', '27-31', '31-35'],
            'fi': ['5', '13', '13', '11', '10'],
            'faq': ['', '', '', '', '']
        })

    # Inicializar flag para controlar atualizações
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False

    # Interface para edição da tabela
    with st.expander("Tabela de Dados", expanded=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            # Usar formulário para evitar atualizações automáticas
            with st.form(key="data_form"):
                # Editor de tabela
                edited_data = st.data_editor(
                    st.session_state.data,
                    num_rows="dynamic",
                    key="data_editor",
                    column_config={
                        "Classe": st.column_config.TextColumn("Classe (ex: 8-10)"),
                        "fi": st.column_config.TextColumn("Frequência (fi)"),
                        "faq": st.column_config.TextColumn("Freq. Acumulada (faq)")
                    },
                    hide_index=True,
                    disabled=False
                )

                # Botão de submissão do formulário
                submit_button = st.form_submit_button(label="Atualizar Dados")

                if submit_button:
                    st.session_state.data = edited_data
                    st.session_state.form_submitted = True

        with col2:
            st.markdown("### Exemplo de entrada (Multimodal):")
            st.markdown("""
            | Classe | fi | faq |
            |--------|----|----|
            | 15-19  | 5  | 5  |
            | 19-23  | 13 | 18 |
            | 23-27  | 13 | 31 |
            | 27-31  | 11 | 42 |
            | 31-35  | 10 | 52 |
            """)

    # Botão para processar os dados
    if st.button("Calcular Estatísticas", type="primary"):
        # Verificar se há dados suficientes
        if len(st.session_state.data) < 2 or not any(st.session_state.data['Classe'].astype(str).str.strip() != ''):
            st.error("Por favor, insira pelo menos duas classes com valores.")
            return

        # Processar os dados
        try:
            processed_data = process_data(st.session_state.data)

            # Exibir tabela processada
            st.subheader("Tabela de Frequências Completa")
            st.dataframe(processed_data, use_container_width=True)

            # Calcular e exibir estatísticas
            display_statistics(processed_data)


        except Exception as e:
            st.error(f"Erro ao processar os dados: {str(e)}")
            st.error("Verifique se os dados estão no formato correto.")

            # Mostrar dicas específicas para erros comuns
            if "extract_class_limits" in str(e):
                st.warning("""
                **Dica para formato de classes:**
                - Use formatos como "8-10", "8 a 10", "8 até 10"
                - Certifique-se de que os números estão separados por hífen, "a" ou "até"
                - Não use outros separadores como ":" ou "/"
                """)
            elif "fi" in str(e) and "faq" in str(e):
                st.warning("""
                **Dica para frequências:**
                - Você deve fornecer pelo menos uma coluna completa (fi ou faq)
                - Se fornecer frequências acumuladas (faq), elas devem estar em ordem crescente
                - Certifique-se de que todos os valores são numéricos
                """)


def process_data(data):
    """Processa os dados da tabela, preenchendo valores faltantes e calculando estatísticas."""
    # Copiar dados para não modificar o original
    df = data.copy()

    # Remover linhas vazias
    df = df[df['Classe'].astype(str).str.strip() != '']

    # Verificar se há pelo menos uma coluna com dados suficientes
    if (df['fi'].astype(str).str.strip() == '').all() and (df['faq'].astype(str).str.strip() == '').all():
        raise ValueError("É necessário fornecer valores para frequência (fi) ou frequência acumulada (faq)")

    # Extrair limites das classes
    try:
        df[['limite_inferior', 'limite_superior']] = df['Classe'].apply(extract_class_limits).apply(pd.Series)
    except Exception as e:
        raise ValueError(f"Erro ao extrair limites das classes. Verifique o formato: {str(e)}")

    # Verificar se os intervalos de classe são consistentes
    check_class_consistency(df)

    # Converter colunas para numérico, mantendo vazios como NaN
    df['fi'] = pd.to_numeric(df['fi'], errors='coerce')
    df['faq'] = pd.to_numeric(df['faq'], errors='coerce')

    # Ordenar por limite inferior para garantir a ordem correta
    df = df.sort_values('limite_inferior').reset_index(drop=True)

    # Calcular fi a partir de faq se necessário
    if df['fi'].isna().any() and not df['faq'].isna().all():
        df = calculate_fi_from_faq(df)

    # Calcular faq a partir de fi se necessário
    if df['faq'].isna().any() and not df['fi'].isna().all():
        df['faq'] = df['fi'].cumsum()

    # Verificar se ainda há valores faltantes após os cálculos
    if df['fi'].isna().any() or df['faq'].isna().any():
        raise ValueError("Não foi possível calcular todos os valores faltantes. Forneça mais dados.")

    # Calcular amplitude das classes
    df['amplitude'] = df['limite_superior'] - df['limite_inferior']

    # Verificar se as amplitudes são consistentes
    if not np.allclose(df['amplitude'].values, df['amplitude'].values[0], rtol=1e-5):
        st.warning("As classes têm amplitudes diferentes. Isso pode afetar a precisão de alguns cálculos estatísticos.")

    # Calcular ponto médio das classes
    df['xi'] = (df['limite_inferior'] + df['limite_superior']) / 2

    # Calcular fi.xi
    df['fi_xi'] = df['fi'] * df['xi']

    # Arredondar todas as colunas numéricas para duas casas decimais
    numeric_cols = ['limite_inferior', 'limite_superior', 'amplitude', 'xi', 'fi_xi']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].round(2)

    return df


def check_class_consistency(df):
    """Verifica se os intervalos de classe são consistentes."""
    # Verificar se há sobreposição ou lacunas entre classes
    df_sorted = df.sort_values('limite_inferior').reset_index(drop=True)

    for i in range(1, len(df_sorted)):
        current_lower = df_sorted.loc[i, 'limite_inferior']
        previous_upper = df_sorted.loc[i - 1, 'limite_superior']

        # Verificar sobreposição
        if current_lower < previous_upper:
            st.warning(
                f"Sobreposição detectada entre as classes: {df_sorted.loc[i - 1, 'Classe']} e {df_sorted.loc[i, 'Classe']}")

        # Verificar lacunas
        if current_lower > previous_upper:
            st.warning(
                f"Lacuna detectada entre as classes: {df_sorted.loc[i - 1, 'Classe']} e {df_sorted.loc[i, 'Classe']}")


def extract_class_limits(class_str):
    """Extrai os limites inferior e superior de uma string de classe."""
    # Remover espaços
    class_str = str(class_str).strip()

    # Padrões comuns: "8-10", "8 a 10", "8 até 10", etc.
    patterns = [
        r'(\d+[\.,]?\d*)\s*[-]\s*(\d+[\.,]?\d*)',  # 8-10
        r'(\d+[\.,]?\d*)\s*[a]\s*(\d+[\.,]?\d*)',  # 8 a 10
        r'(\d+[\.,]?\d*)\s*[até]\s*(\d+[\.,]?\d*)'  # 8 até 10
    ]

    for pattern in patterns:
        match = re.search(pattern, class_str)
        if match:
            lower = float(match.group(1).replace(',', '.'))
            upper = float(match.group(2).replace(',', '.'))
            return lower, upper

    # Se não encontrar padrão, tentar extrair números diretamente
    numbers = re.findall(r'\d+[\.,]?\d*', class_str)
    if len(numbers) >= 2:
        return float(numbers[0].replace(',', '.')), float(numbers[1].replace(',', '.'))

    raise ValueError(f"Não foi possível extrair limites da classe: {class_str}")


def calculate_fi_from_faq(df):
    """Calcula frequências simples a partir das frequências acumuladas."""
    # Verificar se as frequências acumuladas estão em ordem crescente
    if not df['faq'].is_monotonic_increasing:
        raise ValueError("As frequências acumuladas devem estar em ordem crescente")

    # Primeira frequência é igual à primeira faq
    if not pd.isna(df.loc[0, 'faq']):
        df.loc[0, 'fi'] = df.loc[0, 'faq']

    # Para as demais, fi = faq_atual - faq_anterior
    for i in range(1, len(df)):
        if not pd.isna(df.loc[i, 'faq']) and not pd.isna(df.loc[i - 1, 'faq']):
            df.loc[i, 'fi'] = df.loc[i, 'faq'] - df.loc[i - 1, 'faq']

    return df


def display_statistics(df):
    """Exibe as estatísticas calculadas."""
    st.subheader("Estatísticas Descritivas")

    col1, col2 = st.columns(2)

    # Calcular estatísticas
    total_fi = df['fi'].sum()

    # Média
    media = round((df['fi_xi'].sum() / total_fi), 2)

    # Mediana
    mediana = round(calculate_median(df), 2)

    # Moda bruta
    modas_brutas = calculate_raw_mode(df)

    # Moda de Czuber
    modas_czuber = calculate_czuber_mode(df)

    # Variância e desvio padrão
    df['fi_xi_menos_media_quadrado'] = df['fi'] * ((df['xi'] - media) ** 2)
    variancia = round((df['fi_xi_menos_media_quadrado'].sum() / total_fi), 2)
    desvio_padrao = round(np.sqrt(variancia), 2)

    # Coeficiente de variação
    coef_variacao = round((desvio_padrao / media) * 100, 2) if media != 0 else np.nan

    # Exibir resultados
    with col1:
        st.metric("Média", f"{media:.2f}")
        st.metric("Mediana", f"{mediana:.2f}")

        # Exibir modas
        if isinstance(modas_brutas, list):
            st.markdown("**Modas Brutas:**")
            for moda in modas_brutas:
                st.markdown(f"- {moda:.2f}")
        elif pd.isna(modas_brutas):
            st.markdown("**Moda Bruta:** Amodal")
        else:
            st.metric("Moda Bruta", f"{modas_brutas:.2f}")

        if isinstance(modas_czuber, list):
            st.markdown("**Modas de Czuber:**")
            for moda in modas_czuber:
                st.markdown(f"- {moda:.2f}")
        elif pd.isna(modas_czuber):
            st.markdown("**Moda de Czuber:** Amodal")
        else:
            st.metric("Moda de Czuber", f"{modas_czuber:.2f}")

    with col2:
        st.metric("Variância", f"{variancia:.2f}")
        st.metric("Desvio Padrão", f"{desvio_padrao:.2f}")
        st.metric("Coeficiente de Variação", f"{coef_variacao:.2f}%" if not pd.isna(coef_variacao) else "Indefinido")

    # Tabela com cálculos intermediários
    with st.expander("Ver cálculos detalhados"):
        st.dataframe(df[['Classe', 'xi', 'fi', 'faq', 'fi_xi']],
                     use_container_width=True)

        st.markdown(f"""
        ### Fórmulas utilizadas:

        - **Média**: $\\bar{{x}} = \\frac{{\\sum{{f_i \\cdot x_i}}}}{{\\sum{{f_i}}}} = \\frac{{{df['fi_xi'].sum():.2f}}}{{{total_fi}}} = {media:.2f}$

        - **Variância**: $s^2 = \\frac{{\\sum{{f_i \\cdot (x_i - \\bar{{x}})^2}}}}{{\\sum{{f_i}}}} = \\frac{{{df['fi_xi_menos_media_quadrado'].sum():.2f}}}{{{total_fi}}} = {variancia:.2f}$

        - **Desvio Padrão**: $s = \\sqrt{{s^2}} = \\sqrt{{{variancia:.2f}}} = {desvio_padrao:.2f}$

        - **Coeficiente de Variação**: $CV = \\frac{{s}}{{\\bar{{x}}}} \\cdot 100\\% = \\frac{{{desvio_padrao:.2f}}}{{{media:.2f}}} \\cdot 100\\% = {coef_variacao:.2f}\\%$
        """)


def calculate_median(df):
    """Calcula a mediana dos dados agrupados."""
    total_fi = df['fi'].sum()
    posicao_mediana = total_fi / 2

    # Encontrar a classe mediana
    classe_mediana = None
    faq_anterior = 0

    for i, row in df.iterrows():
        if faq_anterior < posicao_mediana and row['faq'] >= posicao_mediana:
            classe_mediana = row
            faq_anterior = df.loc[i - 1, 'faq'] if i > 0 else 0  # Corrigir faq_anterior
            break

    if classe_mediana is None:
        return np.nan

    # Calcular a mediana usando interpolação linear
    limite_inferior = classe_mediana['limite_inferior']
    amplitude = classe_mediana['amplitude']  # Usar amplitude calculada
    fi_classe_mediana = classe_mediana['fi']

    if fi_classe_mediana == 0:
        return np.nan  # Evitar divisão por zero

    mediana = limite_inferior + ((posicao_mediana - faq_anterior) / fi_classe_mediana) * amplitude

    return mediana


def calculate_raw_mode(df):
    """Calcula a(s) moda(s) bruta(s) (ponto médio da(s) classe(s) com maior frequência)."""
    max_fi = df['fi'].max()

    # Caso amodal (todas as frequências iguais)
    if (df['fi'] == max_fi).all():
        st.info("Distribuição amodal (todas as classes têm a mesma frequência). Não há moda bruta definida.")
        return np.nan

    # Encontrar todas as classes com a frequência máxima
    classes_modais = df[df['fi'] == max_fi]

    modas_brutas = []
    for _, row in classes_modais.iterrows():
        moda = (row['limite_inferior'] + row['limite_superior']) / 2
        # Arredondar para duas casas decimais
        moda = round(moda, 2)
        modas_brutas.append(moda)

    return modas_brutas if len(modas_brutas) > 1 else modas_brutas[0]


def calculate_czuber_mode(df):
    """
    Calcula a(s) moda(s) de Czuber usando a fórmula correta.
    Fórmula: Mo = Li + [(d1)/(d1+d2)] * h
    Onde:
    - Li = limite inferior da classe modal
    - d1 = diferença entre a frequência da classe modal e da classe anterior
    - d2 = diferença entre a frequência da classe modal e da classe posterior
    - h = amplitude da classe
    """
    max_fi = df['fi'].max()

    # Caso amodal
    if (df['fi'] == max_fi).all():
        st.info("Distribuição amodal. Usando o ponto médio da distribuição para a moda de Czuber.")
        return round(df['xi'].mean(), 2)

    # Encontrar todas as classes com a frequência máxima
    indices_modais = df.index[df['fi'] == max_fi].tolist()

    modas_czuber = []

    for idx_max in indices_modais:
        fi_modal = df.loc[idx_max, 'fi']

        # Calcular d1 (diferença entre classe modal e anterior)
        if idx_max == 0:  # Primeira classe
            # Para a primeira classe, usamos uma aproximação baseada na tendência das frequências
            if len(df) > 1:
                # Estimativa baseada na tendência das primeiras classes
                fi_anterior = 0  # Assumimos frequência zero antes da primeira classe
            else:
                fi_anterior = 0
        else:
            fi_anterior = df.loc[idx_max - 1, 'fi']

        # Calcular d2 (diferença entre classe modal e posterior)
        if idx_max == len(df) - 1:  # Última classe
            fi_posterior = 0
        else:
            fi_posterior = df.loc[idx_max + 1, 'fi']

        # Calcular as diferenças
        d1 = fi_modal - fi_anterior
        d2 = fi_modal - fi_posterior

        # Aplicar a fórmula de Czuber
        limite_inferior = df.loc[idx_max, 'limite_inferior']
        amplitude = df.loc[idx_max, 'amplitude']

        # Ajustes para casos especiais
        if d1 <= 0 and d2 <= 0:
            # Se ambas as diferenças são não-positivas, usamos o ponto médio
            moda_czuber = (df.loc[idx_max, 'limite_inferior'] + df.loc[idx_max, 'limite_superior']) / 2
        else:
            # Caso normal
            moda_czuber = limite_inferior + (d1 / (d1 + d2)) * amplitude

        # Arredondar para duas casas decimais
        moda_czuber = round(moda_czuber, 2)

        modas_czuber.append(moda_czuber)

    # Remover duplicatas e ordenar
    modas_czuber = sorted(list(set(modas_czuber)))

    return modas_czuber if len(modas_czuber) > 1 else modas_czuber[0]

if __name__ == "__main__":
    main()
