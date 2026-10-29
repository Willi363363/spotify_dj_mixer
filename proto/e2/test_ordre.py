"""Ordre v2 (ADR 0001) et échelle de repli au rendu (spec §8), hors ligne.

- contrat.valider_ordre : ordre valide accepté, chaque champ hors bornes refusé, anciens noms et `mode` refusés ;
- e2.py importé sans démarrer (pas de son, pas de PipeWire) : POST /order, /run, /rating, GET /dj-catalogue.js,
  DJ_SLOW, /state ;
- catalogue.rendre : chaque condition de refus provoquée mène au bon repli ; une erreur de rendu ne coupe rien ;
- e2.handle_order de bout en bout sur une mémoire de synthèse : rapport « jouee » et « secours ».
Usage : python3 -I proto/e2/test_ordre.py
"""
import copy
import http.client
import http.server
import json
import os
import sys
import tempfile
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TMP = tempfile.mkdtemp(prefix="test-ordre-")
os.environ["DJ_NOTES"] = os.path.join(TMP, "notes.jsonl")
os.environ["DJ_JOURNAL"] = os.path.join(TMP, "journal.jsonl")
os.environ.pop("DJ_WORK", None)

import e2  # noqa: E402
import synthese as S  # noqa: E402
from transitions import catalogue as C  # noqa: E402
from transitions import voix as V  # noqa: E402
from transitions.contrat import OrdreInvalide, valider_ordre  # noqa: E402
from transitions.outils import SR, Refus  # noqa: E402

ok = True


def verifie(label, cond, detail=""):
    global ok
    print(f"{'ok' if cond else '✗ '} {label}{' : ' + detail if detail else ''}")
    ok &= bool(cond)


# ─── Contrat ────────────────────────────────────────────────────────────────────────────────────────────────
base = S.ordre_dict("C6", replis=["C5", "R1", "R2"], voix_a=[0.1] * 16, voix_b=[0.0] * 16)
o = valider_ordre(base)
verifie("ordre v2 valide accepté", o.transition == "C6" and o.bars == 4 and o.replis == ("C5", "R1", "R2")
        and o.a.point_s == 48.0 and o.b.entree == "E0")
verifie("champ inconnu toléré (cmd de run.sh)", valider_ordre({**base, "cmd": "transition"}).id == base["id"])
rattrapage = S.ordre_dict("R1", replis=["R2"], manuel=True)
verifie("ordre de rattrapage (manuel, sortie nulle, grilles vides) accepté", valider_ordre(rattrapage).manuel)


def mute(chemin, valeur):
    d = copy.deepcopy(base)
    cible = d
    for k in chemin[:-1]:
        cible = cible[k]
    if valeur is KeyError:
        del cible[chemin[-1]]
    else:
        cible[chemin[-1]] = valeur
    return d


