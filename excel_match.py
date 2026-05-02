from tqdm import tqdm
import pandas as pd
import re
from unidecode import unidecode
from rapidfuzz import fuzz
import xlwings as xw

# =============================
# NORMALIZATION FUNCTION
# =============================
def normalize(text):
    if pd.isna(text):
        return ""

    text = unidecode(text)  # remove accents
    text = text.lower()

    # remove prefixes
    prefixes = ["state of", "republic of"]
    for p in prefixes:
        if text.startswith(p):
            text = text.replace(p, "")

    # remove suffixes
    suffixes = ["ltd", "inc", "corp", "limited", "co", ":"]
    for s in suffixes:
        text = text.replace(s, "")

    # remove special chars
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # trim spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# =============================
# LOAD DATA
# =============================
def load_data(file_path):
    client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl')

    return client_df, db_df


# =============================
# BUILD INDEXES
# =============================
def build_indexes(db_df):
    exact_lookup = {}
    entity_lookup = {}
    norm_lookup = {}
    norm_entity_lookup = {}

    for _, row in db_df.iterrows():
        comp = str(row['Company Name']).strip()
        entity = str(row['Entity Name']).strip()
        cid = row['Company ID']

        key_exact = (comp, entity)
        exact_lookup.setdefault(key_exact, []).append(row)

        entity_lookup.setdefault(entity, []).append(row)

        n_comp = normalize(comp)
        n_entity = normalize(entity)

        key_norm = (n_comp, n_entity)
        norm_lookup.setdefault(key_norm, []).append(row)

        norm_entity_lookup.setdefault(n_entity, []).append(row)

    return exact_lookup, entity_lookup, norm_lookup, norm_entity_lookup


# =============================
# MATCHING FUNCTION
# =============================
def perform_matching(client_df, db_df):
    exact_lookup, entity_lookup, norm_lookup, norm_entity_lookup = build_indexes(db_df)

    results = []

    #for _, row in client_df.iterrows():
    for _, row in tqdm(client_df.iterrows(), total=len(client_df), desc="Matching Progress"):
        comp = str(row['Company Name']).strip()
        entity = str(row['Entity Name']).strip()

        matched = False

        # ---------------------------
        # TIER 1: Exact Company + Entity
        key_exact = (comp, entity)
        if key_exact in exact_lookup:
            match = exact_lookup[key_exact][0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'],match['Entity ID'],
                            "Exact Company + Entity Match", "", ""])
            continue

        # ---------------------------
        # TIER 2: Exact Entity
        if entity in entity_lookup:
            matches = entity_lookup[entity]
            match = matches[0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'],match['Entity ID'],
                            "Exact Entity Match", len(matches), ""])
            continue

        # ---------------------------
        # TIER 3: Normalized Company + Entity
        n_comp = normalize(comp)
        n_entity = normalize(entity)
        key_norm = (n_comp, n_entity)

        if key_norm in norm_lookup:
            match = norm_lookup[key_norm][0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'],match['Entity ID'],
                            "Normalized Company + Entity Match", "", ""])
            continue

        # ---------------------------
        # TIER 4: Normalized Entity
        if n_entity in norm_entity_lookup:
            matches = norm_entity_lookup[n_entity]
            match = matches[0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'],match['Entity ID'],
                            "Normalized Entity Match", len(matches), ""])
            continue

        # ---------------------------
        # TIER 5: Fuzzy Match
        best_score = 0
        best_match = None

        for _, db_row in db_df.iterrows():
            score = fuzz.token_sort_ratio(entity, str(db_row['Entity Name']))

            if score > best_score:
                best_score = score
                best_match = db_row

        if best_score >= 85:
            results.append([best_match['Company ID'], best_match['Company Name'], best_match['Entity Name'],match['Entity ID'],
                            "Fuzzy Match", "", best_score])
        else:
            results.append(["", "", "", "No Match", "", ""])

    return results


# =============================
# WRITE RESULTS TO SHEET
# =============================
def write_results(file_path):
    client_df, db_df = load_data(file_path)

    # ✅ IMPORTANT: remove old output columns
    client_df = client_df.iloc[:, :2]

    results = perform_matching(client_df, db_df)

    result_df = pd.DataFrame(results, columns=[
        "Database Company ID",
        "Database Company Name",
        "Database Entity Name",
        "Database Entity ID",   # ✅ NEW COLUMN
        "Match Type",
        "Matches Count",
        "Similarity Score"
    ])

    final_df = pd.concat([client_df, result_df], axis=1)

    # ✅ Save without deleting other sheet
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        final_df.to_excel(writer, sheet_name="Client Data", index=False)

    print("✅ Matching Completed")


# =============================
# EXPORT FUNCTION
# =============================
def export_results(file_path, output_path):
    df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')

    df.to_excel(output_path, index=False)
    print("✅ Export Completed")

# =============================
# CLEAR FUNCTION
# =============================

def clear_results(file_path):
    client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl')

    # ✅ keep only A & B
    client_df = client_df.iloc[:, :2]

    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        client_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    print("✅ Reset Completed")




if __name__ == "__main__":
    write_results("matching_file.xlsx")
    export_results("matching_file.xlsx", "output.xlsx")
    clear_results("matching_file.xlsx")