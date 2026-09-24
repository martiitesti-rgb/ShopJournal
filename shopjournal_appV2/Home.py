"""
ShopJournal — entry point dell'app Streamlit.

"""
import streamlit as st

from db.database import init_db

from core.recommender import get_recommendations, VARIANTS, EMPTY_NOTE
from db.models import get_generated_note, log_search
from db.models import (
    add_purchase, delete_purchase, get_purchase_history,
    regenerate_note, get_generated_note,
)

st.set_page_config(
    page_title="ShopJournal",
    layout="wide",
)

st.markdown(
    "<style>[data-testid='stStatusWidget'] {visibility: hidden;}</style>",
    unsafe_allow_html=True,
)

init_db()
if "user" not in st.session_state:
    st.session_state.user = None  

st.title("ShopJournal")

if st.session_state.user:
    st.success(f"Hi **{st.session_state.user['username']}**.")
else:
    st.info(
        "You are not logged in"
    )


if "flash_message" in st.session_state:
    st.success(st.session_state["flash_message"])
    del st.session_state["flash_message"]

user = st.session_state.get("user")

note = EMPTY_NOTE
if user:
    generated = get_generated_note(user["id"])
    if generated:
        note = generated
     


query = st.text_input("Cosa stai cercando?", placeholder="es. something quick to eat")
variant = "query_notes_pop_cue"
search=st.button("Search", type="primary")

if "search_results" in st.session_state != []:
        for i, product in enumerate(st.session_state["search_results"], start=1):
            price_str = f"{product.price:.2f}€" if product.price is not None else "prezzo non disponibile"
            st.write(f"{i}. **{product.name}** — {price_str} ")
            ok=st.button("Buy", type="secondary", key=f"buy_{product.id}")
            if ok:
                 if not user:
                    st.warning("You have to login first")
                    st.stop()
                 if product.price is not None:
                     price = product.price
                 else :
                     price = 0
                 add_purchase(user["id"], product.category, product.name, price, None)
                 st.session_state["flash_message"] = f"Bought: {product.name}"
                 st.session_state["search_results"] = []
                 st.rerun()
if search and query.strip():
    log_search(user["id"] if user else None, query, note is not EMPTY_NOTE, variant)

    try:
        purchased = {row["title"] for row in get_purchase_history(user["id"])} if user else set()
        results = get_recommendations(query, note, variant=variant, exclude_titles=purchased)
        st.session_state["search_results"] = results
        if not results:
            st.info("No products match your search.")
      
    except FileNotFoundError as e:
        st.warning("Il catalogo prodotti non è ancora configurato.")
        st.code(str(e))
    except ValueError as e:
        st.warning("Problema con i dati del catalogo.")
        st.code(str(e))