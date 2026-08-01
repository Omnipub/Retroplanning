# calculs_tjm.py
# Module de calcul du simulateur de TJM (Taux Journalier Moyen).
# Aucune dependance a Flask ou a la base de donnees : uniquement des calculs, testables
# isolement (voir tests/test_calculs_tjm.py). Voir cahier des charges section 4 "Logique
# de calcul" et section 7 "Cas limites a tester".
#
# Les taux et coefficients ci-dessous sont des estimations pedagogiques (voir DISCLAIMER
# plus bas) et non un conseil fiscal ou comptable personnalise. Ils sont regroupes ici
# pour rester faciles a modifier (cf. criteres d'acceptation V1).

from dataclasses import dataclass, asdict

JOURS_FERIES_PAR_AN = 11
SEMAINES_PAR_AN = 52

# Taux de cotisations sociales moyen applique au CA pour un statut "micro-entreprise"
# (estimation moyenne prestations de services BIC/BNC). A affiner par activite en V2.
TAUX_COTISATIONS_MICRO = 0.246

# Coefficient multiplicateur applique a la remuneration nette visee pour un statut
# "societe" (charges patronales + IS approximes en un seul coefficient forfaitaire V1).
COEFFICIENT_SOCIETE = 1.45

# Marge appliquee au TJM minimum pour obtenir le TJM conseille (aleas, prospection,
# formation, conges non finances...).
MARGE_TJM_CONSEILLE = 1.15

STATUTS_VALIDES = ("micro", "societe")

DISCLAIMER = (
    "Les taux et formules de cette V1 sont des estimations pedagogiques. "
    "Ils ne constituent ni un conseil fiscal, ni une simulation comptable personnalisee."
)

# Valeurs par defaut realistes, utilisees pour pre-remplir le questionnaire (section 3).
DEFAUTS = {
    "revenu_net_mensuel": 3000.0,
    "mois_remuneres": 11,
    "charges_mensuelles": 400.0,
    "statut_juridique": "micro",
    "temps_facturable": 60.0,
    "jours_par_semaine": 5.0,
    "semaines_conges": 5.0,
}


class ValeurInvalide(ValueError):
    """Une donnee saisie par l'utilisateur est absente, non numerique ou hors limites."""


class ResultatImpossible(ValueError):
    """Les entrees sont individuellement valides mais rendent le calcul du TJM impossible
    (ex : temps facturable nul, plus aucun jour travaille dans l'annee)."""


@dataclass(frozen=True)
class EntreesTJM:
    revenu_net_mensuel: float
    mois_remuneres: float
    charges_mensuelles: float
    statut_juridique: str
    temps_facturable: float
    jours_par_semaine: float
    semaines_conges: float

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ResultatTJM:
    jours_theoriques_an: float
    jours_facturables_an: float
    besoin_annuel_avant_cotisations: float
    ca_cible_annuel: float
    ca_cible_mensuel: float
    tjm_minimum: float
    tjm_conseille: float
    repartition: dict
    avertissements: list

    def as_dict(self):
        return asdict(self)


def _to_float(valeur, nom_champ):
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        raise ValeurInvalide(f"Le champ « {nom_champ} » est obligatoire.")
    try:
        return float(str(valeur).replace(",", ".").replace(" ", "").rstrip("%€"))
    except (TypeError, ValueError):
        raise ValeurInvalide(f"Le champ « {nom_champ} » doit etre un nombre.")


def valider_entrees(donnees):
    """Normalise et valide un dict brut (ex : issu d'un formulaire HTML) en EntreesTJM.
    Leve ValeurInvalide si une valeur est absente, non numerique, negative ou incoherente."""
    revenu_net_mensuel = _to_float(donnees.get("revenu_net_mensuel"), "Revenu net mensuel souhaite")
    if revenu_net_mensuel < 0:
        raise ValeurInvalide("Le revenu net mensuel souhaite ne peut pas etre negatif.")

    mois_remuneres = _to_float(donnees.get("mois_remuneres"), "Nombre de mois a financer")
    if not (0 < mois_remuneres <= 12):
        raise ValeurInvalide("Le nombre de mois a financer doit etre compris entre 1 et 12.")

    charges_mensuelles = _to_float(donnees.get("charges_mensuelles"), "Charges professionnelles mensuelles")
    if charges_mensuelles < 0:
        raise ValeurInvalide("Les charges mensuelles ne peuvent pas etre negatives.")

    statut_juridique = str(donnees.get("statut_juridique") or "").strip().lower()
    if statut_juridique not in STATUTS_VALIDES:
        raise ValeurInvalide("Le statut juridique doit etre « micro » ou « societe ».")

    temps_facturable = _to_float(donnees.get("temps_facturable"), "Part du temps reellement facturable")
    if not (0 <= temps_facturable <= 100):
        raise ValeurInvalide("La part de temps facturable doit etre comprise entre 0 et 100 %.")

    jours_par_semaine = _to_float(donnees.get("jours_par_semaine"), "Jours travailles par semaine")
    if not (0 < jours_par_semaine <= 7):
        raise ValeurInvalide("Le nombre de jours travailles par semaine doit etre compris entre 1 et 7.")

    semaines_conges = _to_float(donnees.get("semaines_conges"), "Semaines non travaillees")
    if not (0 <= semaines_conges < SEMAINES_PAR_AN):
        raise ValeurInvalide("Le nombre de semaines non travaillees doit etre compris entre 0 et 52.")

    return EntreesTJM(
        revenu_net_mensuel=revenu_net_mensuel,
        mois_remuneres=mois_remuneres,
        charges_mensuelles=charges_mensuelles,
        statut_juridique=statut_juridique,
        temps_facturable=temps_facturable,
        jours_par_semaine=jours_par_semaine,
        semaines_conges=semaines_conges,
    )