cas = [
    ("ancien champ mode", {**base, "mode": "melange"}),
    ("ancien nom de transition", mute(["transition"], "melange")),
    ("ancien nom dans replis", mute(["replis"], ["montee"])),
    ("transition inconnue", mute(["transition"], "C9")),
    ("v = 1", mute(["v"], 1)),
    ("id invalide", mute(["id"], "a b")),
    ("bars incompatible (C6 en 8)", mute(["bars"], 8)),
    ("bars booléen", mute(["bars"], True)),
    ("params non permis pour C6", mute(["params"], {"queue_mesures": 2})),
    ("t_wall 40 s dans le passé", mute(["t_wall"], time.time() * 1000 - 40000)),
    ("ratio hors bornes", mute(["ratio"], 5)),
    ("gapless en texte", mute(["gapless"], "true")),
    ("a.bar_s hors bornes", mute(["a", "bar_s"], 0.1)),
    ("a.sortie_s manquant", mute(["a", "sortie_s"], KeyError)),
    ("a.sortie_s nul hors rattrapage", mute(["a", "sortie_s"], None)),
    ("a.beats : 5 valeurs", mute(["a", "beats"], [0.0] * 5)),
    ("a.beats hors ]−60 ; 60[", mute(["a", "beats"], [70.0] * 10)),
    ("a.grille inconnue", mute(["a", "grille"], "bonne")),
    ("a.voix : 17 valeurs", mute(["a", "voix"], [0.0] * 17)),
    ("b.voix hors [0 ; 1]", mute(["b", "voix"], [1.5])),
    ("b.entree inconnue", mute(["b", "entree"], "E3")),
    ("b.cible_s < b.entree_s", mute(["b", "cible_s"], -1)),
    ("manuel sans to_uri", mute(["manuel"], True)),
    ("replis : 4", mute(["replis"], ["C5", "R1", "R2", "R2"])),
    ("replis_plan au rendu", mute(["replis_plan"], [{"de": "C7", "vers": "C6", "raison": "", "ou": "rendu"}])),
    ("raison > 300 caractères", mute(["raison"], "x" * 301)),
    ("voix_source inconnue", mute(["voix_source"], "micro")),
    ("uri invalide", mute(["a", "uri"], "spotify:track:'; alert(1)")),
]
for label, d in cas:
    try:
        valider_ordre(d)
        verifie(f"refus : {label}", False)
    except OrdreInvalide as e:
        verifie(f"refus : {label}", True, str(e))
c2 = valider_ordre(S.ordre_dict("C2", params={"queue_mesures": 4}))
verifie("params de C2 acceptés", c2.params == {"queue_mesures": 4})
try:
    valider_ordre(S.ordre_dict("C2", params={"queue_mesures": 5}))
    verifie("refus : queue_mesures = 5", False)
except OrdreInvalide:
    verifie("refus : queue_mesures = 5", True)

# ─── e2.py : entrées ────────────────────────────────────────────────────────────────────────────────────────
code, body = e2.accept_order({**base, "cmd": "transition"}, demarrer=False)
verifie("POST /order v2 → 202 {ok, id}", code == 202 and body == {"ok": True, "id": base["id"]})
code, body = e2.accept_order({**base, "mode": "melange"}, demarrer=False)
verifie("POST /order avec mode → 400", code == 400 and "mode" in body["message"], body.get("message", ""))
code, _ = e2.accept_order(mute(["transition"], "drop_swap"), demarrer=False)
verifie("POST /order avec ancien nom → 400", code == 400)
A, B = "spotify:track:" + "A" * 22, "spotify:track:" + "B" * 22
verifie("POST /run avec mode → 400", e2.launch({"mode": "montee", "a": A, "b": B})[0] == 400)
verifie("POST /run avec ancien nom → 400", e2.launch({"transition": "melange", "a": A, "b": B})[0] == 400)
verifie("POST /run v2 sans DJ_WORK → 503", e2.launch({"transition": "C5", "a": A, "b": B})[0] == 503)
verifie("DJ_SLOW borné à 1,00..1,06, défaut 1,03",
        (e2._slow("1.10"), e2._slow("0.9"), e2._slow("abc"), e2._slow("1.02")) == (1.06, 1.0, 1.03, 1.02))

# /rating v2
verifie("note d'un id inconnu → 409", e2.rate({"id": "inconnu", "note": 4})[0] == 409)
rap = e2.rapport_vide(valider_ordre(base), 60 * SR)
rap.update(transition_jouee="C6", issue="jouee")
e2.enregistrer(rap)
verifie("note hors 1-5 → 400", e2.rate({"id": base["id"], "note": 6})[0] == 400)
verifie("étiquette inconnue → 400", e2.rate({"id": base["id"], "note": 4, "etiquettes": ["nul"]})[0] == 400)
code, _ = e2.rate({"id": base["id"], "note": 4, "etiquettes": ["trop_court"], "commentaire": "ok"})
with open(os.environ["DJ_NOTES"]) as f:
    ligne = json.loads(f.readlines()[-1])
