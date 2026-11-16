
import datetime
import requests


def cotar():
    cotacoes = []

    hoje = datetime.date.today()

    for i in range(365):
        dia = hoje - datetime.timedelta(days=i)

        data = dia.strftime('%m-%d-%Y')

        url = (
            'https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/'
            'CotacaoDolarDia(dataCotacao=@dataCotacao)?'
            '@dataCotacao=%27' + data + '%27&$format=json'
        )

        resposta = requests.get(url)
        dados = resposta.json()

        if dados['value']:
            cotacao = dados['value'][0]['cotacaoCompra']
            cotacoes.append(cotacao)
        else:
            cotacoes.append(None)

    return cotacoes




