# pyneosol

Python library for 868 MHz roller shutter USB dongles speaking the `PFX` AT serial protocol. Compatible with Profalux Neosol roller shutters and the `DONGLE868-1A`. Fully local, no box, no cloud.

> Bibliothèque Python pour les dongles USB 868 MHz utilisant le protocole série AT
> « PFX ». **Compatible avec** les volets roulants Profalux Neosol — sans la box
> Calyps'HOME ni le cloud.

---

## ⚠️ Avertissement / Disclaimer

**Ce projet est totalement indépendant et n'est en aucun cas affilié, soutenu, approuvé ou
validé par Profalux, Neosol, Calyps'HOME, Athemium, Avidsen, ou l'une quelconque de leurs
filiales ou marques.**

Les noms *Profalux*, *Neosol* et *Calyps'HOME* sont des marques déposées par leurs
propriétaires respectifs. Ils ne sont utilisés ici que pour **décrire le matériel avec lequel
cette bibliothèque est susceptible de communiquer**, à des fins d'interopérabilité. Aucun code,
aucune ressource et aucune documentation du fabricant n'est redistribué dans ce dépôt.

- 🏷️ **Le nom du projet n'emporte aucune affiliation** — `pyneosol` est un nom d'usage choisi
  pour sa lisibilité. Il ne constitue ni une marque, ni une revendication d'origine, ni une
  autorisation du titulaire de la marque *Neosol*. Cette bibliothèque est un composant tiers
  **compatible avec** ce matériel, et rien d'autre.
- ✋ **Projet non officiel** — développé de manière indépendante, sans aucun lien avec le
  fabricant, qui n'en assure ni le développement ni le support.
- 🔍 **Obtenu par rétro-ingénierie** — le protocole documenté ici a été reconstitué par
  observation du dialogue série avec un dongle acquis légalement, dans le seul but
  d'interopérer avec du matériel dont l'utilisateur est propriétaire.
- 🚫 **Aucune garantie** — ce logiciel est fourni « tel quel », **sans aucune garantie
  d'aucune sorte**, expresse ou implicite, y compris, sans s'y limiter, les garanties de
  qualité marchande, d'adéquation à un usage particulier et d'absence de contrefaçon.
- ⚠️ **Utilisation à vos risques et périls** — l'auteur ne saurait être tenu responsable de
  quelque dommage que ce soit : dysfonctionnement, détérioration de matériel, perte de
  configuration ou d'appairage, perte de données, ou tout dommage direct ou indirect résultant
  de l'utilisation de cette bibliothèque.
- 🔌 **Risque sur le matériel** — certaines commandes du dongle sont **destructives** et
  peuvent effacer ses appairages (voir la section *Commandes dangereuses* des
  [spécifications](docs/SPEC-PROTOCOLE-AT.md)). Sauvegardez la configuration de votre dongle
  avant toute expérimentation.
- 🛠️ **Garantie constructeur** — l'usage de ce logiciel avec votre matériel est susceptible
  d'en annuler la garantie. Vérifiez-le avant de l'utiliser.
- 🤝 **Support limité** — assuré bénévolement, sans engagement de délai ni de résultat.
- 📝 **Licence MIT** — voir [LICENSE](LICENSE).

**En utilisant cette bibliothèque, vous reconnaissez avoir lu et accepté l'ensemble de ces
conditions.**

---

## Matériel

Cette bibliothèque est **compatible avec** le dongle USB 868 MHz distribué pour les volets
roulants Profalux Neosol. Elle n'est ni fournie, ni distribuée, ni approuvée par le fabricant.

| | |
|---|---|
| **Modèle validé** | `DONGLE868-1A` |
| **Identification interne** | `PFX KEELOQ` |
| **Hardware Version** | `0` |
| **Software Version** | `Rev10` |
| **Interface** | USB CDC-ACM (port série virtuel) |
| **Débit** | 115200 bauds |

> ℹ️ **`DONGLE868-1A` est à ce jour la seule référence sur laquelle le protocole a été
> validé.** D'autres références existent (le `MAI-DONGLE868CH-NC` est notamment cité dans les
> catalogues) mais n'ont **pas** été testées. Le comportement sur une autre référence, une
> autre version matérielle ou une autre révision logicielle n'est ni vérifié ni garanti.

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

🚧 **Travaux en cours.** Le protocole est documenté dans
[`docs/SPEC-PROTOCOLE-AT.md`](docs/SPEC-PROTOCOLE-AT.md) ; l'implémentation Python reste à
écrire.

---

## Sécurité

Le dongle stocke les **clés KeeLoq** de vos volets, lisibles en clair via la commande
`AT$C?`. Quiconque les possède peut commander vos volets.

**Ne publiez jamais le contenu réel de votre table de canaux** — ni dans une issue, ni dans un
rapport de bug, ni dans un export de configuration. Masquez systématiquement les clés et les
numéros de série avant tout partage.