verifie("note par id → 201, ligne avec rapport complet", code == 201 and ligne["rapport"]["transition_jouee"] == "C6"
        and ligne["etiquettes"] == ["trop_court"])
verifie("moyenne des notes par transition jouée", e2.notes_avg == {"C6": 4.0}, str(e2.notes_avg))
with open(os.environ["DJ_JOURNAL"]) as f:
    verifie("rapport écrit dans DJ_JOURNAL", json.loads(f.readline())["id"] == base["id"])

# HTTP : origine, routes retirées, catalogue
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), e2.Screen)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def requete(methode, chemin, corps=None, origine=e2.ORIGIN):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    h = {"Content-Type": "application/json"}
    if origine:
        h["Origin"] = origine
    c.request(methode, chemin, body=json.dumps(corps).encode() if corps is not None else None, headers=h)
    r = c.getresponse()
    return r.status, r.getheader("Content-Type"), r.read()


st, kind, data = requete("GET", "/dj-catalogue.js")
existe = os.path.exists(e2.CATALOGUE_JS)
verifie("GET /dj-catalogue.js", (st == 200 and kind.startswith("text/javascript")) if existe else st == 404,
        f"{st} {kind}")
st, _, data = requete("POST", "/order", {**base, "mode": "montee"})
verifie("HTTP POST /order ancien mode → 400", st == 400, data.decode()[:80])
verifie("HTTP POST /order sans origine → 403", requete("POST", "/order", base, origine=None)[0] == 403)
verifie("HTTP POST /double retiré → 403", requete("POST", "/double", {})[0] == 403)


def brut(longueur):
    """POST /order avec un Content-Length forgé, sans corps : doit répondre 400 sans bloquer."""
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.putrequest("POST", "/order")
    c.putheader("Origin", e2.ORIGIN)
    c.putheader("Content-Length", str(longueur))
    c.endheaders()
    return c.getresponse().status


verifie("Content-Length négatif → 400 sans blocage", brut(-1) == 400)
verifie("Content-Length au-delà du plafond → 400", brut(e2.MAX_CORPS + 1) == 400)
st, _, data = requete("GET", "/state")
etat = json.loads(data)
verifie("GET /state : rapport et récentes", st == 200 and etat["derniere_transition"]["id"] == base["id"]
        and isinstance(etat["transitions_recentes"], list) and etat["ralenti"] == e2.SLOW)
srv.shutdown()

# ─── Échelle de repli au rendu ──────────────────────────────────────────────────────────────────────────────


def echelle(label, mem, ordre, place, attendu, avance=60 * SR, raison=None):
    try:
        r, replis = C.rendre(mem, ordre, place, avance=avance)
        chemin = [x["de"] for x in replis] + [r.transition]
        bon = chemin == attendu and all(x["ou"] == "rendu" for x in replis)
        bon &= raison is None or any(raison in x["raison"] for x in replis)
        verifie(label, bon, " → ".join(chemin) + (f" ({replis[0]['raison']})" if replis else ""))
        return r
    except Refus as e:
        verifie(label, attendu == "refus" and getattr(e, "replis", None), str(e))


m = S.Mem(140, riche=True)
echelle("tempos éloignés : C6 → C5 → R1", m, S.ordre("C6", replis=["C5", "R1", "R2"], bpm_b=140), m.place(),
        ["C6", "C5", "R1"], raison="tempos")
m = S.Mem(120, riche=True)
echelle("netteté < 1,5 : C7 → C5 → R1", m, S.ordre("C7", 8, replis=["C5", "R1", "R2"]), m.place(nettete=1.2),
        ["C7", "C5", "R1"], raison="netteté")
# avance requise = (2T + 2) mesures + 8 s : C5 (T = 2) 20 s, R1 (T = 1) 16 s, à 120 BPM
echelle("avance 12 s : C5 et R1 refusés → R2", m, S.ordre("C5", replis=["R1", "R2"]), m.place(),
        ["C5", "R1", "R2"], avance=12 * SR, raison="avance")
