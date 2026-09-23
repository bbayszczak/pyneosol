# CLAUDE.md

Contexte pour Claude Code sur ce dépôt.

## Le projet

`pyneosol` est un **pilote bas niveau asyncio** pour les dongles USB 868 MHz parlant le
protocole série AT « PFX », compatibles avec les volets roulants Profalux Neosol. Rien d'autre.

Le protocole est intégralement décrit dans [`docs/SPEC-PROTOCOLE-AT.md`](docs/SPEC-PROTOCOLE-AT.md),
reconstitué par rétro-ingénierie et **validé sur un `MAI-DONGLE868-1A` (HW `0`, SW `Rev10`)**.
Chaque affirmation y porte un statut ✅ validé / 🟡 partiel / ❓ supposé : s'y référer avant
d'implémenter quoi que ce soit, et ne jamais coder sur la foi d'un point ❓.

## Structure

```
src/pyneosol/
  protocol.py    encodage et parsing — fonctions pures, aucune I/O
  transport.py   interface Transport (async) + implémentation pyserial-asyncio-fast
  dongle.py      driver asyncio, sérialise le dialogue
  models.py      Action, Channel, DongleInfo
  discovery.py   détection du port par identifiants USB
  exceptions.py
tests/
  fake.py        faux dongle rejouant les réponses réelles
docs/
  images/        photos du matériel utilisées par le README
```

## Commandes

```bash
uv run ruff check .      # lint
uv run ruff format .     # formatage
uv run pytest            # tests, sans matériel
```

Toujours passer par `uv`. Python ≥ 3.13, CI sur 3.13 et 3.14.

Les tests tournent sous `pytest-asyncio` en mode `auto` (`asyncio_mode = "auto"` dans
`pyproject.toml`) : un test qui touche au pilote s'écrit `async def`, sans décorateur.

## Conventions

- **Commits en Conventional Commits**, en anglais. `release-please` s'en sert pour produire le
  CHANGELOG et la version : seuls `feat:` et `fix:` déclenchent une release.
- Documentation en français, code et docstrings en anglais.
- **Logging** : `logging` standard, un `_LOGGER = logging.getLogger(__name__)` par module et
  **aucune configuration** (ni handler, ni niveau, ni format) — l'hôte, typiquement Home
  Assistant, possède les handlers et filtre sur `pyneosol.<module>`. Tout en `DEBUG`, en
  formatage paresseux (`_LOGGER.debug("> %s", command)`), jamais de f-string — les règles ruff
  `LOG` et `G` le vérifient. Les erreurs se
  lèvent, elles ne se loguent pas : loguer *et* lever produit un doublon dans les journaux de
  l'appelant.
- Le linter est strict (docstrings et annotations obligatoires dans `src/`) ; les tests en sont
  dispensés via `per-file-ignores`.
- Les actions GitHub sont **épinglées sur des SHA complets** (un tag comme `@v4` peut être
  redéplacé sur un autre commit). Dependabot les met à jour ; ne jamais revenir à un tag mobile.
- Dépôt public : `CONTRIBUTING.md` et `SECURITY.md` font foi côté contributeurs, les garder
  cohérents avec ce fichier — notamment la liste des interdits ci-dessous.
- `uv.lock` porte la version du paquet : le workflow de release le resynchronise sur la branche
  de la PR de release. Ne pas l'éditer à la main, lancer `uv lock` après tout changement de
  version ou de dépendance.
- La fusion d'une PR de release publie le paquet sur **PyPI** via le *Trusted Publishing*
  (OIDC) : aucun token d'API n'est stocké, l'autorisation vit dans le *publisher* déclaré côté
  PyPI (dépôt `bbayszczak/pyneosol`, workflow `release.yml`). Renommer ce fichier ou le dépôt
  casse la publication tant que le *publisher* n'est pas mis à jour.
- Le workflow de release sépare volontairement `build` et `publish` : `uv build` exécute du
  code tiers (hatchling et ses dépendances) et ne doit jamais tourner dans le job qui porte
  `id-token: write`, sans quoi une dépendance de build compromise pourrait publier sur PyPI.
  Ne pas refusionner ces deux jobs.
