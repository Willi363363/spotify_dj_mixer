"""Critères d'acceptation automatiques 9.1 de la spec transitions v2, vérifiés sur le son rendu (synthèse).

Un test par critère et par transition du catalogue, nommé d'après le critère (« 9.1-2 basses · C6 · B 124 BPM »).
Les valeurs attendues sont réécrites ici depuis la spec (§3, §4, §8, §9.1), sans reprendre celles du code testé.

- 9.1-1 calage (C5-C8, et R1 depuis l'essai direct 13, §14) mesuré sur les pistes rendues, et repli si le calage est intenable ;
- 9.1-2 basses superposées ≤ 1 temps ; 9.1-3 échange des graves sur **le** 1 prévu par le §4 (pas seulement le
  plus proche) ; 9.1-4 trous ; 9.1-5 clics aux bornes, aux 1 (rampes) et aux deux raccords avec le flux ;
- 9.1-6 niveau O5 et crête ; 9.1-7 courbes du §4 à chaque temps ; 9.1-9 avance ; 9.1-11 échelle de repli du §8
  provoquée (netteté, calage, voix (V3 bouchonné, cf. test_voix.py), avance, B absent) ; 9.1-12 temps de rendu :
  transition prête ≥ 2 s avant d'être jouée avec 60 s d'avance (B arrive en temps réel après le saut).
- 9.1-8 (placement) et 9.1-10 (variété) se vérifient sans son : spicetify/test/simulation.test.mjs.

Écarts connus (affichés « ~ ÉCART CONNU », non bloquants tant qu'ils ne s'aggravent pas) : O5 pour C4 (passe-haut
800 Hz et volume 0,8 imposés par le §4) et pour C8 à 124 BPM (A sous passe-haut, B sous passe-bas).
Usage : python3 -I proto/e2/test_criteres.py
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthese as S  # noqa: E402
from transitions import catalogue as C  # noqa: E402
from transitions import mesures as M  # noqa: E402
from transitions.contrat import BARS_PERMIS, IDS  # noqa: E402
from transitions.outils import SR, Refus  # noqa: E402

AVANCE_S = 60.0                     # avance visée du moteur (D de e2.py)
MARGE_RENDU_S = 2.0                 # 9.1-12
SECHES = ("C1", "C2", "C3", "C4")
SUPERPOSEES = ("C5", "C6", "C7", "C8")
# O5 : écarts connus, avec la borne basse au-delà de laquelle l'écart devient une régression
ECARTS_O5 = {("C4", None): (-6.0, "§4 : boucle sous passe-haut 20 → 800 Hz et volume 1 → 0,8"),
             ("C8", 124): (-3.5, "§4 : A sous passe-haut, B sous passe-bas")}
# §8 : échelle de repli de chaque transition
REPLIS_SPEC = {"C1": ("R2",), "C2": ("C1", "R2"), "C3": ("C1", "R2"), "C4": ("C1", "R2"), "C5": ("R1", "R2"),
               "C6": ("C5", "R1", "R2"), "C7": ("C5", "R1", "R2"), "C8": ("C5", "R1", "R2"), "R1": ("R2",), "R2": ()}

echecs, ecarts = [], []


def verifie(nom, cond, detail=""):
    print(f"{'ok' if cond else '✗ '} {nom}{' : ' + detail if detail else ''}")
    if not cond:
        echecs.append(nom)


def ecart_connu(nom, detail):
    print(f"~  {nom} : ÉCART CONNU, {detail}")
    ecarts.append(nom)


# ─── Mémoire instrumentée : jusqu'où le rendu a lu (pour 9.1-12) ────────────────────────────────────────────

class Mem(S.Mem):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.lu = 0

    def wait(self, n):
        self.lu = max(self.lu, int(n))
        super().wait(n)

    def read(self, a, b):
        self.lu = max(self.lu, int(b))
        return super().read(a, b)


class Cas:
    """Un rendu de synthèse : transition, T, réglages, tempos, et ce qu'il faut pour le mesurer."""

    def __init__(self, ident, bars=None, params=None, bpm_a=120, bpm_b=120):
        self.ident, self.bpm_a, self.bpm_b = ident, bpm_a, bpm_b
        self.m = Mem(bpm_b, bpm_a=bpm_a, riche=True, mesures_a=24 if bpm_a > 100 else 20)
        self.p = self.m.place()
        self.o = S.ordre(ident, bars, params=params, bpm_a=bpm_a, bpm_b=bpm_b)
        self.T = self.o.bars
        t0 = time.perf_counter()
        self.r = C.FICHES[ident].rendu(self.m, self.o, self.p)
        self.rendu_s = time.perf_counter() - t0
        self.beat = self.p.bar_a / 4
        extra = f" T={self.T}" if len(BARS_PERMIS[ident]) > 1 else ""
        extra += "".join(f" {k}={v}" for k, v in (params or {}).items())
        self.nom = f"{ident}{extra} · A {bpm_a} / B {bpm_b} BPM"

    @property
    def L(self):
        """Fin du recouvrement (le 1 final) pour une superposition, jonction (le 1 où B entre) sinon."""
        return int(self.r.infos["recouvrement"][1]) if "recouvrement" in self.r.infos else int(self.r.infos["jonction"])


