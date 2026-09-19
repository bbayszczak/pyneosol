# Politique de sécurité

## Versions suivies

Le projet est en **alpha** : seule la dernière version publiée reçoit des correctifs.

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique pour une faille de sécurité.**

Utilisez [le signalement privé de GitHub](https://github.com/bbayszczak/pyneosol/security/advisories/new),
qui ouvre un canal confidentiel avec les mainteneurs. Une première réponse est visée sous 7 jours.

Merci d'inclure une description du problème, les étapes de reproduction et l'impact estimé.

## Ne publiez jamais vos clés

Ce pilote lit la table des canaux du dongle, qui contient les **clés KeeLoq** commandant vos
volets : quiconque les possède peut les actionner. Avant de joindre un log, une sortie de
`AT$C?` ou un export de configuration à une issue, une PR ou un rapport, **masquez les clés et
les numéros de série réels**.

Voir la section « Sécurité » du [README](README.md).
