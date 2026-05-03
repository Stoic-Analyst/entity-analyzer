from tqdm import tqdm
import pandas as pd
import re
from unidecode import unidecode
from rapidfuzz import process, fuzz
import time

# =============================
# NORMALIZATION FUNCTION
# =============================
def normalize(text):
    if pd.isna(text):
        return ""

    text = unidecode(text).lower()

    prefixes = ["state of", "republic of"]
    for p in prefixes:
        if text.startswith(p):
            text = text.replace(p, "")

    suffixes = ["ltd", "inc", "corp", "limited", "co", ":"]
    for s in suffixes:
        text = text.replace(s, "")

    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# =============================
# LOAD DATA
# =============================

def load_data(file_path):
    client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl')

    return client_df, db_df



# def load_data(file_path):
#     client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl', usecols="A:B")
#     db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl', usecols="A:D")

#     # ✅ Clean Client Data (Sheet 1)
#     client_df = client_df.fillna("")
#     client_df = client_df[client_df['Entity Name'].astype(str).str.strip() != ""]

#     # ✅ Clean Database Data (Sheet 2)
#     db_df = db_df.fillna("")
#     db_df = db_df[db_df['Entity Name'].astype(str).str.strip() != ""]

#     print(f"✅ Client rows after cleanup: {len(client_df)}")
#     print(f"✅ Database rows after cleanup: {len(db_df)}")

#     return client_df, db_df



# =============================
# BUILD INDEXES
# # =============================
# def build_indexes(db_df):
#     exact_lookup = {}
#     entity_lookup = {}
#     norm_lookup = {}
#     norm_entity_lookup = {}
#     grouped_entities = {}

#     db_entities = db_df['Entity Name'].astype(str).tolist()
    
#     #db_df = db_df.reset_index(drop=True)
#     #db_entities = db_df['Entity Name'].astype(str).tolist()


#     for idx, row in db_df.iterrows():
#         comp = str(row['Company Name']).strip().lower()
#         entity = str(row['Entity Name']).strip().lower()

#         # Exact
#         exact_lookup.setdefault((comp, entity), []).append(row)
#         entity_lookup.setdefault(entity, []).append(row)

#         # Normalized
#         n_comp = normalize(comp)
#         n_entity = normalize(entity)

#         norm_lookup.setdefault((n_comp, n_entity), []).append(row)
#         norm_entity_lookup.setdefault(n_entity, []).append(row)

#         # ✅ Blocking (first-letter grouping)
#         key = entity[:1].lower()
#         if key:
#             grouped_entities.setdefault(key, []).append(idx)

#     return exact_lookup, entity_lookup, norm_lookup, norm_entity_lookup, db_entities, grouped_entities

def build_indexes(db_df):
    exact_lookup = {}
    entity_lookup = {}
    norm_lookup = {}
    norm_entity_lookup = {}
    grouped_entities = {}

    # ✅ VERY IMPORTANT: fix index mismatch issue
    db_df = db_df.reset_index(drop=True)

    # ✅ Build entity list AFTER reset
    db_entities = db_df['Entity Name'].astype(str).tolist()

    for idx, row in db_df.iterrows():

        # ✅ RAW values for normalization later
        comp_raw = str(row['Company Name']).strip()
        entity_raw = str(row['Entity Name']).strip()

        # ✅ LOWERCASE ONLY (for exact tiers) — DO NOT use normalize here
        comp = comp_raw.lower()
        entity = entity_raw.lower()

        # -------------------------
        # ✅ EXACT LOOKUPS (FIXED)
        key_exact = (comp, entity)
        exact_lookup.setdefault(key_exact, []).append(row)

        entity_lookup.setdefault(entity, []).append(row)

        # -------------------------
        # ✅ NORMALIZED LOOKUPS (UNCHANGED)
        n_comp = normalize(comp_raw)
        n_entity = normalize(entity_raw)

        norm_lookup.setdefault((n_comp, n_entity), []).append(row)
        norm_entity_lookup.setdefault(n_entity, []).append(row)

        # -------------------------
        # ✅ BLOCKING (SAFE NOW AFTER RESET INDEX)
        key = entity[:1]
        if key:
            grouped_entities.setdefault(key, []).append(idx)

    return exact_lookup, entity_lookup, norm_lookup, norm_entity_lookup, db_entities, grouped_entities