CAS = [Cas(i, bpm_b=b) for b in (120, 124) for i in IDS]
CAS += [Cas("C7", 16), Cas("C8", 8), Cas("C8", 8, bpm_b=124), Cas("C2", params={"queue_mesures": 4}),
        Cas("C3", params={"frein_temps": 2}), Cas("C3", bpm_a=85, bpm_b=85),
        Cas("R1", bpm_b=128), Cas("R1", bpm_b=113)]  # R1 calé à 6-7 % d'écart de tempo (essai direct 13)


# ─── 9.1-1 Calage ───────────────────────────────────────────────────────────────────────────────────────────

def critere_1_calage(c):
    """|écart B − A| ≤ 20 ms, mesuré sur les pistes rendues (avant somme) pendant le recouvrement."""
    L = c.L
    rep = c.r.reperes[c.r.reperes < L]
    e, n = M.calage(c.r.pistes["a"][:L], c.r.pistes["b"][:L], rep)
    verifie(f"9.1-1 calage ≤ 20 ms · {c.nom}", abs(e) <= 20 and abs(c.r.infos["calage_ms"]) <= 20,
            f"mesuré {e:+.1f} ms (rapporté {c.r.infos['calage_ms']:+.1f} ms), netteté {n:.1f}")


def critere_1_calage_intenable():
    """B décalé au-delà de ce que la correction rattrape : soit calé ≤ 20 ms, soit le rapport indique un repli."""
    for off_ms in (40, 120):
        m = Mem(120, off=int(off_ms / 1000 * SR), riche=True)
        o = S.ordre("C6", replis=["C5", "R1", "R2"])
        r, replis = C.rendre(m, o, m.place(), avance=int(AVANCE_S * SR))
        cal = r.infos.get("calage_ms")
        bon = (r.transition in SUPERPOSEES and abs(cal) <= 20) or (
            replis and r.transition not in ("C6",) and any("calage" in x["raison"] or "netteté" in x["raison"]
                                                           for x in replis))
        verifie(f"9.1-1 calage · B décalé de {off_ms} ms : calé ou replié", bon,
                f"joué {r.transition}, calage {cal if cal is None else round(cal, 1)} ms, "
                f"replis {[(x['de'], x['raison']) for x in replis]}")


# ─── 9.1-2 Basses ───────────────────────────────────────────────────────────────────────────────────────────

def critere_2_basses(c):
    ms = M.basses(c.r.pistes["a"], c.r.pistes["b"], c.beat)
    lim = c.beat / SR * 1000
    verifie(f"9.1-2 basses superposées ≤ 1 temps · {c.nom}", ms <= lim, f"{ms:.0f} ms (1 temps = {lim:.0f} ms)")


# ─── 9.1-3 Échange sur le 1 ─────────────────────────────────────────────────────────────────────────────────

