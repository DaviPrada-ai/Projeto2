
import os
import sys
import requests
import folium
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configurações da API SPTrans
BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"
TOKEN = os.getenv("SPTRANS_TOKEN")

# Escolha uma linha diferente da utilizada nos slides.
# Exemplo: 8000 (o código identificador será consultado pela API).
LINHA_BUSCA = "875C"

# Cores dos marcadores
COR_PARADA = "blue"
COR_ONIBUS = "red"


def autenticar():
    """Autentica na API Olho Vivo da SPTrans."""
    if not TOKEN:
        raise ValueError(
            "Token não encontrado. Configure SPTRANS_TOKEN no arquivo .env."
        )

    resposta = requests.post(
        f"{BASE_URL}/Login/Autenticar",
        params={"token": TOKEN},
        timeout=30
    )
    resposta.raise_for_status()

    if resposta.json() is not True:
        raise RuntimeError(
            "Falha na autenticação. Verifique seu token da SPTrans."
        )

    print("Autenticação realizada com sucesso.")


def buscar_linha(termo):
    """Busca a linha e retorna seu código identificador."""
    resposta = requests.get(
        f"{BASE_URL}/Linha/Buscar",
        params={"termosBusca": termo},
        timeout=30
    )
    resposta.raise_for_status()

    linhas = resposta.json()

    if not linhas:
        raise RuntimeError(f"Nenhuma linha encontrada para: {termo}")

    print("\nLinhas encontradas:")
    for i, linha in enumerate(linhas):
        print(
            f"{i}: {linha['lt']} | "
            f"{linha['tp']} -> {linha['ts']} | "
            f"Código: {linha['cl']}"
        )

    # Permite selecionar o sentido desejado
    while True:
        try:
            indice = int(input("Digite o índice da linha desejada: "))
            if 0 <= indice < len(linhas):
                return linhas[indice]
        except ValueError:
            pass

        print("Índice inválido. Tente novamente.")


def buscar_paradas(codigo_linha):
    """Busca as paradas atendidas pela linha selecionada."""
    resposta = requests.get(
        f"{BASE_URL}/Parada/BuscarParadasPorLinha",
        params={"codigoLinha": codigo_linha},
        timeout=30
    )
    resposta.raise_for_status()
    return resposta.json()


def buscar_onibus(codigo_linha):
    """Busca as posições dos veículos da linha em tempo real."""
    resposta = requests.get(
        f"{BASE_URL}/Posicao/Linha",
        params={"codigoLinha": codigo_linha},
        timeout=30
    )
    resposta.raise_for_status()
    dados = resposta.json()
    return dados.get("vs", []), dados.get("hr", "Horário não informado")


def criar_mapa(paradas, onibus, horario, linha):
    """Cria um mapa HTML com paradas e ônibus."""
    coordenadas = []

    # Inclui coordenadas válidas das paradas
    for parada in paradas:
        lat = parada.get("py")
        lon = parada.get("px")
        if lat is not None and lon is not None and (lat != 0 or lon != 0):
            coordenadas.append([lat, lon])

    # Inclui coordenadas válidas dos ônibus
    for veiculo in onibus:
        lat = veiculo.get("py")
        lon = veiculo.get("px")
        if lat is not None and lon is not None and (lat != 0 or lon != 0):
            coordenadas.append([lat, lon])

    if not coordenadas:
        raise RuntimeError("Nenhuma coordenada válida foi encontrada.")

    centro = [
        sum(p[0] for p in coordenadas) / len(coordenadas),
        sum(p[1] for p in coordenadas) / len(coordenadas)
    ]

    mapa = folium.Map(location=centro, zoom_start=13)

    # Grupo de marcadores das paradas
    grupo_paradas = folium.FeatureGroup(name="Paradas de ônibus")

    for parada in paradas:
        lat = parada.get("py")
        lon = parada.get("px")

        if lat is None or lon is None or (lat == 0 and lon == 0):
            continue

        nome = parada.get("np", "Parada sem nome")
        endereco = parada.get("ed", "Endereço não informado")
        codigo = parada.get("cp", "N/A")

        folium.Marker(
            location=[lat, lon],
            tooltip=nome,
            popup=(
                f"<b>Parada:</b> {nome}<br>"
                f"<b>Endereço:</b> {endereco}<br>"
                f"<b>Código:</b> {codigo}"
            ),
            icon=folium.Icon(color=COR_PARADA, icon="info-sign")
        ).add_to(grupo_paradas)

    grupo_paradas.add_to(mapa)

    # Grupo de marcadores dos ônibus
    grupo_onibus = folium.FeatureGroup(name="Ônibus em tempo real")

    for veiculo in onibus:
        lat = veiculo.get("py")
        lon = veiculo.get("px")

        if lat is None or lon is None or (lat == 0 and lon == 0):
            continue

        prefixo = veiculo.get("p", "Não informado")
        acessivel = veiculo.get("a", False)
        atualizado = veiculo.get("ta", "Não informado")

        folium.Marker(
            location=[lat, lon],
            tooltip=f"Ônibus {prefixo}",
            popup=(
                f"<b>Prefixo:</b> {prefixo}<br>"
                f"<b>Acessível:</b> {'Sim' if acessivel else 'Não'}<br>"
                f"<b>Última atualização:</b> {atualizado}"
            ),
            icon=folium.Icon(color=COR_ONIBUS, icon="bus", prefix="fa")
        ).add_to(grupo_onibus)

    grupo_onibus.add_to(mapa)

    # Controle para mostrar ou ocultar cada grupo
    folium.LayerControl().add_to(mapa)

    # Ajusta o zoom para mostrar os marcadores
    mapa.fit_bounds(coordenadas)

    # Adiciona informações sobre a consulta
    titulo = (
        f"Monitoramento da linha {linha['lt']} - "
        f"Atualização da API: {horario}"
    )

    folium.Marker(
        location=centro,
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:14px; font-weight:bold; '
                'background:white; padding:5px; border:1px solid gray; '
                'width:250px;">'
                f'{titulo}</div>'
            )
        )
    ).add_to(mapa)

    mapa.save("mapa_onibus.html")
    print("\nMapa salvo em mapa_onibus.html")
    print(f"Total de paradas retornadas: {len(paradas)}")
    print(f"Total de ônibus retornados: {len(onibus)}")


def main():
    try:
        autenticar()

        linha = buscar_linha(LINHA_BUSCA)
        codigo_linha = linha["cl"]

        print(f"\nLinha selecionada: {linha['lt']}")
        print(f"Código identificador: {codigo_linha}")

        paradas = buscar_paradas(codigo_linha)
        onibus, horario = buscar_onibus(codigo_linha)

        criar_mapa(paradas, onibus, horario, linha)

    except requests.RequestException as erro:
        print(f"Erro na comunicação com a API: {erro}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, RuntimeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