def calculer_tjm(entrees: EntreesTJM) -> ResultatTJM:
    """Calcule le TJM minimum et conseille a partir d'entrees deja validees.
    Voir cahier des charges section 4 pour le detail des formules."""
    avertissements = []

    jours_theoriques_an = (SEMAINES_PAR_AN - entrees.semaines_conges) * entrees.jours_par_semaine
    jours_theoriques_an -= JOURS_FERIES_PAR_AN
    if jours_theoriques_an <= 0:
        raise ResultatImpossible(
            "Avec ce nombre de semaines de conges et de jours travailles par semaine, "
            "il ne reste aucun jour theorique travaille dans l'annee."
        )

    jours_facturables_an = jours_theoriques_an * (entrees.temps_facturable / 100)
    if jours_facturables_an <= 0:
        raise ResultatImpossible(
            "Le temps facturable renseigne ne laisse aucun jour facturable dans l'annee : "
            "le TJM ne peut pas etre calcule."
        )
    if jours_facturables_an < 20:
        avertissements.append(
            "Le temps facturable renseigne est tres faible : le TJM obtenu sera tres eleve "
            "et pourrait etre difficile a defendre commercialement."
        )

    besoin_annuel_avant_cotisations = (
        entrees.revenu_net_mensuel * entrees.mois_remuneres + entrees.charges_mensuelles * 12
    )

    if entrees.statut_juridique == "societe":
        ca_cible_annuel = (
            entrees.revenu_net_mensuel * entrees.mois_remuneres * COEFFICIENT_SOCIETE
            + entrees.charges_mensuelles * 12
        )
    else:
        ca_cible_annuel = besoin_annuel_avant_cotisations / (1 - TAUX_COTISATIONS_MICRO)

    if ca_cible_annuel <= 0:
        avertissements.append(
            "Avec un revenu souhaite et des charges nulles, le chiffre d'affaires cible "
            "est nul : ce resultat n'est fourni qu'a titre indicatif."
        )

    tjm_minimum = ca_cible_annuel / jours_facturables_an
    tjm_conseille = tjm_minimum * MARGE_TJM_CONSEILLE

    if entrees.charges_mensuelles > 0 and entrees.revenu_net_mensuel > 0 and (
        entrees.charges_mensuelles * 12 > entrees.revenu_net_mensuel * entrees.mois_remuneres
    ):
        avertissements.append(
            "Vos charges annuelles depassent le revenu net vise : verifiez qu'elles sont realistes."
        )

    if entrees.statut_juridique == "societe":
        part_revenu = entrees.revenu_net_mensuel * entrees.mois_remuneres * COEFFICIENT_SOCIETE
        part_charges = entrees.charges_mensuelles * 12
        part_cotisations = 0.0
    else:
        part_revenu = entrees.revenu_net_mensuel * entrees.mois_remuneres
        part_charges = entrees.charges_mensuelles * 12
        part_cotisations = ca_cible_annuel - besoin_annuel_avant_cotisations

    repartition = _repartition_pourcentages(ca_cible_annuel, part_revenu, part_charges, part_cotisations)

    return ResultatTJM(
        jours_theoriques_an=round(jours_theoriques_an, 1),
        jours_facturables_an=round(jours_facturables_an, 1),
        besoin_annuel_avant_cotisations=round(besoin_annuel_avant_cotisations, 2),
        ca_cible_annuel=round(ca_cible_annuel, 2),
        ca_cible_mensuel=round(ca_cible_annuel / 12, 2),
        tjm_minimum=round(tjm_minimum, 2),
        tjm_conseille=round(tjm_conseille, 2),
        repartition=repartition,
        avertissements=avertissements,
    )


def _repartition_pourcentages(total, part_revenu, part_charges, part_cotisations):
    """Repartition pedagogique en pourcentages (section 5.3), arrondie a l'entier tout en
    garantissant une somme de 100 quand le total est strictement positif."""
    if total <= 0:
        return {"revenu": 0, "charges": 0, "cotisations": 0}

    revenu_pct = round(100 * part_revenu / total)
    charges_pct = round(100 * part_charges / total)
    cotisations_pct = 100 - revenu_pct - charges_pct
    if cotisations_pct < 0 and part_cotisations <= 0:
        # Statut "societe" : pas de part cotisations distincte, on corrige l'arrondi sur charges.
        charges_pct += cotisations_pct
        cotisations_pct = 0

    return {"revenu": revenu_pct, "charges": charges_pct, "cotisations": cotisations_pct}
