## O que é

Painel estático **Brasil 2018–2026: o que melhorou (e o que não)** em `/brasil/`, com quatro abas (O que melhorou · O que piorou · Professores · Pensionistas), seletor de período (2018–2022 / 2022–2026 / série completa) e um popover de fonte: todo número é rastreável até uma linha de CSV em `brasil/data/`, e toda variação até a fórmula que a calculou.

## Como funciona

- `brasil/index.html`: página autocontida (HTML + CSS + JS); sem front matter, o Jekyll copia a pasta como está. Nenhum build, nenhuma dependência externa.
- `brasil/d3.v7.min.js`: d3 7.9.0 vendorizado (276 KB).
- `brasil/data/*.csv` + `datasets.json`: 31 séries e os metadados exibidos no popover (título, descrição, fonte).
- Funciona em modo claro e escuro (`prefers-color-scheme`) e em telas estreitas.

## Fontes

IBGE (PNAD, SIS, Contas Nacionais, Tábuas de Mortalidade, INPC), INPE (PRODES, DETER, Queimadas), Inep (Ideb, Censo Escolar, Censo da Educação Superior, Indicador 17A), Ministério da Saúde (PNI, arboviroses, Vigitel), FBSP (Anuário 2023–2026), Banco Central, Serasa, MapBiomas, SEEG, OCDE/PISA, OMS/Unicef, FAO, MEC/CNTE, Ministério da Previdência/INSS, PF/CGU. Pontos derivados de variações publicadas, e não de tabelas, estão marcados na coluna `estimado` e aparecem com barra mais clara.

## Checklist

- [x] Testado localmente servido por HTTP (todas as 31 séries carregam; abas, período e popover funcionam)
- [x] Sem alterações fora de `brasil/` (o segundo commit, opcional, só adiciona o link "Brasil em dados" ao menu)