# =============================
# MATCHING FUNCTION
# =============================
def perform_matching(client_df, db_df):

    (exact_lookup,
     entity_lookup,
     norm_lookup,
     norm_entity_lookup,
     db_entities,
     grouped_entities) = build_indexes(db_df)

    results = []
    fuzzy_cache = {}

    for _, row in tqdm(client_df.iterrows(), total=len(client_df), desc="Matching Progress"):

        comp = str(row['Company Name']).strip().lower()
        entity = str(row['Entity Name']).strip().lower()

        # ---------------------------
        # TIER 1
        if (comp, entity) in exact_lookup:
            match = exact_lookup[(comp, entity)][0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'], match['Entity ID'],
                            "Exact Company + Entity Match", "", ""])
            continue

        # ---------------------------
        # TIER 2
        if entity in entity_lookup:
            matches = entity_lookup[entity]
            match = matches[0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'], match['Entity ID'],
                            "Exact Entity Match", len(matches), ""])
            continue

        # ---------------------------
        # TIER 3
        n_comp = normalize(comp)
        n_entity = normalize(entity)

        if (n_comp, n_entity) in norm_lookup:
            match = norm_lookup[(n_comp, n_entity)][0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'], match['Entity ID'],
                            "Normalized Company + Entity Match", "", ""])
            continue

        # ---------------------------
        # TIER 4
        if n_entity in norm_entity_lookup:
            matches = norm_entity_lookup[n_entity]
            match = matches[0]
            results.append([match['Company ID'], match['Company Name'], match['Entity Name'], match['Entity ID'],
                            "Normalized Entity Match", len(matches), ""])
            continue

        # ---------------------------
        # ✅ Fuzzy skip for small strings
        if len(entity) < 4:
            results.append(["", "", "", "", "No Match", "", ""])
            continue

        # ---------------------------
        # ✅ Cache check
        if entity in fuzzy_cache:
            results.append(fuzzy_cache[entity])
            continue

        # ---------------------------
        # ✅ BLOCKING (First letter filter)
        key = entity[0].lower()
        candidate_indices = grouped_entities.get(key, [])

        if not candidate_indices:
            results.append(["", "", "", "", "No Match", "", ""])
            continue

        candidate_entities = [db_entities[i] for i in candidate_indices]

        # ---------------------------
        # ✅ FAST FUZZY MATCH
        match_name, score, idx = process.extractOne(
            entity,
            candidate_entities,
            scorer=fuzz.token_set_ratio
        )

        true_index = candidate_indices[idx]
        best_match = db_df.iloc[true_index]

        if score >= 65:
            result = [best_match['Company ID'], best_match['Company Name'],
                      best_match['Entity Name'], best_match['Entity ID'],
                      "Fuzzy Match", "", score]
        else:
            result = ["", "", "", "", "No Match", "", ""]

        # ✅ Store in cache
        fuzzy_cache[entity] = result
        results.append(result)

    return results