- `release-please` tourne sous l'identité d'une **GitHub App** dédiée, jamais sous le
  `GITHUB_TOKEN` : celui-ci ne peut pas ouvrir de PR tant que le réglage « Allow GitHub Actions
  to create and approve pull requests » du dépôt est décoché, et ses écritures ne déclenchent
  aucun workflow — la PR de release n'obtiendrait donc jamais les checks que le ruleset de
  `main` exige et resterait infusionnable. L'App est installée sur le seul dépôt, avec
  `Contents` et `Pull requests` en écriture ; ses identifiants vivent dans les secrets
  `RELEASE_PLEASE_CLIENT_ID` et `RELEASE_PLEASE_PRIVATE_KEY`. Le premier porte le **Client
  ID** de l'App (`Iv23li…`), pas son App ID numérique : l'entrée `app-id` de l'action est
  dépréciée et `client-id` attend l'autre valeur.
- Le commit qui resynchronise `uv.lock` est créé par **l'API GitHub**, jamais par un
  `git commit` dans le *runner* : `main` exige des signatures vérifiées, or un commit fabriqué
  sur le *runner* n'est pas signé et bloque la fusion de la PR de release (« Commits must have
  verified signatures »). GitHub signe les commits passés par son API, et l'appel porte le
  token de l'App, donc la CI se redéclenche sur le nouveau commit.

## Principes de conception

- **Ce pilote ne connaît aucun état.** Le matériel est unidirectionnel : le dongle émet, le
  moteur ne répond jamais. Une commande acceptée signifie qu'une trame est partie, jamais
  qu'un volet a bougé. Toute position estimée, calibration ou persistance appartient à la
  couche appelante — ne pas les faire remonter ici.
- **Dialogue strictement séquentiel** : une commande en vol à la fois, protégée par un
  `asyncio.Lock`, tampon d'entrée vidé avant chaque envoi.
- **Lire jusqu'à la terminaison**, jamais avec un délai fixe. `AT$C?` renvoie 51 lignes,
  `AT$SF` une seule.
- **Cœur asyncio, et rien qui bloque la boucle.** Le pilote existe pour satisfaire la règle
  `async-dependency` du *Integration Quality Scale* de Home Assistant, qui n'admet aucune
  exemption. Aucun `time.sleep`, aucun `threading.Lock`, aucun `serial.Serial` synchrone sur
  le chemin asynchrone ; ce qui bloque vraiment — l'énumération des ports, l'ouverture du
  port — part dans un thread de travail.
- **Attente événementielle, pas de polling.** `Transport.readline()` rend la main dès qu'une
  ligne arrive et le pilote enveloppe la lecture dans un `asyncio.timeout` : c'est la boucle
  qui réveille le driver, jamais un réveil périodique. Le corollaire est que la détection de
  fin de réponse suppose que **la ligne de terminaison se termine par `\r\n`**, ce que la
  spec confirme (§3, ✅ validé).
- `Transport` est l'unique point d'extension : quatre méthodes, trois coroutines et un
  `reset_input()` synchrone puisqu'il ne fait que vider un tampon mémoire. `tests/fake.py`
  l'implémente, d'où une suite de tests sans matériel.
- Deux entrées : `await Dongle.open(...)` rend un dongle ouvert que l'appelant referme —
  c'est la forme qu'utilise Home Assistant —, `async with Dongle.connect(...)` le referme
  tout seul. `connect()` n'existe que pour éviter `async with await Dongle.open()`.

## Pièges du protocole

- Le nom repris dans la terminaison n'est pas toujours celui envoyé : `AT$C?` → `AT$C:OK`,
  mais `AT?` → `AT?:OK`. D'où une détection par forme et non par nom attendu.
- Deux formes de rejet, à ne pas confondre : `KO` nu = commande inconnue du firmware ;
  `<COMMANDE>:KO` = commande connue, forme ou paramètres refusés.
