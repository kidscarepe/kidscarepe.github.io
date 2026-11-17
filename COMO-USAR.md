# Blog Kids Care Notícias — como colocar no ar e publicar notícias

Tudo aqui é **gratuito**: o site fica no GitHub Pages e as notícias são publicadas por um painel no navegador (Pages CMS). Não precisa saber programar.

## 1. Colocar o site no ar (uma vez só)

1. Entre no GitHub com a conta **kidscarepe**.
2. Crie um repositório **público** chamado `kidscarepe.github.io` (botão **New** em https://github.com/new).
3. Envie os arquivos desta pasta para o repositório (o Claude pode fazer isso por você).
4. No repositório, vá em **Settings → Pages**. Em *Source*, escolha **GitHub Actions**. Pronto: a cada mudança o site é publicado sozinho.
5. Em 1 a 3 minutos o blog estará em **https://kidscarepe.github.io**.
6. Abra o arquivo `_config.yml` e preencha `url: "https://kidscarepe.github.io"` (isso deixa a prévia das redes sociais correta).

> Quer um endereço próprio, como `noticias.kidscare.com.br`? O GitHub Pages aceita domínio próprio de graça; só o registro do domínio é pago.

## 2. Publicar uma notícia (pelo celular ou computador)

1. Acesse **https://app.pagescms.org** e clique em **Sign in with GitHub**.
2. Escolha o repositório `kidscarepe.github.io`.
3. No menu, clique em **Notícias → Add an entry**.
4. Preencha:
   - **Título**
   - **Resumo**: 1 ou 2 frases. É o texto que aparece na prévia do WhatsApp, Facebook e Instagram.
   - **Data**
   - **Foto de capa**: envie uma imagem (ideal: horizontal, 1200 × 675 px, JPG até 500 KB).
   - **Categoria**: Saúde, Dicas, Eventos ou Novidades.
   - **Texto da notícia**: escreva como num editor de texto. Dá para colocar negrito, listas, links e mais fotos.
5. Clique em **Save**. Em 1 a 3 minutos a notícia aparece no site, já como destaque da página inicial.

Para **editar ou apagar**, abra a notícia na lista e use **Save** ou **Delete**.

## 3. Compartilhar nas redes

Cada notícia tem botões de **WhatsApp, Facebook, X, Telegram e Copiar link**. Para Instagram, copie o link e cole na bio, nos stories (figurinha de link) ou na legenda.

## 4. Trocar logo, cores e redes sociais

- **Redes sociais e nome do site**: no painel, em **Configurações do site**.
- **Logo**: substitua o arquivo `assets/img/marca/logo.png` (PNG com fundo transparente).
- **Cores**: estão no topo de `assets/css/style.css`, na seção "IDENTIDADE VISUAL" (paleta oficial: #FAEADA, #F3BB84, #F37A6C, #A7D9D8, #18BEBC).

## 5. Notícias automáticas

Todo dia às 8h (horário de Recife) um robô gratuito do GitHub (GitHub Actions) lê as fontes de notícias listadas em `_data/fontes.yml` e publica até 3 notícias novas sobre infância, desenvolvimento infantil, autismo, TDAH e saúde das crianças, na categoria **Na mídia**.

- Cada notícia automática traz **título, resumo curto e o link para a matéria original**, com o nome do veículo. O texto completo não é copiado (respeita os direitos dos jornais).
- **Mudar fontes, palavras-chave ou a quantidade por dia:** edite `_data/fontes.yml` direto no GitHub (ícone do lápis).
- **Pausar:** troque `ativo: true` por `ativo: false` no mesmo arquivo.
- **Rodar agora:** no GitHub, aba **Actions → Publicar site e buscar notícias → Run workflow**.
- **Apagar uma notícia automática:** pelo painel (Pages CMS), como qualquer outra.

## 6. Recursos do site

- Destaques em mosaico na página inicial (as 3 notícias mais recentes).
- Busca instantânea (ícone da lupa ou tecla `/`).
- Filtro por categoria, tempo de leitura e barra de progresso de leitura.
- Modo claro e escuro (segue o celular da pessoa ou o botão da lua).

## 7. Notícias de exemplo

O blog vem com 3 notícias de exemplo com artes do padrão da marca. Apague ou edite pelo painel quando publicar as reais.
