
from pathlib import Path
import pandas as pd

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.parquet"

REQUIRED_COLUMNS = {"asin", "title", "price", "average_rating"}


def load_catalog_raw(path: Path = CATALOG_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Catalogo non trovato in {path}. "
              f"{sorted(REQUIRED_COLUMNS)}."
        )

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Formato non supportato: {path.suffix} (usa .parquet o .csv)")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonne mancanti nel catalogo: {sorted(missing)}. "
            f"Colonne trovate: {sorted(df.columns)}."
        )

    return df
