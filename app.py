import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import tempfile
import re
import textwrap
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Configuration de l'API Gemini
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(pdf_file):
    """Extrait le texte d'un fichier PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF: {str(e)}")
        return None

def generate_article(full_prompt):
    """Génère un article avec l'API Gemini"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(contents=[full_prompt])
        return response.text
    except Exception as e:
        st.error(f"Erreur lors de la génération de l'article: {str(e)}")
        return None

# --- Suppression de la fonction generate_pdf et du rendu PDF ---
# (La fonction sera à réécrire plus tard avec une nouvelle logique de rendu)


def main():
    st.set_page_config(
        page_title="Générateur d'Articles SEO",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 Générateur d'Articles SEO")
    st.markdown("---")
    
    # Sidebar pour les paramètres
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info("Le prompt utilisé est optimisé pour le freelancing et le SEO. Remplis les champs principaux dans l'interface.")
    
    # Zone principale
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Transcription vidéo (PDF) ou contexte")
        input_method = st.radio(
            "Comment souhaitez-vous fournir la transcription ou le contexte ?",
            [
                "📁 Uploader un fichier PDF (transcription)",
                "✏️ Saisir le contexte manuellement",
                "🔗 Entrer l'URL d'une vidéo YouTube"
            ]
        )
        context = ""
        if input_method == "📁 Uploader un fichier PDF (transcription)":
            uploaded_file = st.file_uploader(
                "Choisissez un fichier PDF (transcription)",
                type=['pdf'],
                help="Le fichier PDF sera utilisé comme transcription vidéo."
            )
            if uploaded_file is not None:
                with st.spinner("Extraction du contenu du PDF..."):
                    context = extract_text_from_pdf(uploaded_file)
                if context:
                    st.success("✅ Transcription extraite avec succès !")
                    context = st.text_area("Transcription extraite (modifiable)", value=context, height=200)
                else:
                    st.error("❌ Impossible d'extraire le contenu du PDF")
        elif input_method == "✏️ Saisir le contexte manuellement":
            context = st.text_area(
                "Saisissez la transcription ou le contexte de votre article",
                height=200,
                placeholder="Collez ici la transcription vidéo ou décrivez le contexte..."
            )
        elif input_method == "🔗 Entrer l'URL d'une vidéo YouTube":
            youtube_url = st.text_input(
                "Collez l'URL de la vidéo YouTube",
                placeholder="https://www.youtube.com/watch?v=..."
            )
            if youtube_url:
                try:
                    match = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", youtube_url)
                    if not match:
                        st.error("Impossible d'extraire l'ID de la vidéo. Veuillez vérifier l'URL.")
                    else:
                        video_id = match.group(1)
                        ytt_api = YouTubeTranscriptApi()
                        fetched_transcript = ytt_api.fetch(video_id, languages=['fr', 'en'])
                        transcript_text = "\n".join([snippet.text for snippet in fetched_transcript])
                        st.success("✅ Transcription extraite avec succès !")
                        
                        # Affichage des 5 premières lignes de la transcription
                        st.info("📝 **Aperçu des 5 premières lignes de la transcription :**")
                        transcript_lines = transcript_text.split('\n')
                        preview_lines = transcript_lines[:5]
                        for i, line in enumerate(preview_lines, 1):
                            if line.strip():  # Ignorer les lignes vides
                                st.markdown(f"**{i}.** {line.strip()}")
                        
                        st.markdown("---")
                        context = st.text_area("Transcription complète (modifiable)", value=transcript_text, height=200)
                except TranscriptsDisabled:
                    st.error("La transcription est désactivée pour cette vidéo.")
                except NoTranscriptFound:
                    st.error("Aucune transcription trouvée pour cette vidéo.")
                except Exception as e:
                    st.error(f"Erreur lors de la récupération de la transcription : {e}")
    
    with col2:
        st.subheader("📝 Sujet principal de l'article")
        article_topic = st.text_input(
            "Sujet principal",
            value="Régie ou Forfait : Quel Mode de Prestation Choisir en Freelance ?",
            help="Définissez le sujet principal de l'article."
        )
        st.subheader("🔑 Mots-clés SEO")
        keywords_input = st.text_area(
            "Liste des mots-clés (un par ligne)",
            height=100,
            placeholder="mot-clé 1\nmot-clé 2\nmot-clé 3",
            help="Entrez un mot-clé par ligne pour optimiser l'article"
        )
        st.subheader("📋 Consignes particulières")
        instructions = st.text_area(
            "Consignes spécifiques pour la rédaction",
            height=100,
            placeholder="Ex: ton formel, longueur 1500 mots, inclure des exemples concrets...",
            help="Donnez des instructions spécifiques pour la rédaction de l'article"
        )
    
    st.markdown("---")
    
    # Bouton de génération
    if st.button("🚀 Générer l'article", type="primary", use_container_width=True):
        # Le contexte n'est plus obligatoire
        if not article_topic:
            st.error("❌ Veuillez fournir un sujet principal")
            return
        if not keywords_input:
            st.warning("⚠️ Aucun mot-clé fourni - l'article ne sera pas optimisé SEO")
        if not instructions:
            instructions = "Aucune consigne particulière"
        # Construction du prompt personnalisé
        full_prompt = f'''
Vous êtes un rédacteur expert spécialisé dans la création d'articles en français sur le freelancing. Votre mission est de générer un article optimisé pour le SEO qui soit engageant, éducatif et informatif, basé sur un sujet donné, une transcription vidéo et des mots-clés cibles.
Voici la transcription vidéo à utiliser comme référence :
<transcript>
{context}
</transcript>
Le sujet principal de l'article est :
<article_topic>
{article_topic}
</article_topic>
Et voici les mots-clés cibles à incorporer :
<target_keywords>
{keywords_input}
</target_keywords>
Avant de rédiger l'article, veuillez planifier votre approche en suivant ces étapes. Encadrez votre planification avec les balises <article_planning> :

1. Analysez la transcription vidéo et listez 3-5 points clés pertinents pour le sujet de l'article. Déterminez l'importance d'une partie par rapport à la longueur du texte du transcript dédié à ce sujet.
2. Énumérez les sections principales de l'article (au moins 3-5 sections).
3. Pour chaque section, définissez 2-3 sous-thèmes potentiels et notez comment intégrer naturellement les mots-clés.
4. Prenez en compte les besoins et les points sensibles du public cible (freelances français âgés de 25-40 ans).
5. Proposez une accroche intrigante pour l'introduction.
6. Réfléchissez à 3 titres et méta-descriptions potentiels intégrant les mots-clés.
7. Créez un bref plan de chaque section, en indiquant les placements possibles des mots-clés.
Une fois la phase de planification terminée, rédigez l'article en suivant ces directives :
8. Structure de l'article :
    - Ne pas fusionnez les sections principales de l'article, uniquement les sous-thèmes
    - Commencez par une introduction engageante qui présente les points principaux.
    - Evitez le plus possible des listes à puces, chaque partie doit contenir des phrases rédigées.
    - Divisez le contenu en sections logiques avec des titres clairs (H2, H3).
    - Concluez en résumant les points clés et en encourageant l'engagement du lecteur.
9. Optimisation SEO :
    - Incorporez naturellement les mots-clés cibles, particulièrement dans le titre, les sous-titres et le premier paragraphe.
    - Utilisez des variations des mots-clés et des termes associés.
    - Incluez des liens internes et externes pertinents.
    - Créez une méta-description et un titre optimisés pour un taux de clics élevé.
10. Style d'écriture :
    - Adoptez un ton décontracté et conversationnel.
    - Partagez des conseils pratiques et des exemples concrets liés au freelancing.
    - Simplifiez les concepts complexes.
    - Tutoyez le lecteur.
    - Restez fidèle à la transcription de la vidéo.
11. Qualité du contenu :
    - Assurez-vous que toutes les informations sont exactes et à jour.
    - Abordez les défis et questions courantes rencontrés par les freelances français.
    - Offrez des perspectives uniques qui distinguent votre contenu.
12. Outro: En italique, ajoute à la fin la phrase suivante: "Si tu veux que l'on discute de ton projet freelance, prends rendez-vous gratuitement avec moi pour que je t'accompagne personnellement". Faites en sorte que cette phrase s'enchaine bien avec la précédente avec une belle transition
Présentez votre article dans le format en markdown avec les sections décrites ci dessous:
Votre titre optimisé pour le SEO ici
Votre méta-description convaincante ici
Votre contenu d'article complet ici, structuré avec les titres, paragraphes et la mise en forme appropriés.
N'oubliez pas de vous concentrer sur la création de contenu qui est à la fois informatif pour les lecteurs et optimisé pour les moteurs de recherche.
Pensez à faire un résultat lisible sur chacun des éléments retournés avec des espaces.
N'affichez pas la partie article_planning, elle doit juste vous aider à rédiger l'article
Affiche uniquement les trois propositions de titre / meta description puis l'article

Instructions particulières de l'utilisateur :
{instructions}
'''
        with st.spinner("🔄 Génération de l'article en cours..."):
            article = generate_article(full_prompt)
        if article:
            st.success("✅ Article généré avec succès !")
            st.subheader("📄 Article généré")
            # Affichage structuré avec titres H1/H2/H3
            import re
            lines = article.split('\n')
            for line in lines:
                if line.startswith('# '):
                    st.title(line[2:].strip())
                elif line.startswith('## '):
                    st.header(line[3:].strip())
                elif line.startswith('### '):
                    st.subheader(line[4:].strip())
                elif line.strip() == '':
                    st.markdown('&nbsp;')  # espace visuel
                else:
                    st.markdown(line)
            # Suppression du bouton de téléchargement PDF
            # (Aucun bouton de téléchargement n'est affiché)
            st.subheader("📊 Statistiques")
            word_count = len(article.split())
            char_count = len(article)
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Mots", word_count)
            with col_stats2:
                st.metric("Caractères", char_count)
            with col_stats3:
                st.metric("Mots-clés fournis", len(keywords_input.split('\n')) if keywords_input else 0)
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Générateur d'Articles SEO - Propulsé par Gemini AI"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 
