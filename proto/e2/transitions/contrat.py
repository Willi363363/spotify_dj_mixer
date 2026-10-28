"""Contrat extension → moteur v2 (ADR 0001) et structures partagées des rendus (ADR 0005).

`valider_ordre` est la seule validation de l'ordre : e2.py la fait tourner sur POST /order et sur UDP, et répond
400 avec le message d'`OrdreInvalide`.
"""
import math
import re
import time
from collections import namedtuple
from dataclasses import dataclass, field

import numpy as np

IDS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "R1", "R2")
# T permis par transition (mesures de recouvrement) ; le premier est la valeur par défaut (replis)
BARS_PERMIS = {"C1": (0,), "C2": (0,), "C3": (0,), "C4": (0,), "R2": (0,), "R1": (1,), "C5": (2,), "C6": (4,),
               "C7": (8, 16), "C8": (4, 8)}
PARAMS = {"C2": {"queue_mesures": (2, 3, 4)}, "C3": {"frein_temps": (1, 2)}}
ANCIENS = {"montee", "montee_courte", "echo_doux", "retour_doux", "frein_doux", "filtre", "drop_swap", "melange",
           "refrain", "secours", "build", "spinback", "retour", "mix", "brake", "frein", "loop", "boucle", "echo",
           "coupe", "auto"}
ETIQUETTES = ("rythme_decroche", "basses_doublees", "voix_superposees", "fin_coupee", "mauvais_endroit", "trop_long",
              "trop_court", "saut_volume", "clic_trou", "effet_de_trop")
GRILLES = ("nette", "moyenne", "floue")
ENTREES = ("E0", "E1", "E2")
SOURCES_VOIX = ("paroles", "segments", "aucune")
RE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
RE_URI = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")


class OrdreInvalide(ValueError):
    """Ordre refusé (HTTP 400) ; le message dit pourquoi."""


@dataclass(frozen=True)
class Bord:
    """Ce que l'ordre dit de A (sortie) ou de B (entrée). `point_s` = sortie_s pour A, entree_s pour B."""
    uri: str | None
    duree_s: float | None
    point_s: float | None
    mesure: int | None
    bar_s: float
    beats: tuple
    grille: str
    voix: tuple
    entree: str | None = None       # B seulement : E0, E1, E2
    cible_s: float | None = None    # B seulement : entreeB + T mesures
    perdu_s: float = 0.0            # A : jamais_entendu_s ; B : saute_s (journal)


@dataclass(frozen=True)
class Ordre:
    id: str
    transition: str
    choisie: str
    replis: tuple
    replis_plan: tuple
    bars: int
    params: dict
    t_wall: float
    gapless: bool
    manuel: bool
    to_uri: str | None
    ratio: float
    a: Bord
    b: Bord
    voix_source: str
    raison: str


@dataclass
class Place:
    """Où sont A et B dans la mémoire, calculé par e2.py avant tout rendu (échantillons absolus)."""
    fin_a: int
    debut_b: int
    bar_a: int
    bar_b: int
    beats_a: np.ndarray | None
    beats_b: np.ndarray | None
    nettete_a: float
    nettete_b: float
    extra: int = 0  # ADR 0005 ; non utilisé en v1 (C4 regagne 2 mesures fixes, le ralenti fait le reste)


Automation = namedtuple("Automation", "piste param t valeur")


@dataclass
class Rendu:
    debut: int
    seg: np.ndarray
    reprise: int
    gain: float
    transition: str
    pistes: dict
    reperes: np.ndarray
    uns: np.ndarray
    automations: list
    infos: dict = field(default_factory=dict)


# ─── Validation ─────────────────────────────────────────────────────────────────────────────────────

def _num(d, k, lo=None, hi=None, nul=False, excl=False, defaut=None):
    if k not in d:
        if defaut is not None or nul:
            return defaut
        raise OrdreInvalide(f"champ manquant : {k}")
    v = d[k]
    if v is None:
        if nul:
            return None
        raise OrdreInvalide(f"{k} ne peut pas être nul")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise OrdreInvalide(f"{k} doit être un nombre")
    if lo is not None and (v <= lo if excl else v < lo):
        raise OrdreInvalide(f"{k} hors bornes ({v})")
    if hi is not None and (v >= hi if excl else v > hi):
        raise OrdreInvalide(f"{k} hors bornes ({v})")
    return float(v)


def _entier(d, k, nul=True):
    v = d.get(k)
    if v is None:
        if nul:
            return None
        raise OrdreInvalide(f"champ manquant : {k}")
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise OrdreInvalide(f"{k} doit être un entier ≥ 0")
    return v


def _bool(d, k):
    v = d.get(k, False)
    if not isinstance(v, bool):
        raise OrdreInvalide(f"{k} doit être un booléen")
    return v


def _ident(v, k):
    if not isinstance(v, str) or v not in IDS:
        if isinstance(v, str) and v in ANCIENS:
            raise OrdreInvalide(f"{k} : ancien nom « {v} » refusé, utiliser C1…C8, R1, R2")
        raise OrdreInvalide(f"{k} : transition inconnue")
    return v


def _uri(v, k):
    if v is None:
        return None
    if not isinstance(v, str) or not RE_URI.match(v):
        raise OrdreInvalide(f"{k} : uri invalide")
    return v


