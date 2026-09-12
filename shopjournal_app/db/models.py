
import hashlib
import os
import sqlite3

from db.database import get_connection
from core.note_pipeline import generate_note

PBKDF2_ITERATIONS = 200_000


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    ).hex()


# ---------------------------------------------------------------- Utenti --

def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username or not password:
        return False, "Username e password non possono essere vuoti."
    if len(password) < 6:
        return False, "La password deve avere almeno 6 caratteri."

    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt) "
                "VALUES (?, ?, ?)",
                (username, pwd_hash, salt.hex()),
            )
        return True, "Registrazione completata. Ora puoi accedere."
    except sqlite3.IntegrityError:
        return False, "Username già in uso."


def verify_user(username: str, password: str) -> dict | None:
    """Verifica le credenziali. Ritorna {id, username} se valide, altrimenti None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

    if row is None:
        return None

    salt = bytes.fromhex(row["salt"])
    expected_hash = _hash_password(password, salt)
    if expected_hash != row["password_hash"]:
        return None

    return {"id": row["id"], "username": row["username"]}


# ----------------------------------------------------- Storico d'acquisti --

def add_purchase(user_id: int, subcategory: str, title: str, price: float,
                  rating: int | None = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO purchase_history (user_id, subcategory, title, price, rating) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, subcategory.strip(), title.strip(), price, rating),
        )
        return cur.lastrowid


def delete_purchase(purchase_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM purchase_history WHERE id = ?", (purchase_id,))


def get_purchase_history(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM purchase_history WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()


# --------------------------------------------------------- Nota generata --

def regenerate_note(user_id: int) -> dict | None:
    """Rigenera la nota dallo storico d'acquisti corrente e la salva
    (upsert — un solo record per utente). Ritorna None se lo storico è vuoto.

    Usa core/note_pipeline.generate_note(), la stessa logica (reale,
    portata da v3r1_extraction_pipeline) usata per il Set A della tesi.
    """
    history = get_purchase_history(user_id)
    if not history:
        return None

    purchase_tuples = [(h["subcategory"], h["title"], h["price"], h["rating"]) for h in history]
    generated = generate_note(purchase_tuples)

    terms_str = ",".join(t for t, _ in generated["distinctive_terms"])
    pp = generated["price_profile"]

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generated_notes
                (user_id, note_text, distinctive_terms, price_median, price_max,
                 price_mean, price_std, price_tier, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                note_text = excluded.note_text,
                distinctive_terms = excluded.distinctive_terms,
                price_median = excluded.price_median,
                price_max = excluded.price_max,
                price_mean = excluded.price_mean,
                price_std = excluded.price_std,
                price_tier = excluded.price_tier,
                updated_at = datetime('now')
            """,
            (user_id, generated["note_text"], terms_str, pp["median"], pp["max"],
             pp["mean"], pp["std"], generated["price_tier"]),
        )

    return get_generated_note(user_id)


def get_generated_note(user_id: int) -> dict | None:
    """Ritorna la nota generata per l'utente, pronta per lo scoring
    (con distinctive_terms già come lista, non stringa)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM generated_notes WHERE user_id = ?", (user_id,)
        ).fetchone()

    if row is None:
        return None

    return {
        "note_text": row["note_text"],
        "distinctive_terms": row["distinctive_terms"].split(",") if row["distinctive_terms"] else [],
        "price_tier": row["price_tier"],
        "price_median": row["price_median"],
        "updated_at": row["updated_at"],
    }


# ------------------------------------------------------------- Cronologia --

def log_search(user_id: int | None, query: str, used_generated_note: bool, variant: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO search_history (user_id, query, used_generated_note, variant) "
            "VALUES (?, ?, ?, ?)",
            (user_id, query, int(used_generated_note), variant),
        )


def get_search_history(user_id: int, limit: int = 20) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM search_history WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
