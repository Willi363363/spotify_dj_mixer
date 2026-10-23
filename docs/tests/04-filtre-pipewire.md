# 04 · Filtre PipeWire

**Question** : peut-on couper les basses de Spotify, et faire varier le filtre en direct, sans toucher à Spotify ?

Config : [`../../outils/dj-filter.conf`](../../outils/dj-filter.conf).

## Montage

1. Lancer une instance PipeWire qui charge le filtre, le temps du test :
   ```bash
   pipewire -c outils/dj-filter.conf &
   ```
   Elle crée la sortie virtuelle `dj_filter` : un passe-haut (`bq_highpass`, nommé `hp`) réglé à 20 Hz, donc neutre.
2. Faire passer Spotify par cette sortie :
   ```bash
   pactl move-sink-input <id du flux Spotify> dj_filter
   ```
3. Trouver l'identifiant du nœud `dj_filter` (`pw-dump`), puis régler la coupure :
   ```bash
   pw-cli s <id> Props '{ params = [ "hp:Freq" 300 ] }'
   ```
4. Relire la valeur : `pw-cli e <id> Props`.

Arrêter le processus fait disparaître la sortie : Spotify revient seul sur les haut-parleurs, **mais se met en pause**.

## Déroulé

| Phase | Réglage |
|---|---|
| Normal | 20 Hz |
| Coupe des basses | montée à 300 Hz en 6 paliers sur 0,2 s, tenue 5 s |
| Retour | 20 Hz |
| Balayage | de 20 à 2 000 Hz en 4 s (80 paliers), puis retour |

## Mesures (Around the World, enregistrement avant et après le filtre)

Énergie par bande, en dB relatifs : seule la différence compte.

| Phase | Basses < 150 Hz avant filtre | Basses après filtre | Médiums 300-3 000 Hz après filtre |
|---|---|---|---|
| Normal | 74,8 | 74,8 | 65,5 |
| **Coupe** | 77,8 | **60,4** | 69,8 |
| Retour | 77,2 | 77,2 | 69,2 |

- **−17,4 dB de basses** pendant la coupe (environ 98 % de leur énergie), médiums intacts.
- Chaque valeur envoyée est bien prise (relecture : 300, puis 20).

## Ressenti

Coupe **peu audible** sur les haut-parleurs du portable, qui ne restituent presque pas les graves (cf. [`../environnement.md`](../environnement.md)). À réécouter au casque. Les clics éventuels du balayage par paliers n'ont pas été évalués.

## Conclusion

✅ Filtres et égaliseur pilotables en direct sur le son de Spotify seul. ⚠️ Un effet touche tout le flux : pas d'effet propre à un morceau avant l'étape E2.