def un_d_echange(c):
    """Le 1 où les graves passent de A à B d'après le §4 (échantillon du segment), None si le §4 n'en fixe pas."""
    u = c.r.uns
    if c.ident in SECHES:
        return int(c.r.infos["jonction"])          # B entre sec et plein au 1
    return {"C5": lambda: u[1],                    # au 1 de m2
            "C6": lambda: u[2],                    # au 1 de m3
            "C7": lambda: u[c.T // 2],             # au 1 de m(T/2 + 1)
            "C8": lambda: u[c.T],                  # au 1 final
            "R1": lambda: u[-1]}.get(c.ident, lambda: None)()


def critere_3_echange(c):
    if c.ident == "R2":
        return  # bord à bord : raccord de 20 ms, pas de grille commune
    attendu = un_d_echange(c)
    t = M.instant_echange(c.r.pistes["a"], c.r.pistes["b"])
    d = None if t is None else (t - attendu) / SR * 1000
    verifie(f"9.1-3 échange des graves sur le 1 prévu (±10 ms) · {c.nom}", d is not None and abs(d) <= 10,
            "B sans graves" if d is None else f"{d:+.1f} ms du 1 attendu")


# ─── 9.1-4 Trous et 9.1-5 clics ─────────────────────────────────────────────────────────────────────────────

def avec_flux(c, ctx_ms=100):
    """Le segment entre le flux avant et le flux après (× gain de B) : les raccords se mesurent aussi."""
    k = int(ctx_ms / 1000 * SR)
    av = c.m.read(c.r.debut - k, c.r.debut)
    ap = c.m.read(c.r.reprise, c.r.reprise + k) * c.r.gain
    return np.concatenate([av, c.r.seg, ap]), k


def critere_4_trous(c):
    x, k = avec_flux(c)
    sil = [(a + k, b + k) for a, b in c.r.infos.get("silences", ())]
    t = M.trous(x, sil)
    verifie(f"9.1-4 pas de trou > 20 ms · {c.nom}", not t, str([(s - k, round(ms, 1)) for s, ms in t]))


def critere_5_clics(c):
    x, k = avec_flux(c)
    bornes = sorted({0, len(c.r.seg), *map(int, c.r.infos.get("bornes", ())), *map(int, c.r.uns)})
    bornes = [b for b in bornes if 0 <= b <= len(c.r.seg)]
    cl = M.clics(x, [b + k for b in bornes], beat=(c.beat, c.p.bar_b / 4))
    verifie(f"9.1-5 pas de clic (bornes, 1, raccords) · {c.nom}", not cl,
            f"{len(bornes)} bornes" if not cl else f"clics à {[round((b - k) / SR, 3) for b in cl]} s")


# ─── 9.1-6 Niveau (O5) ──────────────────────────────────────────────────────────────────────────────────────

def critere_6_niveau(c):
    s = M.sonie(c.r.seg, c.r.infos.get("ref_a"), c.r.infos.get("ref_b"))
    nom = f"9.1-6 sonie 3 s dans [−3 ; +2] dB (O5) · {c.nom}"
    if s is None:
        verifie(nom, False, "références de niveau absentes")
        return
    conforme = -3 <= s[0] and s[1] <= 2
    connu = ECARTS_O5.get((c.ident, c.bpm_b)) or ECARTS_O5.get((c.ident, None))
    if connu and not conforme:
        plancher, pourquoi = connu
        if s[0] >= plancher and s[1] <= 2:
            ecart_connu(nom, f"[{s[0]:.2f} ; {s[1]:.2f}] dB ({pourquoi} ; régression sous {plancher} dB)")
        else:
            verifie(nom + " (écart connu aggravé)", False, f"[{s[0]:.2f} ; {s[1]:.2f}] dB, plancher {plancher}")
    else:
        verifie(nom, conforme, f"[{s[0]:.2f} ; {s[1]:.2f}] dB" + (" (écart connu résorbé)" if connu else ""))
    # Crête : hors des 150 ms de bord, où le segment rejoint le flux à gain 1 (sa crête y est celle du morceau)
    b = int(0.15 * SR)
    cr = M.crete_dbfs(c.r.seg[b:-b])
    verifie(f"9.1-6 crête ≤ −0,3 dBFS · {c.nom}", cr <= -0.3 and np.isfinite(c.r.seg).all(), f"{cr:.2f} dBFS")


# ─── 9.1-7 Courbes ──────────────────────────────────────────────────────────────────────────────────────────

def _up(x):
    return math.sin(math.pi / 2 * min(1.0, max(0.0, x)))


def _down(x):
    return math.cos(math.pi / 2 * min(1.0, max(0.0, x)))


def _lin(v0, v1, x):
    return v0 + (v1 - v0) * min(1.0, max(0.0, x))


def _expo(f0, f1, x):
    return f0 * (f1 / f0) ** min(1.0, max(0.0, x))


def _frac(t, t0, t1):
    return (t - t0) / (t1 - t0)


def courbes_spec(c):
    """[(piste, param, t, valeur)] au milieu de chaque temps, d'après le §4 (et le §8 pour R1, R2)."""
    r, T = c.r, c.T
    rep = np.asarray(r.reperes, dtype=float)
    pts = np.round((rep[:-1] + rep[1:]) / 2).astype(int)
    out = []

    def regle(piste, param, f, de=0, a=None):
        out.extend((piste, param, int(t), float(f(t))) for t in pts if t >= de and (a is None or t < a))

    u = r.uns
    if c.ident in SUPERPOSEES + ("R1",):
        L = c.L
        if c.ident == "C5":  # médiums et aigus en cos sur m1-m2, graves échangés au 1 de m2
            for q in ("mediums", "aigus"):
                regle("a", q, lambda t: _down(t / L), a=L)
                regle("b", q, lambda t: _up(t / L), a=L)
            regle("a", "graves", lambda t: 1 if t < u[1] else 0, a=L)
            regle("b", "graves", lambda t: 0 if t < u[1] else 1, a=L)
        elif c.ident == "C6":
            regle("b", "volume", lambda t: _up(_frac(t, u[0], u[1])), a=L)          # cos 0 → 1 sur m1
            regle("b", "mediums", lambda t: 0.5 if t < u[1] else 1, a=L)            # 0,5 sur m1, 1 dès m2
            regle("b", "aigus", lambda t: 1, a=L)
            regle("b", "graves", lambda t: 0 if t < u[2] else 1, a=L)               # échangés au 1 de m3
            regle("a", "mediums", lambda t: _lin(1, 0.5, _frac(t, u[0], u[2])) if t < u[2]
                  else _lin(0.5, 0, _frac(t, u[2], u[3])), a=L)                     # 1 → 0,5 (fin m2) → 0 (fin m3)
            regle("a", "aigus", lambda t: 1 if t < u[2] else _lin(1, 0, _frac(t, u[2], u[4])), a=L)  # 1 → 0 sur m3-m4
            regle("a", "graves", lambda t: 1 if t < u[2] else 0, a=L)
            regle("a", "volume", lambda t: 1 if t < u[3] else _down(_frac(t, u[3], u[4])), a=L)    # cos 1 → 0 sur m4
        elif c.ident == "C7":
            mid = u[T // 2]
            regle("b", "volume", lambda t: _up(t / mid), a=L)
            regle("b", "aigus", lambda t: _lin(0.5, 1, t / mid), a=L)
            regle("b", "graves", lambda t: 0 if t < mid else 1, a=L)
            regle("a", "volume", lambda t: 1 if t < mid else _down(_frac(t, mid, L)), a=L)
            regle("a", "aigus", lambda t: 1 if t < mid else _lin(1, 0, _frac(t, mid, L)), a=L)
            regle("a", "graves", lambda t: 1 if t < mid else 0, a=L)
        elif c.ident == "C8":
            der = u[T - 1]
            regle("b", "passe_bas_hz", lambda t: _expo(400, 16000, t / L), a=L)
            regle("b", "volume", lambda t: _up(t / u[T // 2]), a=L)
            regle("b", "graves", lambda t: 0, a=L)                                  # pleins au 1 final seulement
            regle("a", "passe_haut_hz", lambda t: _expo(20, 250, t / der) if t < der
                  else _expo(250, 1000, _frac(t, der, L)), a=L)
            regle("a", "volume", lambda t: _lin(1, 0.7, t / L), a=L)
            regle("a", "graves", lambda t: 1, a=L)
        else:  # R1 : 1 mesure en cos, graves de B coupés jusqu'au 1 final
            regle("a", "volume", lambda t: _down(t / L), a=L)
            regle("b", "volume", lambda t: _up(t / L), a=L)
            regle("b", "graves", lambda t: 0, a=L)
        return out
    j = int(r.infos["jonction"])
    n = len(r.seg)
    regle("b", "volume", lambda t: 0 if t < j else 1)                               # B sec et plein au 1
    if c.ident != "C4":
        regle("a", "volume", lambda t: 1 if t < j else 0)                           # A 1 → 0 au 1
    if c.ident == "C2":
        beat = rep[1] - rep[0]
        s0 = j - int(round(beat))                                                    # dernier temps de A
        regle("effet", "volume", lambda t: 1 if t < j else _lin(1, 0, _frac(t, j, n)), de=s0)  # lin sur la queue
        regle("effet", "passe_haut_hz", lambda t: 300, de=s0)
        regle("effet", "passe_bas_hz", lambda t: _expo(8000, 2000, _frac(t, s0, n)), de=s0)
    elif c.ident == "C3":
        beat = rep[1] - rep[0]
        nt = c.o.params.get("frein_temps", 2 if c.bpm_a < 90 else 1)              # 2 temps sous 90 BPM
        s = j - int(round(nt * beat))
        regle("a", "vitesse", lambda t: 1, a=s)
        regle("a", "passe_bas_hz", lambda t: _expo(16000, 500, _frac(t, s, j)), de=s, a=j)
    elif c.ident == "C4":
        bar = 4 * (rep[1] - rep[0])
        n_a = j - 2 * bar                                                            # 2 mesures de boucle
        regle("a", "volume", lambda t: 1 if t < n_a else (_lin(1, 0.8, _frac(t, n_a, j)) if t < j else 0))
        regle("a", "passe_haut_hz", lambda t: _expo(20, 800, _frac(t, n_a, j)), de=n_a, a=j)
    return out


def critere_7_courbes(c):
    att = courbes_spec(c)
    e = M.courbes(c.r.automations, att)
    nb_temps = len(c.r.reperes) - 1
    verifie(f"9.1-7 courbes conformes au §4 (±1 dB, ±10 %) · {c.nom}", not e and len(c.r.automations) >= nb_temps,
            "; ".join(e[:3]) + (f" (+{len(e) - 3})" if len(e) > 3 else "") if e
            else f"{len(att)} relevés comparés")
    if c.ident == "C3":  # vitesse : de 1 à 0 en courbe exponentielle sur le frein, décroissante
        j = int(c.r.infos["jonction"])
        v = [(a.t, a.valeur) for a in c.r.automations if a.piste == "a" and a.param == "vitesse"]
        dans = [x for t, x in sorted(v) if t >= j - c.r.infos["frein_temps"] * c.beat]
        verifie(f"9.1-7 vitesse du frein entre 0 et 1, décroissante · {c.nom}",
                bool(dans) and all(0 <= x < 1 for x in dans) and dans == sorted(dans, reverse=True), str(dans))


# ─── 9.1-9 Avance ───────────────────────────────────────────────────────────────────────────────────────────

def critere_9_avance(c):
    trou = (c.m.start_b - c.m.end_a) / c.beat
    conso = ((c.r.reprise - c.r.debut) - len(c.r.seg)) / c.beat - trou   # en temps de A, trou du saut retiré
    if c.ident == "C4":
        verifie(f"9.1-9 avance regagnée ≥ 1,5 mesure · {c.nom}", -conso >= 6, f"{-conso / 4:+.2f} mesure")
    else:
        verifie(f"9.1-9 avance consommée {4 * c.T} temps ± 1 · {c.nom}", abs(conso - 4 * c.T) <= 1,
                f"{conso:+.2f} temps")


# ─── 9.1-12 Temps de rendu ──────────────────────────────────────────────────────────────────────────────────

def critere_12_temps(c):
    """Le saut a lieu à la fin de A ; B arrive ensuite en temps réel. Le début du segment est joué
    avance − (fin de A − début) s après le saut ; le rendu est prêt quand tout le son qu'il lit est arrivé, plus le
    temps de calcul. Vérifié à 60 s d'avance, et à l'avance minimale que l'échelle accepte pour ce T
    (catalogue.avance_requise) : c'est là que la marge est la plus faible."""
    b_lu_s = max(0, c.m.lu - c.m.end_a) / SR
    pret_s = b_lu_s + c.rendu_s
    requise = C.avance_requise(c.T, c.o.a.bar_s)

    def marge(avance_s):
        return avance_s - (c.m.end_a - c.r.debut) / SR - pret_s

    detail = f"son de B lu jusqu'à +{b_lu_s:.1f} s après le saut, calcul {c.rendu_s:.2f} s"
    if AVANCE_S < requise:  # l'échelle doit la refuser à 60 s : elle n'est alors jamais jouée en retard
        ch, replis = chemin(c.m, c.o, c.p)
        verifie(f"9.1-12 avance 60 s < {requise:.1f} s requises : repliée avant rendu · {c.nom}",
                ch[0] == c.ident and len(ch) > 1 and "avance" in replis[0]["raison"],
                " → ".join(ch) + f" ; {c.ident} n'est jamais jouable avec l'avance visée de {AVANCE_S:.0f} s")
    else:
        verifie(f"9.1-12 prête ≥ 2 s avant d'être jouée (avance 60 s) · {c.nom}", marge(AVANCE_S) >= MARGE_RENDU_S,
                f"marge {marge(AVANCE_S):.1f} s ({detail})")
    if c.T > 0:
        verifie(f"9.1-12 prête ≥ 2 s à l'avance minimale acceptée ({requise:.1f} s) · {c.nom}",
                marge(requise) >= MARGE_RENDU_S, f"marge {marge(requise):.1f} s ({detail})")


# ─── 9.1-11 Échelle de repli ────────────────────────────────────────────────────────────────────────────────

def chemin(m, o, p, avance_s=AVANCE_S):
    """Chemin de l'échelle au rendu : [de…, jouée], ou [de…, "secours"] si tout est refusé. Toute autre exception
    que Refus remonte (elle couperait la lecture)."""
    try:
        r, replis = C.rendre(m, o, p, avance=int(avance_s * SR))
        return [x["de"] for x in replis] + [r.transition], replis
    except Refus as e:
        replis = getattr(e, "replis", [])
        return [x["de"] for x in replis] + ["secours"], replis


def critere_11_repli():
    for ident in IDS:
        verifie(f"9.1-11 échelle de repli de {ident} = §8", tuple(C.FICHES[ident].replis) == REPLIS_SPEC[ident],
                f"{C.FICHES[ident].replis} contre {REPLIS_SPEC[ident]}")

    def essai(nom, m, o, p, attendu, mot, avance_s=AVANCE_S):
        try:
            ch, replis = chemin(m, o, p, avance_s)
        except Exception as e:  # noqa: BLE001
            verifie(f"9.1-11 {nom}", False, f"exception qui couperait la lecture : {e!r}")
            return
        bon = ch == attendu and (mot is None or any(mot in x["raison"] for x in replis))
        verifie(f"9.1-11 {nom}", bon, " → ".join(ch) + (f" ({replis[0]['raison']})" if replis else ""))

    # netteté < 1,5 : toute superposition repliée jusqu'à R1 (R1 n'exige pas de grille)
    for ident in SUPERPOSEES:
        m = Mem(120, riche=True)
        rep = list(REPLIS_SPEC[ident])
        att = [ident] + [x for x in rep if x in SUPERPOSEES] + ["R1"]
        essai(f"netteté 1,2 : {ident} → … → R1", m, S.ordre(ident, replis=rep), m.place(nettete=1.2), att, "netteté")
    # tempos à 16 % : aucune superposition calée possible
    m = Mem(140, riche=True)
    essai("tempos à 16 % : C8 → C5 → R1", m, S.ordre("C8", replis=["C5", "R1", "R2"], bpm_b=140), m.place(),
          ["C8", "C5", "R1"], "tempos")
    # avance, (2T + 2) × mesure + 8 s à 120 BPM : C7 (T = 8 : 44 s) refusé à 20 s, C5 (T = 2 : 20 s) accepté
    m = Mem(120, riche=True)
    essai("avance 20 s : C7 → C5", m, S.ordre("C7", 8, replis=["C5", "R1", "R2"]), m.place(), ["C7", "C5"], "avance",
          avance_s=20)
    # voix mesurée par V3 au rendu : V3 est ajusté sur l'audio réel (docs/tests/11-voix.md) et la voix factice de
    # synthese.py n'en est pas représentative ; un bouchon de V3 qui voit la voix là où elle est placée
    from transitions import voix as V
    bar = 2.0
    vrai = V.voix_par_mesure
    try:
        V.voix_par_mesure = lambda x, bornes: np.ones(len(bornes) - 1, np.float32)
        m = Mem(120, riche=True, voix_a=[(48 - bar, 48)])
        essai("voix sur la mesure bouclée : C4 → C1", m, S.ordre("C4", replis=["C1", "R2"]), m.place(), ["C4", "C1"],
              "bouclée")
        m = Mem(120, riche=True, voix_b=[(0, 4 * bar)])
        essai("voix dans l'intro de B : C6 → C5", m, S.ordre("C6", replis=["C5", "R1", "R2"]), m.place(), ["C6", "C5"],
              "intro")
        m = Mem(120, riche=True, voix_a=[(48 - 8 * bar, 48)], voix_b=[(0, 8 * bar)])
        essai("voix superposées sur 8 mesures : C7 → C5", m, S.ordre("C7", 8, replis=["C5", "R1", "R2"]), m.place(),
              ["C7", "C5"], "superposées")
    finally:
        V.voix_par_mesure = vrai
    # B absent (mémoire qui s'arrête juste après le saut) : Refus, jamais une autre exception
    for ident in ("C1", "C5"):
        m = Mem(120, riche=True, mesures_b=1)
        essai(f"B absent : {ident} → … → secours, sans exception", m,
              S.ordre(ident, replis=list(REPLIS_SPEC[ident])), m.place(), [ident, *REPLIS_SPEC[ident], "secours"], None)


# ─── Exécution ──────────────────────────────────────────────────────────────────────────────────────────────

print(f"== {len(CAS)} rendus de synthèse ({', '.join(c.nom for c in CAS[:2])}, …)")
for titre, f, filtre in (
        ("9.1-1 Calage (C5 à C8, et R1 : §14)", critere_1_calage, lambda c: c.ident in SUPERPOSEES + ("R1",)),
        ("9.1-2 Basses", critere_2_basses, None),
        ("9.1-3 Échange sur le 1", critere_3_echange, None),
        ("9.1-4 Pas de trou", critere_4_trous, None),
        ("9.1-5 Pas de clic", critere_5_clics, None),
        ("9.1-6 Niveau (O5)", critere_6_niveau, None),
        ("9.1-7 Courbes conformes", critere_7_courbes, None),
        ("9.1-9 Avance", critere_9_avance, None),
        ("9.1-12 Temps de rendu", critere_12_temps, None)):
    print(f"-- {titre}")
    for c in CAS:
        if filtre is None or filtre(c):
            f(c)
    if f is critere_1_calage:
        critere_1_calage_intenable()
print("-- 9.1-11 Repli")
critere_11_repli()

print(f"\nÉcarts connus (non bloquants) : {len(ecarts)}")
for e in ecarts:
    print(f"  ~ {e}")
print(f"Échecs : {len(echecs)}")
for e in echecs:
    print(f"  ✗ {e}")
print("RÉSULTAT :", "tout passe" if not echecs else "ÉCHEC")
sys.exit(0 if not echecs else 1)