- Dans la table des canaux, un **espace** précède la clé, pas les autres champs.
- Le compteur `sync` est en hexadécimal et s'incrémente à chaque trame émise, `register`
  compris.
- `unregister` (action `14`) ne fait rien seul : il faut ensuite deux descentes en butée
  basse à la télécommande d'origine (spec §10). Le dongle ne touche pas au canal, qui garde
  un `sync` non nul et reste donc « utilisé » : savoir qu'un canal est libre relève de
  l'appelant.
- `sync` non nul = condition **nécessaire, pas suffisante** d'un appairage (spec §6) :
  `used_channels()` rend des candidats, jamais un état. Ne pas chercher à « corriger » cela
  dans le pilote.

## À ne pas faire

- ⛔ **Ne jamais implémenter ni envoyer `ATZ`** (reset usine : efface la table des canaux,
  donc tous les appairages), ni `AT&F`.
- ⛔ **Ne pas balayer les codes d'action non attribués** (`3`, `5`–`10`, `12`, `13`) : le
  risque est de dérégler les fins de course des moteurs.
- ⛔ **Ne pas implémenter `AT$C=`** (écriture d'identité) tant qu'elle n'a pas été validée :
  une écriture malformée écrase un appairage.
- ⛔ **Ne jamais remettre un `sync` à zéro**, même pour marquer un canal désappairé comme
  libre : le compteur KeeLoq doit rester croissant (rejeu, désynchronisation — spec §9).

## Sécurité

La table des canaux contient les **clés KeeLoq** qui commandent les volets. Elles ne doivent
apparaître **ni dans les logs, ni dans les `__repr__`, ni dans les messages d'exception** —
`Channel.__repr__` et `DongleInfo.__repr__` les masquent déjà, garder cette propriété.

Aucune clé, aucun numéro de série réel ne doit entrer dans le dépôt : les valeurs de
`tests/fake.py` et de la documentation sont factices.

Cela vaut aussi pour les **images** de `docs/images/` : toute photo de matériel entre dans le
dépôt numéro de série masqué et métadonnées supprimées (`exiftool -all= --icc_profile:all`),
sans quoi la position GPS de la prise de vue et le numéro de série partent avec le fichier.

Côté logs, `Dongle.execute()` est le point de passage unique du dialogue, **dans les deux
sens** : les réponses traversent `protocol.redact()`, les commandes `protocol.redact_command()`.
Tous deux masquent les clés et les numéros de série. Ne jamais loguer de ligne ni de commande
brute ailleurs, ni un `Channel`/`DongleInfo` autrement que par son `__repr__`.

Le sens commande est nécessaire parce que `execute()` accepte des commandes brutes : `AT$C=`
et `AT$SN=` portent leur secret dans la commande. Ajouter une commande porteuse de secret au
protocole impose d'ajouter son motif à `redact_command()`. La règle vaut aussi pour les
messages d'exception : `execute()` construit `CommandRejectedError`, `UnknownCommandError` et
`ResponseTimeoutError` avec la forme masquée, que l'on retrouve donc dans leur attribut
`.command`. Les tests `test_debug_logging_never_leaks_a_key_or_a_serial_number` et
`test_a_raw_command_carrying_a_key_leaks_neither_to_the_logs_nor_to_the_error` gardent la
propriété.

Le **chemin du port** forme une troisième direction, traitée par `protocol.redact_port()` :
macOS nomme le nœud d'après le numéro de série USB (`/dev/cu.usbmodem0000000012341`), les
liens `by-id` de Linux aussi. Toute suite d'au moins quatre chiffres y est masquée — le seuil
laisse `/dev/ttyACM0` lisible, et masque au passage le port TCP d'une URL `socket://`, effet
de bord assumé. Les points de passage sont `discovery.find_ports()`, `Dongle.open()` et les
messages d'erreur de `transport.py` — ouverture, écriture, lien perdu : tout nouvel endroit
qui logue ou lève un chemin de port doit passer par `redact_port()`.
