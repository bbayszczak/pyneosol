# pyneosol

Python library for 868 MHz roller shutter USB dongles speaking the `PFX` AT
serial protocol. Compatible with Profalux Neosol roller shutters and the
`MAI-DONGLE868-1A`. Fully local, no box, no cloud.

> Bibliothèque Python pour les dongles USB 868 MHz utilisant le protocole série AT
> « PFX ». **Compatible avec** les volets roulants Profalux Neosol — sans la box
> Calyps'HOME ni le cloud.

---

## ⚠️ Avertissement / Disclaimer

> **Unofficial project.** This library is an independent work. It is not affiliated
> with, endorsed, sponsored or approved by Profalux, Stella Advanced Technology, or
> any of their affiliates. All trademarks belong to their respective owners.

**Ce projet est totalement indépendant et n'est en aucun cas affilié, soutenu, approuvé
ou validé par Profalux, Stella Advanced Technology, ou l'une quelconque de leurs
filiales, marques, sociétés apparentées, sous-traitants ou partenaires.**

*Profalux*, *Stella Advanced Technology*, *Neosol*, *NeosoL* et *Calyps'HOME* sont des
marques de leurs titulaires respectifs. Elles ne sont citées ici que pour **décrire le
matériel avec lequel cette bibliothèque est susceptible de communiquer**, à des fins
d'interopérabilité. Aucun code, aucun binaire, aucun micrologiciel, aucune clé
cryptographique et aucune documentation du fabricant n'est reproduit ni redistribué
dans ce dépôt.

**Nom du projet** — `pyneosol` est un nom d'usage choisi pour sa lisibilité. Il
n'emporte aucune affiliation, ne constitue ni une marque, ni une revendication
d'origine, ni une autorisation du titulaire de la marque *Neosol*. Cette bibliothèque
est un composant tiers **compatible avec** ce matériel, et rien d'autre.

**Méthode** — le protocole documenté ici a été reconstitué par la seule observation du
dialogue série avec un dongle acquis légalement, sur une installation appartenant à
l'auteur. Aucune décompilation de micrologiciel, aucune extraction ni publication de
clé cryptographique constructeur n'a été réalisée. Ce travail relève de l'exception
d'interopérabilité (art. L122-6-1 III et IV du Code de la propriété intellectuelle,
directive 2009/24/CE art. 5 et 6).

**Usage** — cette bibliothèque est destinée au pilotage d'équipements dont vous êtes
propriétaire ou légitime utilisateur, et à eux seuls.

**Absence de garantie** — ce logiciel est fourni « tel quel », sans aucune garantie
d'aucune sorte, expresse ou implicite, y compris, sans s'y limiter, les garanties de
qualité marchande, d'adéquation à un usage particulier et d'absence de contrefaçon.
Dans les limites permises par le droit applicable, l'auteur ne saurait être tenu
responsable d'un quelconque dommage : dysfonctionnement, détérioration de matériel,
perte de configuration ou d'appairage, perte de données, ou tout dommage direct ou
indirect résultant de l'utilisation de cette bibliothèque.

**Risque matériel** — certaines commandes du dongle sont **destructives** et peuvent
effacer ses appairages (voir la section *Commandes dangereuses* des
[spécifications](docs/SPEC-PROTOCOLE-AT.md)). Sauvegardez la configuration de votre
dongle avant toute expérimentation.

**Garantie constructeur** — l'usage de ce logiciel avec votre matériel est susceptible
d'en affecter la garantie. Vérifiez-le avant de l'utiliser.

**Support** — assuré bénévolement, sans engagement de délai ni de résultat.

**Licence** — MIT, voir [LICENSE](LICENSE).

En utilisant cette bibliothèque, vous reconnaissez avoir lu et accepté l'ensemble de
ces conditions.

---

## Démarrage rapide

