# Lighthouses — Playground del AI Contest de FaROS LaSER

*[English version](README.md)*

Playground público de **FaROS LaSER** (Faros Láser), el juego de estrategia
multijugador del **AI Contest de la Euskal Encounter**
([página del concurso](https://ee34.euskalencounter.org/software-libre/ai-contest.html),
[repo original del concurso](https://github.com/marcan/lighthouses_aicontest)).

Este repositorio es la cara pública del proyecto *Lighthouse AI*: incluye
todo lo necesario para ejecutar el juego y escribir tus propios bots — las
reglas completas, el motor, un conjunto de mapas, dos bots de ejemplo, un
visor en vivo con pygame y un ejecutor de partidas headless con
estadísticas.

![Partida de 4 bots en el mapa island](docs/img/match_island.png)

## El juego

Los jugadores comparten una isla 2D salpicada de faros:

- Los faros irradian energía (`floor(5 - distancia)`) sobre las casillas
  cercanas en cada ronda; los jugadores cosechan la energía de la casilla
  que pisan (se reparte si la comparten).
- Estar sobre un faro otorga su **clave**; la energía se gasta en
  **capturar** (atacar) o **recargar** faros, y los faros propios se pueden
  **conectar** con haces láser (sin cruces; la clave es de un solo uso).
- Tres faros conectados entre sí forman un **triángulo** que puntúa su área
  en casillas cada ronda — la fuente decisiva de puntos.
- Los faros pierden 10 de energía por ronda; al llegar a cero vuelven a ser
  neutros y todas sus conexiones y triángulos se rompen.

Reglas completas y protocolo de comunicación de los bots:
[`aicontest_spec.txt`](aicontest_spec.txt).

## Inicio rápido

Visor en vivo (la única parte con dependencias, pygame-ce):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python ai_contest.py --bots greedy,random
```

Partida headless con estadísticas (solo biblioteca estándar, nada que
instalar):

```bash
python3 match.py --bots greedy,random --map maps/island.txt \
    --games 10 --rounds 200 --rotate
```

Controles del visor: `espacio` pausa · `+/-` velocidad · `B` haces ·
`V` visión · `H` hud · `S` captura · `Q`/`Esc` salir. `--presentation`
activa la vista de retransmisión 1280x720; `--screenshot salida.png` guarda
el fotograma final.

![Modo de retransmisión](docs/img/presentation.png)

## Escribe tu propio bot

El playground ejecuta bots de Python **en proceso**: copia cualquiera de
los ejemplos en `examples/` y hereda de `interface.Bot` (`play(state)`
devuelve una de `move / attack / connect / pass` — ver
`examples/GreedyBot/greedybot.py` para una estrategia codiciosa mínima en
~50 líneas).

El protocolo oficial del concurso — mensajes JSON por stdio, cualquier
lenguaje de programación, 2 s para inicializarse y 100 ms por turno — está
documentado en [`aicontest_spec.txt`](aicontest_spec.txt) (sección
*Protocolo*). Los bots son scripts autocontenidos, así que un bot escrito
para este playground solo necesita una fina capa stdio para competir.

## Estadísticas base

Duelos entre los dos bots de ejemplo, 20 partidas por mapa, 200 rondas,
semilla 42, rotando posiciones (`match.py --bots greedy,random --rotate`;
salida completa en [`stats/`](stats)):

| Mapa | Tamaño | Faros | Victorias GreedyBot | Victorias RandBot | Media Greedy | Media Rand |
|---|---|---|---|---|---|---|
| grid | 19x18 | 25 | 2 | 18 | 336.9 | 913.2 |
| island | 21x18 | 11 | 4 | 16 | 298.1 | 607.9 |
| square | 8x7 | 4 | 3 | 17 | 277.5 | 709.3 |
| square_l | 12x11 | 4 | 17 | 3 | 357.5 | 181.7 |
| square_xl | 20x19 | 4 | 20 | 0 | 379.9 | 24.8 |
| gen_open_m | 16x12 | 6 | 10 | 10 | 330.1 | 342.0 |
| gen_cross | 21x21 | 5 | 14 | 6 | 308.3 | 242.7 |
| gen_donut | 20x20 | 6 | 17 | 3 | 392.4 | 233.6 |
| gen_ring_l | 30x30 | 10 | 11 | 9 | 349.8 | 369.4 |
| **Total** | | | **98** | **82** | | |

Melee de 4 jugadores en island (2x GreedyBot + 2x RandBot, 20 partidas):
los asientos de RandBot ganaron 16 partidas, los de GreedyBot 4. Incluso un
bot puramente aleatorio es peligroso en mapas densos — cosechar rutas y
acampar en un faro no es suficiente. Ejecuta la tuya:

```bash
python3 match.py --bots greedy,greedy,random,random --map maps/island.txt --rotate --games 20
```

![Partida en el mapa generado donut](docs/img/match_donut.png)

## Estructura del proyecto

```
├── aicontest_spec.txt   # Reglas completas + protocolo de bots
├── engine/              # Motor del juego (simulación + vistas pygame)
├── examples/
│   ├── RandBot/         # Bot aleatorio de ejemplo (del concurso original)
│   └── GreedyBot/       # Bot codicioso de ejemplo (cosechar + capturar)
├── maps/                # Mapas clásicos del concurso + variantes generadas
├── ai_contest.py        # Visor en vivo con pygame
├── match.py             # Ejecutor headless de partidas con estadísticas
├── docs/img/            # Capturas de pantalla
├── stats/               # Estadísticas base en bruto
└── tests/               # Tests de humo (motor + ejecutor de partidas)
```

## Tests

Solo biblioteca estándar, no hay nada que instalar:

```bash
python3 -m unittest discover -s tests -v
```

Juegan un duelo corto con semilla en cada mapa, una partida de 4 jugadores,
comprueban que las partidas con semilla son deterministas y que GreedyBot
le gana a RandBot en el mapa island, y ejecutan `match.py` de punta a punta.
La CI los ejecuta en cada push.

## Créditos y licencia

- Diseño del juego, reglas y motor original: **AI Contest de la Euskal
  Encounter**, por marcan. `examples/RandBot` es el ejemplo original de
  marcan (dominio público).
- Este playground: proyecto *Lighthouse AI* — licencia MIT, Jose Lopez
  ([@aifriend](https://github.com/aifriend)). Ver [LICENSE](LICENSE).
