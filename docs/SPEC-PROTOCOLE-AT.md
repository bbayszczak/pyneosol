# Protocole AT du dongle Neosol 868 MHz — spécifications

Document de référence décrivant le protocole série du dongle USB `MAI-DONGLE868-1A`, destiné à
servir de base à l'implémentation de `pyneosol`.

> ⚠️ Protocole reconstitué par **rétro-ingénierie**, par observation du dialogue série avec un
> dongle acquis légalement. Voir l'avertissement complet dans le [README](../README.md). Ce
> document ne reproduit aucun code ni aucune documentation du fabricant.

## Sommaire

- [1. Statut des observations](#1-statut-des-observations)
- [2. Transport](#2-transport)
- [3. Format des échanges](#3-format-des-échanges)
- [4. Jeu de commandes](#4-jeu-de-commandes)
- [5. `AT&V` — identification](#5-atv--identification)
- [6. `AT$C?` — table des canaux](#6-atc--table-des-canaux)
- [7. `AT$C=` — écriture d'identité](#7-atc--écriture-didentité)
- [8. `AT$SF=` — émission d'une trame](#8-atsf--émission-dune-trame)
- [9. Compteur de synchronisation](#9-compteur-de-synchronisation)
- [10. Appairage d'un volet](#10-appairage-dun-volet)
- [11. Positionnement intermédiaire](#11-positionnement-intermédiaire)
- [12. Absence de réception radio](#12-absence-de-réception-radio)
- [13. Commandes dangereuses](#13-commandes-dangereuses)
- [14. Séquence d'initialisation de la box](#14-séquence-dinitialisation-de-la-box)
- [15. Points non validés](#15-points-non-validés)
- [16. Notes d'implémentation](#16-notes-dimplémentation)
- [17. Références](#17-références)

---

## 1. Statut des observations

Chaque élément de ce document porte l'une des mentions suivantes :

| Mention | Signification |
|---|---|
| ✅ **Validé** | Observé et reproduit sur un dongle `MAI-DONGLE868-1A` (HW `0`, SW `Rev10`) |
| 🟡 **Partiel** | Comportement observé mais périmètre ou paramètres incomplets |
| ❓ **Supposé** | Déduit sans vérification directe — à confirmer |

Toutes les valeurs de `serial` et de `key` figurant dans ce document sont **factices**. Les
valeurs réelles sont propres à chaque dongle et ne doivent jamais être publiées.

---

## 2. Transport

✅ **Validé**

Le dongle se présente comme un périphérique **USB CDC-ACM** (port série virtuel). Aucun pilote
spécifique n'est nécessaire sous Linux ni macOS.

| Paramètre | Valeur |
|---|---|
| Débit | `115200` bauds |
| Format | 8N1 |
| Contrôle de flux | aucun (ni RTS/CTS, ni DSR/DTR) |
| Port (Linux) | `/dev/ttyACM0` |
| Port (macOS) | `/dev/cu.usbmodem*` |

Sur une box Athemium, le périphérique est exposé via le lien symbolique
`/dev/atm_profalux_keeloq`.

> Le débit `115200` est celui sur lequel le dongle répond. S'agissant d'un périphérique
> CDC-ACM, le débit est probablement ignoré par le firmware, mais rien ne le garantit.

Un délai d'environ **400 ms** après l'ouverture du port est recommandé avant d'émettre la
première commande.

### Identification USB

✅ **Validé** — le périphérique expose des métadonnées qui permettent de le détecter
automatiquement, sans demander le port à l'utilisateur :

| Champ | Valeur |
|---|---|
| Vendor ID | `0x10C4` (Silicon Laboratories) |
| Product ID | `0x0003` |
| Fabricant | `PROFALUX` |
| Produit | `KEELOQ USB Device` |
| Numéro de série USB | propre à chaque exemplaire |

⚠️ Le VID `0x10C4` appartient à Silicon Labs et équipe quantité de périphériques série sans
rapport. Il ne suffit donc pas à lui seul : la confirmation doit passer par la réponse
`PFX KEELOQ` à `AT&V` (§5).

---

## 3. Format des échanges

✅ **Validé**

**Requête** — la commande est suivie de `\r\n` :

```
AT&V\r\n
```

**Réponse** — le dongle émet des lignes séparées par `\r\n`, **avec une ligne vide entre
chaque ligne utile** (autrement dit chaque ligne est encadrée de `\r\n`) :

```
\r\nPFX KEELOQ\r\n\r\nHardware Version:  0\r\n\r\n...\r\nAT&V:OK\r\n
```

**Terminaison** — la réponse se termine systématiquement par une ligne de statut construite
sur le nom de la commande :

| Terminaison | Sens |
|---|---|
| `<COMMANDE>:OK` | succès — ex. `AT&V:OK`, `AT$SF:OK`, `AT?:OK` |
| `<COMMANDE>:KO` | commande **reconnue**, mais forme ou paramètres refusés |
| `KO` *(sans préfixe)* | commande **inconnue** du firmware |

C'est le marqueur à utiliser pour détecter la fin d'une réponse, plutôt qu'un délai fixe.

✅ **Validé** — la distinction entre les deux formes de rejet est exploitable : elle permet de
savoir si un firmware *connaît* une commande, indépendamment du fait qu'il accepte ce qu'on lui
passe. Utile pour sonder les différences entre révisions sans rien modifier.

```
ATI       →  KO           commande inconnue
AT&V0     →  AT&V:KO      AT&V reconnue, variante refusée
AT$CP=?   →  AT$CP:KO     AT$CP reconnue, forme test non supportée
AT        →  AT:OK        ping
```

> ℹ️ Le champ `Return Code Active : 1` de `AT&V` laisse penser que l'émission de ces
> terminaisons est configurable, et qu'un dongle configuré à `0` n'en produirait pas. ❓

---

## 4. Jeu de commandes

✅ **Validé** — la commande `AT?` retourne la liste des commandes supportées par le firmware :

```
AT
A/
AT?
ATQ<n>
ATZ
AT&V
AT$C=<channel>,<serial number>,<sync>,<key>
AT$P=<code>,<value>
AT$SF=<channel>,<code>
AT$SN=<serialNb>
AT$CW=<mode>
AT$TR=<T0>,<T1>,<T2>,<T3>
AT$CP=<power>
```

| Commande | Rôle | Statut |
|---|---|---|
| `AT` | ping | ✅ |
| `A/` | répéter la dernière commande (convention Hayes) | ❓ |
| `AT?` | lister les commandes supportées | ✅ |
| `ATQ<n>` | *quiet mode* | ❓ |
| `ATZ` | **reset usine — destructif** | ⛔ non testé volontairement |
| `AT&V` | identification et configuration active | ✅ |
| `AT$C=` | écrire l'identité d'un canal | ❓ |
| `AT$C?` | lire la table des canaux | ✅ |
| `AT$P=` | paramètre indéterminé | ❓ |
| `AT$SF=` | émettre une trame radio | ✅ |
| `AT$SN=` | définir un numéro de série | ❓ |
| `AT$CW=` | mode indéterminé — ⚠️ voir la mise en garde en [§12](#12-absence-de-réception-radio) | ❓ |
| `AT$TR=` | temporisations d'émission | 🟡 |
| `AT$CP=` | puissance d'émission — lisible, vaut `14` sur le matériel testé | 🟡 |

### Exhaustivité

✅ **Validé** — `AT?` liste la **totalité** des commandes reconnues. Un sondage des commandes
Hayes usuelles non déclarées (`ATI`, `ATI0`–`ATI9`, `AT+GMI`, `AT+GMM`, `AT+GMR`, `AT+GSN`)
renvoie systématiquement `KO` nu : le firmware ne les connaît pas. Aucune information de
version ou de build supplémentaire n'est donc accessible.

Aucune **forme test** (`=?`) n'est implémentée non plus : `AT$CP=?`, `AT$TR=?`, `AT$SN=?`,
`AT$CW=?` et `AT$P=?` répondent toutes `<COMMANDE>:KO`.

> Sondage effectué avec relevé d'empreinte de la table des canaux et de `AT$CP?` avant et
> après : **aucune modification**. `ATZ`, `AT&F` et toute forme de `AT$C=` avaient été exclues
> du balayage (§13).

⚠️ **Toutes les commandes n'acceptent pas de forme interrogative.** Seules **`AT$C?`** et
**`AT$CP?`** retournent une valeur ; `AT$TR?`, `AT$SN?`, `AT$CW?` et `AT$P?` répondent `:KO` et
n'existent donc qu'en écriture. Détail des réponses en [§12](#12-absence-de-réception-radio).

---

## 5. `AT&V` — identification

✅ **Validé**

```
AT&V\r\n
```

Réponse :

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

| Champ | Description |
|---|---|
| `PFX KEELOQ` | marqueur de famille — sert à confirmer qu'on parle bien à ce type de dongle |
| `Hardware Version` | version matérielle |
| `Software Version` | révision du firmware (ex. `Rev10`) |
| `S/N` | numéro de série de l'exemplaire (8 chiffres) |
| `Return Code Active` | émission des terminaisons `:OK` / `:KO` |
| `Frame Repeat Nb` | temporisations `T0..T3`, voir `AT$TR` |
| `Read Protection Active` | `0` = table des canaux lisible via `AT$C?` |

> ⚠️ Si `Read Protection Active` vaut `1`, la lecture des clés par `AT$C?` est probablement
> refusée. Non vérifié. ❓

---

## 6. `AT$C?` — table des canaux

✅ **Validé**

Retourne les **50 canaux** (indices `0` à `49`) que contient le dongle, un par ligne.

```
AT$C?\r\n
```

Réponse (valeurs factices) :

```
0,000AAAA1,0029, 00112233445566AA

1,000AAAA2,0009, 00112233445566BB

2,000AAAA3,0000, 00112233445566CC

...

49,000AAAD2,0000, 00112233445566DD
```

### Format d'une ligne

```
<channel>,<serial>,<sync>, <key>
```

| Champ | Format | Description |
|---|---|---|
| `channel` | décimal, `0`–`49` | index du canal, utilisé par `AT$SF=` |
| `serial` | 8 chiffres hexadécimaux | numéro de série de l'identité virtuelle |
| `sync` | 4 chiffres hexadécimaux | compteur de synchronisation KeeLoq |
| `key` | 16 chiffres hexadécimaux | **clé KeeLoq 64 bits** |

> ⚠️ **Attention au parsing** : un **espace** sépare la virgule de la clé, alors que les
> autres champs n'en comportent pas. Une expression régulière tolérante est recommandée :
> `^\s*(\d+),([0-9A-Fa-f]+),([0-9A-Fa-f]+),\s*([0-9A-Fa-f]+)`

### Identités préprovisionnées

✅ **Validé** — le dongle est livré avec **50 identités déjà provisionnées en usine** :

- les `serial` sont **séquentiels** sur toute la table (`N`, `N+1`, … `N+49`) ;
- chaque canal possède une **clé distincte**, apparemment aléatoire ;
- un canal jamais utilisé a un `sync` à `0000`.

L'appairage ne génère donc **aucune clé** : il fait accepter par le moteur l'une des identités
déjà présentes dans le dongle.

> Cela tranche une question restée ouverte dans les travaux antérieurs (cf. §17) : le
> mécanisme n'est pas un apprentissage à clé arbitraire de type *Chamberlain Self-Learn*, mais
> bien un stock d'identités préprovisionnées.

### Détecter les canaux en service

Un canal dont le `sync` est différent de `0000` a déjà émis, et correspond donc en principe à
un volet appairé. C'est l'heuristique à utiliser pour repérer les canaux occupés — sachant
qu'un `sync` non nul prouve seulement qu'une trame a été émise, pas qu'un moteur a répondu.

---

## 7. `AT$C=` — écriture d'identité

❓ **Supposé — non testé**

```
AT$C=<channel>,<serial>,<sync>,<key>
```

Écrit une identité complète dans un canal. Usages attendus :

- **sauvegarde / restauration** de la table d'un dongle ;
- **recopie** d'identités vers un dongle de remplacement ;
- **resynchronisation** d'un compteur désaligné.

> ⛔ Écrire sur un canal en service écrase l'identité qui fonctionne et fait perdre
> l'appairage correspondant. Voir §13.

---

## 8. `AT$SF=` — émission d'une trame

✅ **Validé**

```
AT$SF=<channel>,<code>
```

Émet une trame radio depuis l'identité du canal indiqué. Réponse : `AT$SF:OK`.

### Codes d'action

| Code | Action | Statut |
|---:|---|---|
| `0` | ouvrir / monter | ✅ validé |
| `1` | fermer / descendre | ✅ validé |
| `2` | stop | ✅ validé |
| `4` | appel de la position favorite | ✅ validé |
| `11` | enregistrer — *register* | ✅ validé (voir §10) |
| `14` | désenregistrer — *unregister* | ❓ non testé |

### Sémantique des mouvements

Les moteurs fonctionnent en **appui bref** : une commande `0` ou `1` lance le moteur, qui
poursuit sa course jusqu'à la butée ou jusqu'à réception d'un `2` (stop). Il n'existe pas de
commande de maintien.

### Position favorite

✅ **Validé** — le code `4` demande au moteur de rejoindre sa **position favorite**, une
position mémorisée **dans le moteur** et non dans le dongle.

La vérification s'est faite en deux temps, le premier essai ayant été non concluant :

1. **Appel alors qu'un favori réglé en butée haute était enregistré** → le volet est monté
   jusqu'en haut. Résultat ambigu : compatible aussi bien avec un appel de favori qu'avec une
   simple commande de montée.
2. **Nouveau favori enregistré à une position intermédiaire**, volet placé ailleurs, puis
   nouvel appel → **le volet a rejoint cette position et s'y est arrêté**. Aucune commande de
   mouvement ordinaire ne provoque un arrêt en cours de course : l'attribution est confirmée.

> 💡 Un favori positionné sur une butée rend le test indiscernable d'une commande de
> mouvement. Toute vérification doit donc porter sur une position **franchement
> intermédiaire**.

#### Enregistrer la position favorite

✅ **Validé** — **l'enregistrement ne passe pas par le dongle**, il s'effectue sur la
télécommande d'origine :

1. amener le volet à la position souhaitée ;
2. appuyer **simultanément** sur **montée** et **descente**, et maintenir environ
   **5 secondes** ;
3. le moteur confirme par un **bref aller-retour de quelques millimètres**.

La position est alors mémorisée dans le moteur, et rappelable par `AT$SF=<canal>,4`.

**Aucun code `AT$SF` ne permet cet enregistrement**, et il n'en existe vraisemblablement pas.
L'analyse du greffon de la box (cf. §17) établit qu'il n'émet que **six** actions —
`open`, `close`, `stop`, `fav_pos1`, `register`, `unregister` — ce que corroborent ses propres
traces internes (« *Motorisation commands open/stop/close/fav_pos1 will be repeated N times* »)
et son gestionnaire d'action, qui ne traite que ces quatre mouvements. **La box elle-même ne
sait donc pas enregistrer un favori par radio.**

Les entrées `FAV_SET_1`, `FAV_SET_2` et `FAV_CALL_2` visibles dans le code de l'interface web
appartiennent à sa liste d'actions **masquées** : ce code est commun à tous les types
d'équipements gérés par la box, et ces actions ne s'appliquent pas à ce driver. Elles ne
signalent donc pas un code restant à découvrir — plutôt l'inverse.

> ⛔ Chercher un `FAV_SET` en balayant les codes non attribués reviendrait à traquer une
> fonction qui n'existe probablement pas, au prix d'un risque réel de dérèglement des fins de
> course (§15). L'enregistrement à la télécommande décrit ci-dessus rend cette recherche
> inutile.

Le driver de la box connaît **deux** positions favorites (`FAV_CALL_1` et `FAV_CALL_2`). Seul
l'appel de la première dispose à ce jour d'un code identifié.

### Absence de retour d'état

⚠️ `AT$SF:OK` confirme uniquement que **le dongle a accepté et émis** la trame. Le dongle
**ne renvoie aucun acquittement du moteur** : rien ne permet de savoir si un volet a
effectivement bougé, ni quelle est sa position réelle.

Le dongle ne remonte pas davantage les trames émises par les télécommandes — il n'a aucune
capacité de réception exploitable, voir [§12](#12-absence-de-réception-radio).

Toute notion de position doit donc être **estimée** côté logiciel (voir §11).

---

## 9. Compteur de synchronisation

✅ **Validé**

Le champ `sync` de chaque canal **s'incrémente de 1 à chaque trame émise** sur ce canal, quel
que soit le code d'action — y compris pour un `register` (code `11`).

Observations :

| Séquence émise | Évolution du `sync` |
|---|---|
| 1 descente | `42` → `43` |
| 1 stop + 1 descente | `9` → `11` |
| 1 montée + 1 stop | `11` → `13` |
| 1 register | `0` → `1` |

Les canaux non sollicités restent **strictement inchangés**, ce qui permet de vérifier après
coup qu'une opération n'a produit aucun effet de bord.

> 💡 Comparer la table avant et après une opération est le moyen le plus fiable de contrôler
> ce qui a réellement été émis. À utiliser systématiquement dans les tests.

---

## 10. Appairage d'un volet

✅ **Validé**

L'appairage associe un canal du dongle à un moteur. Il combine **une trame radio émise par le
dongle** et **une séquence de mouvements exécutée depuis une télécommande déjà appairée au
moteur cible**.

### Procédure

1. Choisir un **canal libre** (`sync` à `0000`).
2. Placer le volet cible **à mi-course**.
3. Émettre `AT$SF=<canal>,11` → ouvre une fenêtre d'environ **60 secondes**.
4. Depuis **la télécommande d'origine du volet cible**, dérouler la séquence :
   1. **montée** — attendre la butée haute ;
   2. **descente** — laisser apparaître environ 4 lattes (quelques secondes) ;
   3. **stop** ;
   4. **montée** — attendre la butée haute.
5. Laisser expirer la fenêtre de 60 secondes sans rien émettre.

Le canal est alors appairé : `AT$SF=<canal>,0|1|2` pilote le volet.

### Points importants

- ✅ **La sélection du volet se fait par la télécommande.** Seul le moteur qui reçoit la
  séquence de sa propre télécommande s'appaire. Les autres volets à portée ne sont pas
  affectés, ce qui a été vérifié sur une installation comportant plusieurs volets.
- ✅ **L'appairage est additif.** Le volet continue de répondre à sa télécommande d'origine et
  à ses canaux précédents.
- ❓ On ignore si la trame `11` est émise une seule fois ou répétée pendant la fenêtre. La
  séquence ci-dessus, avec la trame émise **avant** la chorégraphie, est celle qui a été
  validée.
- ❓ La chorégraphie décrite est celle documentée pour ce matériel. D'autres modèles de
  télécommande utilisent un sélecteur `P`/`N` et un appui long sur *stop* — variante non
  testée ici.

---

## 11. Positionnement intermédiaire

✅ **Validé**

En l'absence de commande de position et de tout retour d'état, une position intermédiaire
s'obtient en **chronométrant** : lancer le mouvement, puis émettre un `stop` après le délai
voulu.

```
AT$SF=<canal>,0      # départ montée, t0
...attente de N secondes...
AT$SF=<canal>,2      # stop
```

Mesure relevée sur un test à 8 secondes : écart réel de **8,005 s**, soit 5 ms de dérive. La
précision du pilotage n'est donc pas le facteur limitant — l'imprécision vient du moteur
(inertie, temps de démarrage) et du cumul d'erreurs.

### Implications pour une position 0–100 %

- il faut **calibrer la durée de course complète**, séparément pour la montée et la descente,
  celles-ci différant fréquemment ;
- la position ne peut être qu'**estimée**, et **dérive** au fil des mouvements ;
- elle peut être **recalée** en envoyant le volet en butée (0 % ou 100 %), le moteur s'y
  arrêtant de lui-même.

---

## 12. Absence de réception radio

✅ **Validé**

Le dongle est un **émetteur seul**. Il ne remonte aucune information sur les trames radio
émises autour de lui.

### Observation

Port série ouvert en écoute **strictement passive**, sans qu'aucune commande ne soit émise,
pendant qu'une télécommande d'origine pilotait un volet — séquence montée, stop, descente,
stop, puis descente jusqu'en butée basse.

**Résultat : aucun octet reçu.** Les moteurs ont pourtant obéi, les trames étaient donc bien
présentes sur la bande.

### Aucun mode d'écoute exposé

Aucun paramètre du firmware ne laisse entrevoir une réception activable. Sur les cinq
paramètres interrogés, un seul répond :

| Requête | Réponse |
|---|---|
| `AT$CP?` | `14` puis `AT$CP:OK` |
| `AT$CW?` | `AT$CW:KO` |
| `AT$P?` | `AT$P:KO` |
| `AT$SN?` | `AT$SN:KO` |
| `AT$TR?` | `AT$TR:KO` |

⚠️ `AT$CW=<mode>` n'a **pas** été testé en écriture. En radio, *CW* désigne habituellement une
*continuous wave*, une porteuse continue servant aux essais d'émission. L'activer à l'aveugle
ferait courir le risque d'une émission permanente sur la bande. À ne pas explorer sans
précaution.

### Conséquences

- aucune confirmation qu'un moteur a exécuté une commande ;
- aucune position réelle ne peut être obtenue ;
- **les commandes passées depuis une télécommande physique restent invisibles** : une position
  estimée dérive alors sans autre recalage possible qu'un envoi en butée.

Un véritable retour d'état supposerait un **récepteur distinct** — typiquement un CC1101 en
réception sur 868,425 MHz décodant les trames des télécommandes — ce qui sort du périmètre de
cette bibliothèque.

---

## 13. Commandes dangereuses

⛔ À manipuler avec précaution — ces opérations peuvent faire perdre des appairages.

| Commande | Risque |
|---|---|
| `ATZ` | **Reset usine.** Effacerait vraisemblablement toute la table des canaux, donc l'ensemble des appairages. Jamais testé. |
| `AT$SF=<canal>,14` | *Unregister* — désappairerait le volet du canal visé. |
| `AT$C=<canal>,...` | Écrase l'identité du canal, donc son appairage. |
| `AT$SN=` | Modifierait un numéro de série, avec un risque de désynchronisation. |

**Garde-fous recommandés dans la bibliothèque :**

- ne jamais exposer `ATZ` dans l'API publique, ou l'assortir d'une confirmation explicite ;
- refuser par défaut toute écriture (`AT$C=`, code `14`) sur un canal dont le `sync` est non
  nul, sauf paramètre explicite de forçage ;
- proposer un export complet de la table **avant** toute opération destructive.

---

## 14. Séquence d'initialisation de la box

🟡 **Partiel** — séquence issue de l'analyse du greffon de la box (cf. §17), non nécessaire au
pilotage.

```
AT?                     ping
ATQ0                    quiet mode
AT$C?                   lecture de la table
AT$TR=25,15,70,70       temporisations
AT$CP=14                puissance d'émission
AT$CP?                  relecture
AT&V                    identification
```

En pratique, **aucune initialisation n'est requise** : le dongle répond à `AT$C?` et à
`AT$SF=` dès l'ouverture du port, sans configuration préalable. Les valeurs
`T0=25,T1=15,T2=70,T3=70` sont celles rapportées par `AT&V` et correspondent à celles que la
box positionne.

### Divergences relevées

Deux points de l'analyse antérieure sont infirmés par l'observation directe :

| Affirmation antérieure | Observation |
|---|---|
| `AT&V` retournerait la liste des clés | ❌ `AT&V` ne renvoie **aucune clé**. C'est `AT$C?` qui expose la table. La mention *« Received list of keys »* provenait d'un message de log du greffon, non d'une réponse du dongle. |
| `AT$CP` serait un « paramètre de configuration » | ❌ `AT?` documente `AT$CP=<power>` : il s'agit de la **puissance d'émission**. |

---

## 15. Points non validés

À confirmer par l'expérimentation :

- [ ] `AT$SF=<canal>,14` — *unregister* : effet réel côté moteur
- [ ] Second favori (`FAV_CALL_2`) et enregistrement par trame (`FAV_SET_1`, `FAV_SET_2`) :
      probablement **inexistants** côté protocole, le greffon de la box n'émettant que six
      actions (§8). À ne pas rechercher en balayant les codes non attribués.
- [ ] **Codes d'action non attribués** — `3`, `5` à `10`, `12`, `13`. L'interface de la box
      expose des actions sans correspondance connue à ce jour : `FAV_SET_1`, `FAV_CALL_2`,
      `FAV_SET_2`, `TILT` (inclinaison, pour les BSO) et `POSITION`. Elles occupent
      vraisemblablement une partie de ces codes.
      > ⛔ **Ne pas balayer ces codes à l'aveugle.** Sur ce type de motorisation, certaines
      > séquences radio servent au réglage des **fins de course** : un code envoyé au hasard
      > risque de dérégler les butées haute et basse du volet. Les codes `11` et `14` agissent
      > déjà sur la configuration du moteur, cette zone n'a donc rien d'anodin.
- [ ] `AT$C=` — écriture d'identité, restauration et migration vers un autre dongle
- [ ] `AT$P=`, `AT$CW=`, `AT$SN=` — rôle et valeurs admises
- [ ] `AT$TR=` et `AT$CP=` — effet mesurable sur la portée et la fiabilité d'émission
- [ ] `ATQ<n>` — effet du *quiet mode* sur le format des réponses
- [ ] `A/` — répétition de la dernière commande
- [ ] `Read Protection Active : 1` — conséquences sur `AT$C?`
- [ ] Trames binaires : d'anciens travaux mentionnent un décodage de paquets binaires renvoyés
      par le dongle. Aucun n'a été observé, ni en réponse à `AT$SF`, ni spontanément (§12) —
      reste à savoir s'ils apparaissent dans un mode ou une configuration particulière
- [ ] Comportement avec plusieurs dongles simultanément à portée
- [ ] Portée radio effective et influence de l'antenne
- [ ] Autres références de dongle et autres révisions de firmware

---

## 16. Notes d'implémentation

Recommandations pour `pyneosol`, issues des observations ci-dessus.

**Lecture des réponses**

- lire jusqu'à la terminaison `:OK` / `:KO` plutôt que d'attendre un délai fixe ;
- prévoir malgré tout un délai de garde : `AT$C?` retourne 50 lignes et demande nettement plus
  de temps qu'une commande unitaire (compter quelques secondes) ;
- ignorer les lignes vides, systématiques entre chaque ligne utile ;
- vider le tampon d'entrée avant chaque émission, pour ne pas mélanger les réponses.

**Robustesse**

- attendre ~400 ms après l'ouverture du port ;
- vérifier la présence du marqueur `PFX KEELOQ` via `AT&V` avant toute opération, afin de ne
  pas dialoguer avec un périphérique série quelconque ;
- consigner `Hardware Version` et `Software Version`, le protocole n'étant validé que sur
  `HW 0` / `SW Rev10`.

**Sûreté**

- traiter la table des canaux comme une **donnée sensible** : ne jamais la journaliser en
  clair, masquer les clés dans les messages de débogage et les exceptions ;
- séparer nettement l'API de lecture de l'API destructive.

**Modélisation suggérée**

- un objet *dongle* — connexion, identification, table des canaux ;
- un objet *canal* — `channel`, `serial`, `sync`, `key`, et les actions de mouvement ;
- le suivi de position estimée relève d'une **couche supérieure**, pas de cette bibliothèque,
  qui doit rester un pilote bas niveau.

---

## 17. Références

- [OpenProfalux](https://github.com/Isno-Open/OpenProfalux) — firmware ESP32 + CC1101 pour
  volets Profalux 868 MHz. Son document `docs/PROTOCOLE-DONGLE-AT.md` décrit le protocole AT
  tel que déduit du désassemblage du greffon de la box, **sans dongle physique**. Le présent
  document le confirme sur plusieurs points, le complète et en corrige deux (voir §13).
- [Calypshome-ha](https://github.com/akoonet-homeassistant/Calypshome-ha) — intégration Home
  Assistant passant par le cloud du fabricant.
- Fréquence porteuse relevée par des travaux tiers : **868,425 MHz**, modulation OOK,
  codage KeeLoq.