verifie("avance requise : C7 16 mesures à 120 BPM = 76 s, 0 sans recouvrement",
        C.avance_requise(16, 2.0) == 76 and C.avance_requise(0, 2.0) == 0)
echelle("C7 16 mesures, avance 60 s : refusé → C5", m, S.ordre("C7", 16, replis=["C5", "R1", "R2"]), m.place(),
        ["C7", "C5"], avance=60 * SR, raison="avance")
echelle("C7 16 mesures, avance 75 s : refusé → C5", m, S.ordre("C7", 16, replis=["C5", "R1", "R2"]), m.place(),
        ["C7", "C5"], avance=75 * SR, raison="avance")
echelle("C7 16 mesures, avance 76 s : accepté", m, S.ordre("C7", 16, replis=["C5", "R1", "R2"]), m.place(), ["C7"],
        avance=76 * SR)
echelle("avance 17 s : C5 refusé → R1", m, S.ordre("C5", replis=["R1", "R2"]), m.place(), ["C5", "R1"], avance=17 * SR)
m = S.Mem(140, riche=True)
echelle("toute l'échelle refusée → Refus (secours)", m, S.ordre("C5", bpm_b=140), m.place(), "refus")

vrai = V.voix_par_mesure
try:
    V.voix_par_mesure = lambda x, bornes: np.full(len(bornes) - 1, 0.9)  # voix partout
    m = S.Mem(120, riche=True)
    echelle("voix sur la mesure bouclée : C4 → C1", m, S.ordre("C4", replis=["C1", "R2"]), m.place(), ["C4", "C1"],
            raison="bouclée")
    # C5 ne superpose que 2 mesures : il ne dépasse jamais O4 (> 2 mesures) et arrête l'échelle
    echelle("voix dans l'intro de B : C6 → C5", m, S.ordre("C6", replis=["C5", "R1", "R2"]), m.place(),
            ["C6", "C5"], raison="intro")
    r = echelle("voix superposées : C7 → C5", m, S.ordre("C7", 8, replis=["C5", "R1", "R2"]), m.place(),
                ["C7", "C5"], raison="superposées")
    verifie("voix_mesures rapporté (2 sur C5)", r is not None and r.infos["voix_mesures"] == 2)
    r = echelle("voix : C1 n'est jamais replié", m, S.ordre("C1", replis=["R2"]), m.place(), ["C1"])
finally:
    V.voix_par_mesure = vrai

fiche = C.FICHES["C1"]
try:
    C.FICHES["C1"] = fiche._replace(rendu=lambda m, o, p: 1 / 0)
    m = S.Mem(120)
    echelle("erreur dans un rendu : journalisée, repli → R2", m, S.ordre("C1", replis=["R2"]), m.place(), ["C1", "R2"],
            raison="erreur")
finally:
    C.FICHES["C1"] = fiche
verifie("identifiants du catalogue = contrat", sorted(C.FICHES) == sorted(e2.X["contrat"].IDS))

# ─── handle_order de bout en bout, sur une mémoire de synthèse ─────────────────────────────────────────────


def charger(mem):
    """Copie la mémoire de synthèse dans celle de e2 et relie l'heure aux échantillons (saut au trou)."""
    e2.buf[:] = 0
    e2.buf[:len(mem.buf)] = mem.buf
    e2.written = len(mem.buf)
    with e2.lock:
        e2.plan.clear()
        e2.last_resume = 0
    t = time.time() * 1000
    idx = mem.end_a + int(0.02 * SR)
    with e2.clock_lock:
        e2.clock[:] = [(t - idx / SR * 1000, 0), (t + (len(mem.buf) - idx) / SR * 1000, len(mem.buf))]
    return t


