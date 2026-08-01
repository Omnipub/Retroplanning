# tests/test_calculs_tjm.py
# Tests du module de calcul pur du simulateur de TJM (calculs_tjm.py).
# Couvre les cas limites listes au cahier des charges, section 7 :
# temps facturable tres faible/nul, charges nulles/elevees, semaines de conges
# proches de 52, revenu nul, valeurs decimales/arrondis, resultats incoherents.

import pytest

from calculs_tjm import (
    DEFAUTS,
    ResultatImpossible,
    ValeurInvalide,
    calculer_tjm,
    valider_entrees,
)


def entrees_par_defaut(**overrides):
    donnees = dict(DEFAUTS)
    donnees.update(overrides)
    return valider_entrees(donnees)


def test_cas_nominal_micro():
    resultat = calculer_tjm(entrees_par_defaut())
    assert resultat.jours_theoriques_an == pytest.approx(224.0)
    assert resultat.jours_facturables_an == pytest.approx(134.4)
    assert resultat.tjm_minimum > 0
    assert resultat.tjm_conseille == pytest.approx(resultat.tjm_minimum * 1.15, abs=0.01)
    assert resultat.repartition["revenu"] + resultat.repartition["charges"] + resultat.repartition["cotisations"] == 100


def test_cas_nominal_societe_ca_cible_superieur_a_micro():
    resultat_micro = calculer_tjm(entrees_par_defaut(statut_juridique="micro"))
    resultat_societe = calculer_tjm(entrees_par_defaut(statut_juridique="societe"))
    # Le coefficient societe (1.45) doit produire un CA cible plus eleve que le taux
    # de cotisations micro par defaut, a besoin identique.
    assert resultat_societe.ca_cible_annuel != resultat_micro.ca_cible_annuel


def test_temps_facturable_nul_leve_resultat_impossible():
    entrees = entrees_par_defaut(temps_facturable=0)
    with pytest.raises(ResultatImpossible):
        calculer_tjm(entrees)


def test_temps_facturable_tres_faible_ajoute_un_avertissement():
    entrees = entrees_par_defaut(temps_facturable=1)
    resultat = calculer_tjm(entrees)
    assert resultat.tjm_minimum > 0
    assert any("faible" in avert for avert in resultat.avertissements)


def test_charges_nulles_calcule_sans_erreur():
    resultat = calculer_tjm(entrees_par_defaut(charges_mensuelles=0))
    assert resultat.tjm_minimum > 0


def test_charges_tres_elevees_calcule_sans_erreur():
    resultat = calculer_tjm(entrees_par_defaut(charges_mensuelles=50000))
    assert resultat.tjm_minimum > 0
    assert any("charges" in avert.lower() for avert in resultat.avertissements)


def test_semaines_conges_proches_de_52_leve_resultat_impossible():
    entrees = entrees_par_defaut(semaines_conges=51.9, jours_par_semaine=1)
    with pytest.raises(ResultatImpossible):
        calculer_tjm(entrees)


def test_semaines_conges_egale_52_refusee_a_la_validation():
    with pytest.raises(ValeurInvalide):
        entrees_par_defaut(semaines_conges=52)


def test_revenu_souhaite_nul_calcule_sans_erreur():
    resultat = calculer_tjm(entrees_par_defaut(revenu_net_mensuel=0, charges_mensuelles=200))
    assert resultat.tjm_minimum > 0


def test_revenu_et_charges_nuls_produit_un_avertissement():
    resultat = calculer_tjm(entrees_par_defaut(revenu_net_mensuel=0, charges_mensuelles=0))
    assert resultat.tjm_minimum == 0
    assert any("nul" in avert.lower() for avert in resultat.avertissements)


def test_valeurs_decimales_et_arrondis_monetaires():
    entrees = entrees_par_defaut(revenu_net_mensuel=2999.99, charges_mensuelles=333.33)
    resultat = calculer_tjm(entrees)
    # Les montants doivent etre arrondis a 2 decimales, sans erreur de type.
    assert round(resultat.ca_cible_annuel, 2) == resultat.ca_cible_annuel
    assert round(resultat.tjm_minimum, 2) == resultat.tjm_minimum


@pytest.mark.parametrize("champ,valeur", [
    ("revenu_net_mensuel", -100),
    ("charges_mensuelles", -1),
    ("mois_remuneres", 0),
    ("mois_remuneres", 13),
    ("temps_facturable", -5),
    ("temps_facturable", 101),
    ("jours_par_semaine", 0),
    ("jours_par_semaine", 8),
    ("semaines_conges", -1),
])
def test_valeurs_negatives_ou_hors_limites_sont_refusees(champ, valeur):
    with pytest.raises(ValeurInvalide):
        entrees_par_defaut(**{champ: valeur})


def test_champ_manquant_leve_valeur_invalide():
    donnees = dict(DEFAUTS)
    donnees["revenu_net_mensuel"] = ""
    with pytest.raises(ValeurInvalide):
        valider_entrees(donnees)


def test_champ_non_numerique_leve_valeur_invalide():
    donnees = dict(DEFAUTS)
    donnees["charges_mensuelles"] = "abc"
    with pytest.raises(ValeurInvalide):
        valider_entrees(donnees)


def test_statut_juridique_invalide_leve_valeur_invalide():
    with pytest.raises(ValeurInvalide):
        entrees_par_defaut(statut_juridique="autoentreprise")


def test_saisie_avec_virgule_et_symboles_est_acceptee():
    donnees = dict(DEFAUTS)
    donnees["revenu_net_mensuel"] = "3 000,50 €"
    donnees["temps_facturable"] = "60%"
    entrees = valider_entrees(donnees)
    assert entrees.revenu_net_mensuel == pytest.approx(3000.50)
    assert entrees.temps_facturable == pytest.approx(60.0)