def _bord(d, cote, manuel):
    if not isinstance(d, dict):
        raise OrdreInvalide(f"{cote} : objet attendu")
    pref = f"{cote}."
    point_k = "sortie_s" if cote == "a" else "entree_s"
    mesure_k = "sortie_mesure" if cote == "a" else "entree_mesure"
    if point_k not in d:
        raise OrdreInvalide(f"champ manquant : {pref}{point_k}")
    point = _num(d, point_k, lo=0, nul=(cote == "a" and manuel))
    try:
        mesure = _entier(d, mesure_k)
        bar_s = _num(d, "bar_s", 0.3, 5)
        duree = _num(d, "duree_s", lo=0, nul=True)
        perdu = _num(d, "jamais_entendu_s" if cote == "a" else "saute_s", lo=0, nul=True) or 0.0
    except OrdreInvalide as e:
        raise OrdreInvalide(f"{pref}{e}") from None
    beats = d.get("beats", [])
    if not isinstance(beats, list) or not (len(beats) == 0 or 8 <= len(beats) <= 120):
        raise OrdreInvalide(f"{pref}beats : 0 ou 8 à 120 valeurs")
    for x in beats:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not -60 < x < 60:
            raise OrdreInvalide(f"{pref}beats : valeurs dans ]−60 ; 60[")
    grille = d.get("grille")
    if grille not in GRILLES:
        raise OrdreInvalide(f"{pref}grille : nette, moyenne ou floue")
    voix = d.get("voix", [])
    if not isinstance(voix, list) or len(voix) > 16 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1 for x in voix):
        raise OrdreInvalide(f"{pref}voix : au plus 16 valeurs dans [0 ; 1]")
    entree = cible = None
    if cote == "b":
        entree = d.get("entree")
        if entree not in ENTREES:
            raise OrdreInvalide("b.entree : E0, E1 ou E2")
        cible = _num(d, "cible_s", lo=0, defaut=point)
        if point is not None and cible < point:
            raise OrdreInvalide("b.cible_s doit être ≥ b.entree_s")
    return Bord(uri=_uri(d.get("uri"), f"{pref}uri"), duree_s=duree, point_s=point, mesure=mesure, bar_s=bar_s,
                beats=tuple(float(x) for x in beats), grille=grille, voix=tuple(float(x) for x in voix),
                entree=entree, cible_s=cible, perdu_s=perdu)


def valider_ordre(d, maintenant_ms=None):
    """Ordre v2 (ADR 0001) → Ordre. Lève OrdreInvalide(message) au moindre champ manquant ou hors bornes, pour un
    ancien nom de transition et pour l'ancien champ `mode`."""
    if not isinstance(d, dict):
        raise OrdreInvalide("objet JSON attendu")
    if "mode" in d:
        raise OrdreInvalide("champ « mode » (contrat v1) refusé : utiliser « transition » (C1…C8, R1, R2)")
    if d.get("v") != 2 or isinstance(d.get("v"), bool):
        raise OrdreInvalide("v doit valoir 2")
    oid = d.get("id")
    if not isinstance(oid, str) or not RE_ID.match(oid):
        raise OrdreInvalide("id invalide")
    tr = _ident(d.get("transition"), "transition")
    choisie = _ident(d.get("choisie", tr), "choisie")
    replis = d.get("replis", [])
    if not isinstance(replis, list) or len(replis) > 3:
        raise OrdreInvalide("replis : 0 à 3 identifiants")
    replis = tuple(_ident(r, "replis") for r in replis)
    rp = d.get("replis_plan", [])
    if not isinstance(rp, list) or len(rp) > 3:
        raise OrdreInvalide("replis_plan : 0 à 3 objets")
    for x in rp:
        if (not isinstance(x, dict) or x.get("ou") != "plan" or not isinstance(x.get("raison", ""), str)
                or len(x.get("raison", "")) > 300):
            raise OrdreInvalide("replis_plan : objets {de, vers, raison, ou: \"plan\"}")
        _ident(x.get("de"), "replis_plan.de")
        _ident(x.get("vers"), "replis_plan.vers")
    rp = tuple({"de": x["de"], "vers": x["vers"], "raison": x.get("raison", ""), "ou": "plan"} for x in rp)
    bars = d.get("bars")
    if isinstance(bars, bool) or not isinstance(bars, int) or bars not in BARS_PERMIS[tr]:
        raise OrdreInvalide(f"bars : {tr} demande {' ou '.join(map(str, BARS_PERMIS[tr]))}")
    params = d.get("params", {})
    if not isinstance(params, dict):
        raise OrdreInvalide("params : objet attendu")
    permis = PARAMS.get(tr, {})
    for k, v in params.items():
        if k not in permis or isinstance(v, bool) or v not in permis[k]:
            raise OrdreInvalide(f"params : {k} non permis pour {tr}")
    t_wall = _num(d, "t_wall", lo=0, excl=True)
    now = time.time() * 1000 if maintenant_ms is None else maintenant_ms
    if abs(t_wall - now) > 30000:
        raise OrdreInvalide("t_wall à plus de 30 s de l'heure actuelle")
    gapless, manuel = _bool(d, "gapless"), _bool(d, "manuel")
    to_uri = _uri(d.get("to_uri"), "to_uri")
    if manuel and to_uri is None:
        raise OrdreInvalide("to_uri requis pour un changement manuel")
    ratio = _num(d, "ratio", 0.3, 3)
    a = _bord(d.get("a"), "a", manuel)
    b = _bord(d.get("b"), "b", manuel)
    src = d.get("voix_source", "aucune")
    if src not in SOURCES_VOIX:
        raise OrdreInvalide("voix_source : paroles, segments ou aucune")
    raison = d.get("raison", "")
    if not isinstance(raison, str) or len(raison) > 300:
        raise OrdreInvalide("raison : texte de 300 caractères au plus")
    return Ordre(id=oid, transition=tr, choisie=choisie, replis=replis, replis_plan=rp, bars=bars,
                 params=dict(params), t_wall=t_wall, gapless=gapless, manuel=manuel, to_uri=to_uri, ratio=ratio,
                 a=a, b=b, voix_source=src, raison=raison)