# =============================
# WRITE RESULTS
# =============================
def write_results(file_path):

    print(f"⏱ Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    client_df, db_df = load_data(file_path)

    client_df = client_df.iloc[:, :2]
    
# ✅ Build indexes
    (exact_lookup,
     entity_lookup,
     norm_lookup,
     norm_entity_lookup,
     db_entities,
     grouped_entities) = build_indexes(db_df)

      # ✅ Main matching
    results = perform_matching(client_df, db_df)

    result_df = pd.DataFrame(results, columns=[
        "Database Company ID",
        "Database Company Name",
        "Database Entity Name",
        "Database Entity ID",
        "Match Type",
        "Matches Count",
        "Similarity Score"
    ])

    final_df = pd.concat([client_df, result_df], axis=1)

    # with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    #     final_df.to_excel(writer, sheet_name="Client Data", index=False)

    
# ✅ OUTPUT FILE 1 → Main results
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        final_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    #print("✅ Main-Matching Completed")

    # ✅ OUTPUT FILE 2 → Multi-match detail
    
    export_multi_match_details(client_df,exact_lookup,entity_lookup,norm_lookup,norm_entity_lookup,file_path)

    print("✅ Main-Matching Completed")
    print("✅ Multi-Matching Completed")

    
# ✅ CREATE MULTI-MATCH OUTPUT FILE
   # export_multi_match_details(client_df, exact_lookup, entity_lookup, file_path)


    #✅ STEP 2: CREATE FULL COPY OF WORKBOOK
    output_file = file_path.replace(".xlsx", "_output.xlsx")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        final_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    #print(f"✅ Output file created: {output_file}")
    #print(f"✅ Output file created: {output2_file}")
    print("🗄️ Output Files Added To Repository")
# =============================
# EXPORT
# =============================
def export_results(file_path, output_path):
    df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    df.to_excel(output_path, index=False)
    print("✅ Export Completed")


# =============================
# CLEAN
# =============================
def clear_results(file_path):
    client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl')

    client_df = client_df.iloc[:, :2]

    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        client_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    print("✅ Reset Completed")

    end_time = time.time()
    print(f"⏱ End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")


    # =============================
# MULTI MATCH EXPANSION OUTPUT
# =============================
# def export_multi_match_details(client_df, exact_lookup, entity_lookup, file_path):

#     expanded_rows = []

#     for _, row in client_df.iterrows():

#         comp = str(row['Company Name']).strip().lower()
#         entity = str(row['Entity Name']).strip().lower()

#         key_exact = (comp, entity)

#         matches = None
#         match_type = ""

#         # Tier 1
#         if key_exact in exact_lookup:
#             matches = exact_lookup[key_exact]
#             match_type = "Exact Company + Entity Match"

#         # Tier 2
#         elif entity in entity_lookup:
#             matches = entity_lookup[entity]
#             match_type = "Exact Entity Match"

#         # Only expand when multiple matches
#         if matches and len(matches) > 1:

#             for match in matches:
#                 expanded_rows.append([
#                     row['Company Name'],               # original client data
#                     row['Entity Name'],
#                     match['Company ID'],
#                     match['Company Name'],
#                     match['Entity Name'],
#                     match.get('Entity ID', ""),
#                     match_type,
#                     len(matches)
#                 ])

#     expanded_df = pd.DataFrame(expanded_rows, columns=[
#         "Client Company Name",
#         "Client Entity Name",
#         "Database Company ID",
#         "Database Company Name",
#         "Database Entity Name",
#         "Database Entity ID",
#         "Match Type",
#         "Total Matches"
#     ])

#     output_file = file_path.replace(".xlsx", "_multi_match_detail.xlsx")

#     expanded_df.to_excel(output_file, index=False)

def export_multi_match_details(client_df,exact_lookup,entity_lookup,norm_lookup,norm_entity_lookup,file_path):

    expanded_rows = []

    for _, row in client_df.iterrows():

        comp_raw = str(row['Company Name']).strip()
        entity_raw = str(row['Entity Name']).strip()

        comp = comp_raw.lower()
        entity = entity_raw.lower()

        n_comp = normalize(comp_raw)
        n_entity = normalize(entity_raw)

        matches = None
        match_type = ""

        # ✅ Tier 1
        key_exact = (comp, entity)
        if key_exact in exact_lookup:
            matches = exact_lookup[key_exact]
            match_type = "Exact Company + Entity Match"

        # ✅ Tier 2
        elif entity in entity_lookup:
            matches = entity_lookup[entity]
            match_type = "Exact Entity Match"

        # ✅ Tier 3 (NEW)
        elif (n_comp, n_entity) in norm_lookup:
            matches = norm_lookup[(n_comp, n_entity)]
            match_type = "Normalized Company + Entity Match"

        # ✅ Tier 4 (NEW)
        elif n_entity in norm_entity_lookup:
            matches = norm_entity_lookup[n_entity]
            match_type = "Normalized Entity Match"

        # ✅ Only expand if multiple matches
        if matches and len(matches) > 1:

            for match in matches:
                expanded_rows.append([
                    comp_raw,
                    entity_raw,
                    match['Company ID'],
                    match['Company Name'],
                    match['Entity Name'],
                    match.get('Entity ID', ""),
                    match_type,
                    len(matches)
                ])

    expanded_df = pd.DataFrame(expanded_rows, columns=[
        "Client Company Name",
        "Client Entity Name",
        "Database Company ID",
        "Database Company Name",
        "Database Entity Name",
        "Database Entity ID",
        "Match Type",
        "Total Matches"
    ])

    output_file = file_path.replace(".xlsx", "_multi_match_detail.xlsx")

    expanded_df.to_excel(output_file, index=False)


    



# =============================
# MAIN
# =============================
if __name__ == "__main__":
    write_results("matching_file.xlsx")
    clear_results("matching_file.xlsx")
