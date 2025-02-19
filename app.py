import streamlit as st
import pandas as pd
import random
import os

# Chemin du fichier CSV (vérifiez que ce chemin est correct)
csv_path = "final.csv"

# -------------------------------
# Fonctions auxiliaires
# -------------------------------
def get_genus(scientific_name):
    if not scientific_name:
        return ""
    return scientific_name.split()[0]

def get_species_name(scientific_name):
    words = scientific_name.split()
    if len(words) >= 2:
        return " ".join(words[:2])
    return scientific_name

# -------------------------------
# Chargement des données avec mise en cache
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(csv_path, sep=";")
    # Conversion de la colonne Images en liste en scindant par ";"
    df["Images"] = df["Images"].apply(lambda x: x.split(";") if isinstance(x, str) else x)
    return df

quiz_data = load_data()
quiz_data["Genus"] = quiz_data["Nom_scientifique"].apply(get_genus)

# -------------------------------
# Initialisation de l'état de session
# -------------------------------
if "question" not in st.session_state:
    st.session_state.question = None
if "current_img_index" not in st.session_state:
    st.session_state.current_img_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "total" not in st.session_state:
    st.session_state.total = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# -------------------------------
# Interface - Barre latérale
# -------------------------------
st.sidebar.title("Quiz Botanique - Flore des Alpes Francaise")

mode = st.sidebar.radio("Mode de jeu :", 
                        ["Facile", "Difficile", "Extrêmement difficile", 
                         "Entrainement facile", "Entrainement difficile"],
                        index=0)

# Pour les modes d'entraînement, permettre le choix de la famille
training_family = None
if mode in ["Entrainement facile", "Entrainement difficile"]:
    training_family = st.sidebar.selectbox("Choisissez la famille pour l'entraînement :", 
                                           sorted(quiz_data["Famille"].unique()))

