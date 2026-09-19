# Contribuer

## Périmètre

`pyneosol` est un **pilote bas niveau** pour les dongles USB 868 MHz parlant le protocole AT
« PFX ». Il ne conserve aucun état : position estimée, calibration et persistance appartiennent
à la couche appelante. Les propositions qui font remonter de l'état ici seront refusées.

## Mise en route

```bash
uv run ruff check .      # lint
uv run ruff format .     # formatage
uv run pytest            # tests — aucun matériel requis, le dongle est simulé
```

Python ≥ 3.13. Toujours passer par `uv`. Le linter est strict sur `src/` (docstrings et
annotations obligatoires) ; les tests en sont dispensés.

## Conventions

- Commits en [Conventional Commits](https://www.conventionalcommits.org/), en anglais.
  `release-please` s'en sert : seuls `feat:` et `fix:` déclenchent une release.
- Documentation en français, code et docstrings en anglais.
- Le protocole est décrit dans [`docs/SPEC-PROTOCOLE-AT.md`](docs/SPEC-PROTOCOLE-AT.md), où
  chaque affirmation porte un statut ✅ validé / 🟡 partiel / ❓ supposé. **Ne codez jamais sur
  la foi d'un point ❓** : validez-le d'abord sur du matériel réel et mettez la spec à jour.

## Interdits

Ces points sont destructifs pour le matériel de l'utilisateur et ne seront pas fusionnés :

- ⛔ `ATZ` (reset usine : efface la table des canaux, donc tous les appairages) et `AT&F`.
- ⛔ L'action `14` (*unregister*) : destructive et jamais testée.
- ⛔ Le balayage des codes d'action non attribués (`3`, `5`–`10`, `12`, `13`) : risque de
  dérégler les fins de course des moteurs.
- ⛔ `AT$C=` (écriture d'identité) tant qu'elle n'est pas validée : une écriture malformée
  écrase un appairage.

## Sécurité

Aucune clé KeeLoq ni aucun numéro de série réel ne doit entrer dans le dépôt — les valeurs de
`tests/fake.py` et de la documentation sont factices. Pour signaler une faille, voir
[SECURITY.md](SECURITY.md).
