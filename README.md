# Aventura em texto

> **Status:** Em andamento
> **Engine / Biblioteca:** Nenhuma (somente console)
> **Linguagem:** Python 3.11+ (somente biblioteca padrão)

## Proposta

Um RPG de aventura em texto, rodando só no console, inspirado em um bot de RPG para Discord que eu fiz antes. O mundo é um grafo de salas divididas em duas áreas. O jogador explora, pega itens, abre uma porta trancada, enfrenta monstros em combate simples por turnos, ganha ouro e XP, compra poções na loja, coleta madeira e minério para fabricar equipamentos (arma, escudo e armadura, como no bot antigo) e enfrenta um chefe em cada área. O jogo termina com a derrota do jogador ou com a vitória sobre o mula sem cabeça, o chefe final. Vários personagens nomeados podem ser salvos, e só um jogador joga por vez.

O conteúdo do jogo (salas, monstros, itens, textos) está em português do Brasil; código, comentários e documentação estão em inglês.

"Concluído" significa: uma partida completa, da primeira sala até o chefe final, funciona; o progresso pode ser salvo e carregado; e a lógica central está coberta por testes. Isso já é verdade hoje.

## Habilidades que pretendo praticar

- **Entrada e saída básicas:** um laço de comandos que lê a entrada e imprime resultados, separado da lógica do jogo.
- **Estrutura de código:** engine pura, parser e arquivos de dados, em vez de um script único e grande.
- **Lógica de ramificação:** salas como grafo, saídas trancadas, tratamento de comandos e resultados de combate.
- **Estado do jogo:** um objeto `GameState` explícito que pode ser salvo e restaurado em JSON.

## Escopo

- **Essencial (feito):**
  - Parser de comandos e REPL.
  - Grafo de salas carregado de JSON e validado por testes.
  - Inventário e um quebra-cabeça de chave e porta.
  - Combate simples por turnos com gerador aleatório semeável.
  - Loja para comprar e usar itens de cura.
  - Salvar e carregar personagens nomeados em JSON.
- **Extras (feitos):** duas áreas, um chefe em cada uma, XP e níveis, slots de equipamento com bônus de atributos, crafting básico (coletar madeira e cobre, fabricar um conjunto de madeira e um de cobre), e um simulador de balanceamento (`python -m adventure.simulate`).
- **Extras (não feitos):** `undo`.
- **Fora do escopo:** gráficos, som, rede/multiplayer, interpretação de linguagem natural, cooldowns em tempo real, monstros que reaparecem.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
python -m adventure
```

O jogo pede o nome do personagem. Um nome novo começa um jogo novo; um nome já conhecido carrega o save desse personagem de `saves/`.

### Comandos

| Comando | O que faz |
|---|---|
| `olhar` | Descreve a sala: itens, loja, perigo e saídas |
| `ir <direção>` (ou `n`, `s`, `l`, `o`) | Anda para norte, sul, leste ou oeste |
| `pegar <item>` / `largar <item>` | Pega ou larga um item |
| `usar <item>` | Usa uma chave em uma porta, ou um item de cura |
| `inventario` / `perfil` | Mostra seus itens / nível, vida, atributos, equipamento e ouro |
| `cortar [vezes]` / `minerar [vezes]` | Coleta madeira (floresta) ou cobre (acampamento no deserto); cada ponto tem usos limitados |
| `receitas` / `fabricar <item>` | Lista as receitas / fabrica um equipamento (é equipado na hora se for uma melhoria) |
| `equipar <item>` | Veste um item do inventário (o antigo volta para o inventário) |
| `loja` / `comprar <item> [n]` | Mostra a loja / compra itens |
| `atacar` / `fugir` | Luta / tenta fugir |
| `descansar` | Recupera vida (somente em locais seguros) |
| `salvar` | Salva o personagem (`sair` não salva) |

Você pode digitar só parte do nome de um item, e os acentos são opcionais.

### Testes, linter e balanceamento

```bash
python -m pytest
python -m ruff check .
python -m adventure.simulate 500      # taxa de vitória da partida-guia, por política
```

O simulador reproduz `data/walkthrough.txt` (um spoiler: a rota de vitória) com aleatoriedade real, então mostra o quão difícil o jogo está depois de mudar números em `data/world.json`. Ele compara políticas de uso de poção e uma partida sem crafting (`--sem-equipamento` aplica isso a todas as partidas). Exemplo:

```
Nunca bebe poção: 37.2% de vitórias (372/1000)
Bebe poção abaixo de 35% da vida: 95.7% de vitórias (957/1000)
Bebe poção abaixo de 35% da vida, sem equipamento: 4.4% de vitórias (44/1000)
```

Ou seja, poções e equipamentos fabricados importam: o equipamento inicial sozinho não basta para o deserto.

## Screenshots / GIFs

<Adicionar uma gravação do terminal quando quiser.>

## O que aprendi

<Preencher após terminar: o que foi difícil, o que faria diferente, o que vou reaproveitar no futuro.>