if st.sidebar.button("Nouvelle Question"):
    # Sélection d'une ligne aléatoire selon le mode
    if mode in ["Entrainement facile", "Entrainement difficile"]:
        if not training_family:
            st.sidebar.warning("Veuillez choisir une famille pour l'entraînement.")
        else:
            training_data = quiz_data[quiz_data["Famille"] == training_family]
            if training_data.empty:
                st.sidebar.error("Aucune plante trouvée pour cette famille.")
            else:
                quiz_row = training_data.sample(1).iloc[0]
    else:
        quiz_row = quiz_data.sample(1).iloc[0]
        
    # Récupérer la liste d'images et réinitialiser l'index
    quiz_images = quiz_row["Images"]
    st.session_state.current_img_index = 0

    # Construire le dictionnaire de la question
    correct_species = (quiz_row["Nom_scientifique"] 
                       if mode not in ["Extrêmement difficile", "Entrainement difficile"] 
                       else get_species_name(quiz_row["Nom_scientifique"]))
    
    q = {
        "images": quiz_images,
        "mode": mode,
        "correct_species": correct_species,
        "correct_family": quiz_row["Famille"],
        "correct_common": quiz_row["Nom_commun"]
    }
    
    # Pour les modes QCM, préparer les propositions
    if mode in ["Facile", "Difficile", "Entrainement facile"]:
        if mode in ["Facile", "Entrainement facile"]:
            pool = quiz_data if mode == "Facile" else quiz_data[quiz_data["Famille"] == training_family]
            corr = quiz_row["Nom_scientifique"]
            available_species = pool[pool["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
            if len(available_species) >= 3:
                choices = random.sample(available_species, 3) + [corr]
            else:
                choices = available_species + [corr]
            random.shuffle(choices)
            q["species_choices"] = choices
            # En mode Facile, ajouter également un QCM pour la famille
            if mode == "Facile":
                available_families = list(set(quiz_data["Famille"].tolist()) - {quiz_row["Famille"]})
                if len(available_families) >= 3:
                    fam_choices = random.sample(available_families, 3) + [quiz_row["Famille"]]
                else:
                    fam_choices = available_families + [quiz_row["Famille"]]
                random.shuffle(fam_choices)
                q["family_choices"] = fam_choices
        elif mode == "Difficile":
            corr = quiz_row["Nom_scientifique"]
            genus_corr = quiz_row["Genus"]
            same_genus = quiz_data[quiz_data["Genus"] == genus_corr]
            same_genus = same_genus[same_genus["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
            if len(same_genus) >= 3:
                other_names = random.sample(same_genus, 3)
            else:
                needed = 3 - len(same_genus)
                available_species = quiz_data[quiz_data["Nom_scientifique"] != corr]["Nom_scientifique"].tolist()
                other_names = same_genus + random.sample(available_species, min(needed, len(available_species)))
            choices = [corr] + other_names
            random.shuffle(choices)
            q["species_choices"] = choices
            available_families = list(set(quiz_data["Famille"].tolist()) - {quiz_row["Famille"]})
            if len(available_families) >= 3:
                fam_choices = random.sample(available_families, 3) + [quiz_row["Famille"]]
            else:
                fam_choices = available_families + [quiz_row["Famille"]]
            random.shuffle(fam_choices)
            q["family_choices"] = fam_choices
    st.session_state.question = q
    st.session_state.feedback = ""

if st.sidebar.button("Photo suivante"):
    if st.session_state.question is not None:
        if st.session_state.current_img_index < len(st.session_state.question["images"]) - 1:
            st.session_state.current_img_index += 1
        else:
            st.session_state.current_img_index = 0

st.sidebar.subheader(f"Score: {st.session_state.score} / {st.session_state.total}")

# -------------------------------
# Partie principale de l'application
# -------------------------------
st.title("Quiz Botanique")
if st.session_state.question is not None:
    q = st.session_state.question
    # Afficher l'image courante
    img_url = q["images"][st.session_state.current_img_index]
    st.image(img_url, width=400)
    
    # Afficher la zone de réponse selon le mode
    if q["mode"] in ["Facile", "Difficile", "Entrainement facile"]:
        species_answer = st.radio("Choisissez le nom scientifique :", q.get("species_choices", []), key="species_radio")
        if q["mode"] == "Facile":
            family_answer = st.radio("Choisissez la famille :", q.get("family_choices", []), key="family_radio")
        else:
            family_answer = q["correct_family"]  # Pour les modes où la famille est fixée
    elif q["mode"] in ["Extrêmement difficile", "Entrainement difficile"]:
        species_answer = st.text_input("Entrez le genre et l'espèce (ex: Genus species) :", key="typed_species")
        if q["mode"] == "Extrêmement difficile":
            family_answer = st.text_input("Entrez la famille :", key="typed_family")
        else:
            family_answer = q["correct_family"]

    if st.button("Valider"):
        mode_q = q["mode"]
        feedback = ""
        # Modes QCM
        if mode_q in ["Facile", "Difficile", "Entrainement facile"]:
            if species_answer == q["correct_species"]:
                feedback += "✅ Nom scientifique correct !\n"
                species_points = 1
            else:
                if get_genus(species_answer).lower() == get_genus(q["correct_species"]).lower():
                    feedback += f"⚠️ Genre correct, mais espèce incorrecte. La bonne réponse était: {q['correct_species']}\n"
                    species_points = 0.5
                else:
                    feedback += f"❌ Nom scientifique incorrect ! La bonne réponse était: {q['correct_species']}\n"
                    species_points = 0
            if mode_q == "Facile":
                if family_answer == q["correct_family"]:
                    feedback += "✅ Famille correcte !\n"
                    family_points = 1
                else:
                    feedback += f"❌ Famille incorrecte ! La bonne réponse était: {q['correct_family']}\n"
                    family_points = 0
            else:
                family_points = 0
            if mode_q == "Facile":
                st.session_state.total += 1
            elif mode_q == "Difficile":
                st.session_state.total += 2
            else:  # Entrainement facile
                st.session_state.total += 1
            st.session_state.score += species_points + family_points
        # Modes réponse écrite
        elif mode_q in ["Extrêmement difficile", "Entrainement difficile"]:
            user_species = species_answer.lower().strip()
            correct_species = q["correct_species"].lower().strip()
            if user_species == correct_species:
                feedback += "✅ Nom scientifique correct !\n"
                species_points = 1
            else:
                if get_genus(user_species) == get_genus(correct_species):
                    feedback += f"⚠️ Genre correct, mais espèce incorrecte. La bonne réponse était: {q['correct_species']}\n"
                    species_points = 0.5
                else:
                    feedback += f"❌ Nom scientifique incorrect ! La bonne réponse était: {q['correct_species']}\n"
                    species_points = 0
            if mode_q == "Extrêmement difficile":
                user_family = family_answer.lower().strip()
                correct_family = q["correct_family"].lower().strip()
                if user_family == correct_family:
                    feedback += "✅ Famille correcte !\n"
                    family_points = 1
                else:
                    feedback += f"❌ Famille incorrecte ! La bonne réponse était: {q['correct_family']}\n"
                    family_points = 0
            else:
                family_points = 0
            st.session_state.total += 2 if mode_q == "Extrêmement difficile" else 1
            st.session_state.score += species_points + family_points
        
        # Ajout du nom commun (nom de la plante en français) dans le feedback
        feedback += f"\nNom commun : {q['correct_common']}"
        st.session_state.feedback = feedback

    st.markdown("### Feedback")
    st.markdown(st.session_state.feedback)
    
st.markdown("---")
st.markdown("<div style='font-size:10px; text-align:center; color:gray;'>Crédits : SOUYRIS Thomas / Photos: FloreAlpes</div>", unsafe_allow_html=True)
