import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re

st.set_page_config(page_title="Calculadora Estatística", layout="wide")


def main():
    st.title("Calculadora de Estatística para Dados Agrupados")

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

    # Configuração inicial da tabela
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame({
            'Classe': ['8-10', '10-12', '12-14'],
            'fi': ['', '', ''],
            'faq': ['2', '8', '18']
        })

    # Interface para edição da tabela
    with st.expander("Tabela de Dados", expanded=True):
        col1, col2 = st.columns([3, 1])

        with col1:
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
                hide_index=True
            )

            # Atualizar dados na sessão
            st.session_state.data = edited_data

        with col2:
            st.markdown("### Exemplo de entrada:")
            st.markdown("""
            | Classe | fi | faq |
            |--------|----|----|
            | 8-10   | 2  | 2  |
            | 10-12  | 6  | 8  |
            | 12-14  | 10 | 18 |
            """)

            st.markdown("Você pode deixar campos vazios e a aplicação tentará calcular os valores faltantes.")

    # Botão para processar os dados
    if st.button("Calcular Estatísticas"):
        # Verificar se há dados suficientes
        if len(edited_data) < 2 or not any(edited_data['Classe'].astype(str).str.strip() != ''):
            st.error("Por favor, insira pelo menos duas classes com valores.")
            return

        # Processar os dados
        try:
            processed_data = process_data(edited_data)

            # Exibir tabela processada
            st.subheader("Tabela de Frequências Completa")
            st.dataframe(processed_data)

            # Calcular e exibir estatísticas
            display_statistics(processed_data)

            # Exibir gráficos
            # display_charts(processed_data)

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

    # Calcular frequência relativa
    # total_fi = df['fi'].sum()
    # df['fri'] = df['fi'] / total_fi
    # df['fri_percent'] = df['fri'] * 100

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
    media = df['fi_xi'].sum() / total_fi

    # Mediana
    mediana = calculate_median(df)

    # Moda bruta
    moda_bruta = calculate_raw_mode(df)

    # Moda de Czuber
    moda_czuber = calculate_czuber_mode(df)

    # Variância e desvio padrão
    df['fi_xi_menos_media_quadrado'] = df['fi'] * ((df['xi'] - media) ** 2)
    variancia = df['fi_xi_menos_media_quadrado'].sum() / total_fi
    desvio_padrao = np.sqrt(variancia)

    # Coeficiente de variação
    coef_variacao = (desvio_padrao / media) * 100

    # Exibir resultados
    with col1:
        st.metric("Média", f"{media:.4f}")
        st.metric("Mediana", f"{mediana:.4f}")
        st.metric("Moda Bruta", f"{moda_bruta:.4f}")
        st.metric("Moda de Czuber", f"{moda_czuber:.4f}")

    with col2:
        st.metric("Variância", f"{variancia:.4f}")
        st.metric("Desvio Padrão", f"{desvio_padrao:.4f}")
        st.metric("Coeficiente de Variação", f"{coef_variacao:.2f}%")

    # Tabela com cálculos intermediários
    with st.expander("Ver cálculos detalhados"):
        # st.dataframe(df[['Classe', 'xi', 'fi', 'faq', 'fi_xi', 'fri_percent', 'fi_xi_menos_media_quadrado']])
        st.dataframe(df[['Classe', 'xi', 'fi', 'faq', 'fi_xi']])

        st.markdown(f"""
        ### Fórmulas utilizadas:

        - **Média**: $\\bar{{x}} = \\frac{{\\sum{{f_i \\cdot x_i}}}}{{\\sum{{f_i}}}} = \\frac{{{df['fi_xi'].sum():.4f}}}{{{total_fi}}} = {media:.4f}$

        - **Variância**: $s^2 = \\frac{{\\sum{{f_i \\cdot (x_i - \\bar{{x}})^2}}}}{{\\sum{{f_i}}}} = \\frac{{{df['fi_xi_menos_media_quadrado'].sum():.4f}}}{{{total_fi}}} = {variancia:.4f}$

        - **Desvio Padrão**: $s = \\sqrt{{s^2}} = \\sqrt{{{variancia:.4f}}} = {desvio_padrao:.4f}$

        - **Coeficiente de Variação**: $CV = \\frac{{s}}{{\\bar{{x}}}} \\cdot 100\\% = \\frac{{{desvio_padrao:.4f}}}{{{media:.4f}}} \\cdot 100\\% = {coef_variacao:.2f}\\%$
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
            break
        faq_anterior = row['faq']

    if classe_mediana is None:
        return np.nan

    # Calcular a mediana usando interpolação linear
    limite_inferior = classe_mediana['limite_inferior']
    amplitude = classe_mediana['limite_superior'] - classe_mediana['limite_inferior']
    fi_classe_mediana = classe_mediana['fi']

    mediana = limite_inferior + ((posicao_mediana - faq_anterior) / fi_classe_mediana) * amplitude

    return mediana


def calculate_raw_mode(df):
    """Calcula a moda bruta (classe com maior frequência)."""
    if df['fi'].max() == df['fi'].min():
        st.info("Todas as classes têm a mesma frequência. Não há moda bruta definida.")
        return np.nan

    classe_modal = df.loc[df['fi'].idxmax()]
    return (classe_modal['limite_inferior'] + classe_modal['limite_superior']) / 2


def calculate_czuber_mode(df):
    """Calcula a moda de Czuber."""
    # Encontrar a classe com maior frequência
    idx_max = df['fi'].idxmax()

    # Se todas as classes têm a mesma frequência
    if df['fi'].max() == df['fi'].min():
        st.info("Todas as classes têm a mesma frequência. Usando o ponto médio da distribuição para a moda de Czuber.")
        return df['xi'].mean()

    # Se for a primeira ou última classe, usar a moda bruta
    if idx_max == 0 or idx_max == len(df) - 1:
        st.info("A classe modal é a primeira ou última classe. Usando a moda bruta para a moda de Czuber.")
        return calculate_raw_mode(df)

    # Obter dados da classe modal e adjacentes
    d1 = df.loc[idx_max, 'fi'] - df.loc[idx_max - 1, 'fi']
    d2 = df.loc[idx_max, 'fi'] - df.loc[idx_max + 1, 'fi']

    # Se d1 ou d2 for negativo ou zero, usar a moda bruta
    if d1 <= 0 or d2 <= 0:
        st.info("Não é possível calcular a moda de Czuber com as diferenças atuais. Usando a moda bruta.")
        return calculate_raw_mode(df)

    # Calcular a moda de Czuber
    limite_inferior = df.loc[idx_max, 'limite_inferior']
    amplitude = df.loc[idx_max, 'limite_superior'] - df.loc[idx_max, 'limite_inferior']

    moda_czuber = limite_inferior + (d1 / (d1 + d2)) * amplitude

    return moda_czuber


def display_charts(df):
    """Exibe gráficos para visualização dos dados."""
    st.subheader("Visualização dos Dados")

    col1, col2 = st.columns(2)

    with col1:
        # Histograma
        fig, ax = plt.subplots(figsize=(10, 6))

        # Criar rótulos para o eixo x
        labels = [f"{row['limite_inferior']}-{row['limite_superior']}" for _, row in df.iterrows()]

        ax.bar(labels, df['fi'], color='skyblue', edgecolor='navy')
        ax.set_title('Histograma de Frequências')
        ax.set_xlabel('Classes')
        ax.set_ylabel('Frequência (fi)')
        ax.tick_params(axis='x', rotation=45)

        # Adicionar valores sobre as barras
        for i, v in enumerate(df['fi']):
            ax.text(i, v + 0.1, str(int(v) if v.is_integer() else f"{v:.1f}"),
                    ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        st.pyplot(fig)

    with col2:
        # Polígono de frequências acumuladas
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(labels, df['faq'], marker='o', linestyle='-', color='green', linewidth=2)
        ax.set_title('Polígono de Frequências Acumuladas')
        ax.set_xlabel('Classes')
        ax.set_ylabel('Frequência Acumulada (faq)')
        ax.tick_params(axis='x', rotation=45)

        # Adicionar valores sobre os pontos
        for i, v in enumerate(df['faq']):
            ax.text(i, v + 0.5, str(int(v) if v.is_integer() else f"{v:.1f}"),
                    ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        st.pyplot(fig)

    # Adicionar gráfico de pizza para frequências relativas
    st.subheader("Distribuição de Frequências")
    fig, ax = plt.subplots(figsize=(10, 6))

    # Criar rótulos para o gráfico de pizza
    pie_labels = [f"{row['limite_inferior']}-{row['limite_superior']} ({row['fri_percent']:.1f}%)" for _, row in
                  df.iterrows()]

    ax.pie(df['fi'], labels=pie_labels, autopct='%1.1f%%', startangle=90, shadow=True)
    ax.axis('equal')
    ax.set_title('Distribuição Percentual das Classes')

    plt.tight_layout()
    st.pyplot(fig)


if __name__ == "__main__":
    main()
