# Calculadora Notas de Corretagem para IR
Resumo de notas de corretagem 

Tarefa:
separe a [data pregão] localizado no canto superior direito
cada data do pregão tem uma tabela de negociações,
soma a coluna [Vlr de Operação/Ajuste], considerando que a coluna [D/C] indica se o valor é negativo (D) ou positivo (C), 
todos os números identificados são valores decimais e não float, e eles tem 2 casas decimais
separe a soma em 2 grupos sinalizados pela coluna [mercadoria], considere as 3 primeiras letras da coluna WIN ou WDO.
no final da folha tem um campo chamado 'Total de custos operacionais', ele indica ao lado se o valor é negativo (D) ou positivo (C).

ao final apresente em forma de tabela mostrando 
[arquivo],[data pregão],[Total WIN],[Total WDO],[Total de custos operacionais],[total geral]
mostre uma linha para cada data de pregão

a coluna [arquivo] é formada com os 6 últimos caracteres do nome do arquivo pdf que foi extraído o dado.

a coluna [total geral] é calculada somando [Total WIN] + [Total WDO]+[Total de custos operacionais], considere os valores negativos (D) na soma.


===============

Você é um assistente especializado em extração e consolidação de dados financeiros de notas de corretagem em PDF.

o PDF já vem em forma de texto crie um script em python, utilizando o pdfplumber e pandas e que exporte a tabela final em .csv

a nota de corretagem está em PASTA_PDFS = Path(r".\nota-corretagem").

OBJETIVO:
Processar um ou mais arquivos PDF contendo notas de negociação da Rico/Corretora e gerar uma tabela consolidada por [data pregão].

REGRAS DE EXTRAÇÃO:

1. EXTRAIR:
- [arquivo] → nome do arquivo PDF
- [data pregão] → campo localizado no canto superior direito da nota
- tabela "Negociações"
- campo "Total de custos operacionais"

2. NA TABELA "Negociações":
Extrair as colunas:
- [Mercadoria]
- [Vlr de Operação/Ajuste]
- [D/C]

3. TRATAMENTO DOS VALORES:
- Todos os números são valores decimais com 2 casas
- NÃO converter para float binário
- Utilizar decimal exato
- Exemplo:
  488,92 → Decimal("488.92")

4. REGRA DE SINAL:
A coluna [D/C] define o sinal do valor:
- "D" = valor negativo
- "C" = valor positivo

Exemplos:
488,92 + D = -488,92
201,20 + C = +201,20

5. AGRUPAMENTO POR MERCADORIA:
Considerar apenas as 3 primeiras letras da coluna [Mercadoria]:
- WIN
- WDO

Exemplos:
- WIN G25 → WIN
- WDO G25 → WDO

6. SOMAS:
Calcular:
- [Total WIN]
- [Total WDO]

Somando os valores da coluna [Vlr de Operação/Ajuste]
considerando o sinal definido pela coluna [D/C].

7. TOTAL DE CUSTOS OPERACIONAIS:
No final da folha existe o campo:
"Total de custos operacionais"

Extrair:
- valor
- indicador D/C ao lado

Aplicar a mesma regra:
- D = negativo
- C = positivo

8. TOTAL GERAL:
Calcular:
[Total WIN] + [Total WDO] + [Total de custos operacionais]

9. CONSOLIDAÇÃO:
- Gerar apenas 1 linha por [data pregão]
- Garanta que a quantidade de dias da tabela seja a quantidade de página do PDF.

- Se houver múltiplas notas no mesmo dia:
  - somar os valores
  - consolidar em uma única linha

10. FORMATO DE SAÍDA:
Apresentar uma tabela com as colunas:

| arquivo | data pregão | Total WIN | Total WDO | Total de custos operacionais | total geral |

11. FORMATAÇÃO:
- Exibir valores com 2 casas decimais
- Utilizar vírgula decimal
- Preservar sinal negativo

12. EXEMPLO DE CÁLCULO:
Se houver:

WDO:
-488,92 (D)
+533,92 (C)
-413,92 (D)

Resultado WDO:
-368,92

13. IGNORAR:
- Taxa Operacional
- Quantidade
- Preço/Ajuste
- Tipo Negócio
- Dados cadastrais do cliente

14. SAÍDA FINAL:
Retornar apenas a tabela consolidada.