for ident, bpm_b, attendu in (("C6", 124, ("C6", "jouee")), ("C5", 140, ("secours", "secours"))):
    m = S.Mem(bpm_b, riche=True)
    t = charger(m)
    o = S.ordre(ident, bpm_b=bpm_b, t_wall=t, gapless=False)
    e2.handle_order(o)
    rap = e2.recentes[0]
    with e2.lock:
        prevu = list(e2.plan)
    verifie(f"bout en bout {ident} à {bpm_b} BPM : {attendu[1]}", (rap["transition_jouee"], rap["issue"]) == attendu
            and rap["id"] == o.id and len(prevu) == 1 and prevu[0][4]["id"] == o.id,
            f"{rap['transition_jouee']} / {rap['issue']}, replis {[x['de'] for x in rap['replis']]}, "
            f"mesures {rap['mesures']}")
    if attendu[1] == "jouee":
        mes = rap["mesures"]
        verifie("rapport : mesures de l'ADR 0001", set(mes) == {"calage_ms", "nettete", "basses_ms", "echange_ms",
                                                              "voix_mesures", "sonie_db", "crete_dbfs"}
                and abs(mes["calage_ms"]) <= 20, json.dumps(mes))
        nxt = e2.state()["next"]
        verifie("/state next : id, transition, from, to, dur_s, real_s, sortieA, entreeB, raison",
                {"id", "transition", "from", "to", "dur_s", "real_s", "sortieA", "entreeB", "raison"} <= set(nxt)
                and nxt["transition"] == "C6" and nxt["id"] == o.id)
    else:
        verifie("secours : replis au rendu dans le rapport", [x["de"] for x in rap["replis"]] == ["C5"])

# ─── Placement réel (essai direct 13) : Spotify saute après le 1 de sortie (LEAD < 0), sans silence ───────
# A joue encore 60 à 300 ms après son 1, puis B commence par une attaque forte. Le moteur doit poser la fin de A sur
# ce 1 : ni une mesure plus tôt (défaut vu en direct), ni sur une attaque de B. Ordres v2 actuels (temps de A
# jusqu'à la sortie) et anciens (une mesure de temps après la sortie, tombant dans B).
a_long = S.track(120, 50.0, 220, basse=True, seed=1, riche=True)   # 25 mesures : le 1 de sortie à 48 s
b_son = S.track(126, 30.0, 330, basse=True, seed=2, riche=True)
un = 48 * SR
for apres_ms in (30, 60, 150, 230, 300):   # 30 ms : le 1 tombe entre la fin estimée de A et le début estimé de B
    for ancien in (False, True):
        buf = np.concatenate([a_long[:un + int(apres_ms / 1000 * SR)], b_son])
        e2.buf[:] = 0
        e2.buf[:len(buf)] = buf
        e2.written = len(buf)
        saut = un + int(apres_ms / 1000 * SR)
        t = time.time() * 1000
        idx = saut - int(e2.SWITCH_S * SR)        # l'ordre part SWITCH_S avant le changement dans le flux
        with e2.clock_lock:
            e2.clock[:] = [(t - idx / SR * 1000, 0), (t + (len(buf) - idx) / SR * 1000, len(buf))]
        d = S.ordre_dict("C1", t_wall=t, gapless=True, bpm_a=120, bpm_b=126)
        if not ancien:
            d["a"]["beats"] = [round(-2 + k * 0.5, 4) for k in range(5)] + [round(-4 + k * 0.5, 4) for k in range(4)]
            d["a"]["beats"].sort()
        o = valider_ordre(d)
        fin_a, debut_b, ahead = e2.find_switch(o)
        pl = e2.placer(o, fin_a, debut_b, ahead)
        err = (pl.fin_a - un) / SR * 1000
        verifie(f"placement : saut {apres_ms} ms après le 1 ({'ancien ordre' if ancien else 'ordre v2'}) → fin de A sur ce 1 "
                f"(±15 ms)", abs(err) <= 15, f"{err:+.0f} ms")

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