Avec [`uv`](https://docs.astral.sh/uv/) et le dongle branché :

```bash
git clone https://github.com/bbayszczak/pyneosol
cd pyneosol
uv run demo.py
```

`uv` crée l'environnement et installe les dépendances tout seul. Sans argument, `demo.py`
**n'émet rien** : il identifie le dongle et liste les canaux utilisés — de quoi vérifier en
quelques secondes que votre matériel est reconnu.

---

## Matériel

Cette bibliothèque est **compatible avec** le dongle USB 868 MHz distribué pour les volets
roulants Profalux Neosol. Elle n'est ni fournie, ni distribuée, ni approuvée par le fabricant.

| | |
|---|---|
| **Modèle validé** | `MAI-DONGLE868-1A` |
| **Identification interne** | `PFX KEELOQ` |
| **Hardware Version** | `0` |
| **Software Version** | `Rev10` |
| **Interface** | USB CDC-ACM (port série virtuel) |
| **Débit** | 115200 bauds |

> ℹ️ **`MAI-DONGLE868-1A` est la seule référence sur laquelle le protocole a été validé**, et
> la seule dont dispose l'auteur. L'existence et le comportement d'éventuelles autres
> références ne sont pas connus : rien n'est vérifié ni garanti sur une autre référence, une
> autre version matérielle ou une autre révision logicielle. Les retours sur d'autres modèles
> sont les bienvenus.

### Identifier votre dongle

Avant d'ouvrir une issue, indiquez toujours **la référence de votre dongle ainsi que ses
versions matérielle et logicielle**. Elles s'obtiennent avec la commande AT `AT&V`.

**1. Repérer le port série**

```bash
# Linux
ls -l /dev/ttyACM*

# macOS
ls -1 /dev/cu.usbmodem*
```

**2. Interroger le dongle**

```bash
python3 -c "
import serial, time
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)   # adapter le port
time.sleep(0.4)
ser.write(b'AT&V\r\n'); ser.flush()
time.sleep(1.5)
print(ser.read(ser.in_waiting).decode('utf-8', 'replace'))
ser.close()
"
```

**3. Sortie attendue**

```
PFX KEELOQ

Hardware Version:  0

Software Version: Rev10

S/N: XXXXXXXX

ACTIVE CONFIG :

Return Code Active : 1

Frame Repeat Nb : T0=25,T1=15,T2=70,T3=70

Read Protection Active : 0

AT&V:OK
```

La ligne `PFX KEELOQ` confirme qu'il s'agit bien d'un dongle de cette famille. `Hardware
Version` et `Software Version` sont les deux valeurs à communiquer en cas de problème.

> 🔐 Le numéro de série (`S/N`) identifie votre exemplaire : inutile de le publier.

---

## État du projet

🚧 **Alpha.** Le pilotage fonctionne et le protocole est documenté dans
[`docs/SPEC-PROTOCOLE-AT.md`](docs/SPEC-PROTOCOLE-AT.md). L'API peut encore changer.

---

## Installation

```bash
pip install git+https://github.com/bbayszczak/pyneosol
```

## Utilisation

```python
from pyneosol import Dongle

with Dongle.open() as dongle:  # détection automatique du port
    print(dongle.info().software_version)

    for channel in dongle.used_channels():
        print(channel)  # la clé n'est jamais affichée

    dongle.close_shutter(0)  # descente
    dongle.stop(0)  # arrêt en cours de course
    dongle.favourite(0)  # position favorite
```

Le port peut aussi être imposé : `Dongle.open("/dev/ttyACM0")`.

> ⚠️ **Aucun retour d'état.** Le dongle ne fait qu'émettre. Une commande acceptée signifie
> qu'une trame est partie, jamais qu'un volet a bougé, et aucune position n'est lisible.
> Toute notion d'état ou de position relève de la couche appelante.

### Essayer sans écrire de code

Le dépôt fournit un script de démonstration à sa racine :

```bash
uv run demo.py                           # identification et table des canaux
uv run demo.py --port /dev/ttyACM0       # forcer le port série
uv run demo.py --channel 2 --close       # descente, avec confirmation
uv run demo.py --channel 2 --stop --yes  # stop, sans confirmation
```

Sans argument, il **n'émet rien** : il se contente d'identifier le dongle et de lister les
canaux utilisés. C'est le moyen le plus rapide de vérifier que votre dongle est reconnu.

Les actions (`--open`, `--close`, `--stop`, `--favourite`) doivent être demandées explicitement
et déclenchent une confirmation, puisqu'elles déplacent un volet réel. Les clés ne sont jamais
affichées.

Exemple de sortie (valeurs factices) :

```
Looking for a dongle...
  /dev/ttyACM0  PROFALUX / KEELOQ USB Device

Dongle
  hardware version : 0
  software version : Rev10
  frame repeat     : T0=25,T1=15,T2=70,T3=70
  read protection  : no
  transmit power   : 14

Channels: 50 total, 2 used
  channel  0  serial 000AAAA1  sync 43
  channel  1  serial 000AAAA2  sync 14

Read-only run: nothing was transmitted.
```

## Développement

```bash
uv run ruff check .      # lint
uv run ruff format .     # formatage
uv run pytest            # tests — aucun matériel requis, le dongle est simulé
```

Périmètre, conventions et interdits : [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Sécurité

Le dongle stocke les **clés KeeLoq** de vos volets, lisibles en clair via la commande
`AT$C?`. Quiconque les possède peut commander vos volets.

Pour signaler une faille, utilisez le [signalement privé](SECURITY.md) — jamais une issue
publique.

**Ne publiez jamais le contenu réel de votre table de canaux** — ni dans une issue, ni dans un
rapport de bug, ni dans un export de configuration. Masquez systématiquement les clés et les
numéros de série avant tout partage.
