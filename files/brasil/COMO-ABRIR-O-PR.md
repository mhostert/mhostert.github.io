# Como abrir o pull request (2 minutos)

Dois caminhos. Nos dois, o resultado é um branch `brasil-dashboard` com a pasta `brasil/` e um PR contra `master`.

## A) Com os patches (preserva a mensagem de commit)

```bash
git clone https://github.com/mhostert/mhostert.github.io.git
cd mhostert.github.io
git checkout -b brasil-dashboard
git am /caminho/para/0001-Add-Brasil-2018-2026-indicators-dashboard-static-at-.patch
git am /caminho/para/0002-Add-Brasil-em-dados-to-the-main-navigation-optional.patch   # opcional: link no menu
git push -u origin brasil-dashboard
gh pr create --base master --title "Add Brasil 2018–2026 indicators dashboard at /brasil/" --body-file PR-BODY.md
```

## B) Com o zip (sem git am)

```bash
git clone https://github.com/mhostert/mhostert.github.io.git
cd mhostert.github.io
git checkout -b brasil-dashboard
unzip /caminho/para/brasil-site.zip          # cria a pasta brasil/
git add brasil && git commit -m "Add Brasil 2018–2026 indicators dashboard (static) at /brasil/"
git push -u origin brasil-dashboard
gh pr create --base master --title "Add Brasil 2018–2026 indicators dashboard at /brasil/" --body-file PR-BODY.md
```

Sem o `gh`, abra https://github.com/mhostert/mhostert.github.io/compare/master...brasil-dashboard e clique em "Create pull request".

## Depois do merge

A página fica em https://mhostert.com/brasil/ (o Jekyll copia a pasta como está; não há build). Para testar localmente antes: `cd brasil && python3 -m http.server 8000` e abra http://localhost:8000/.
