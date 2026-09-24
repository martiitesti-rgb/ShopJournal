
import streamlit as st

from db.models import (
    add_purchase, delete_purchase, get_purchase_history,
    regenerate_note, get_generated_note,
)

st.set_page_config(page_title="Purchased History ShopJournal", layout="wide")

st.markdown(
    "<style>[data-testid='stStatusWidget'] {visibility: hidden;}</style>",
    unsafe_allow_html=True,
)
st.title("Purchased History")


user = st.session_state.get("user")
if not user:
    st.warning("You have to login")
    st.stop()


history = get_purchase_history(user["id"])
if not history:
    st.caption("Make your first purchase")
else:
    for item in history:
        c1, c2 = st.columns([5, 1])
        with c1:
            st.write(f"**{item['title']}** — {item['subcategory']} — "
                     f"{item['price']:.2f}€")
        with c2:
            if st.button("Delete", key=f"del_{item['id']}"):
                delete_purchase(item["id"])
                st.rerun()

