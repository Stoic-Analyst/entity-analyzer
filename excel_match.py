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

    prefixes = ["university of","school of","state of","republic of","kingdom of",
                "government of","region of","city of","county of","province of",
                "canton of","donotuse","do not use","dnu"]
    for p in prefixes:
        if text.startswith(p):
            text = text.replace(p, "")

    suffixes = ["B.V.","S.A.","SICAV","saint","st","intl","bros","brothers",
                "cap","capital","limited","ltd","limited liability company",
                "llc","incorporated","inc","corporation","corp","organisation",
                "organization","org","companies","cos","limited partnership",
                "lp","public limited company","plc","proprietary","pty","ag",
                "GESELLSCHAFTMITBESCHRAENKTERHAFTUNG","gmbh","ab","sa","cie",
                "scarl","cia","bhd","tbk","pt","limited","co",":","(dnu)",
                "dnu","- dnu","donotuse","do not use"]

    for s in suffixes:
        text = text.replace(s.lower(), "")

    noisewords = ["group", "holdings", "holding", "global", "international", "services"]
    for n in noisewords:
        text = text.replace(n, "")

    text = text.replace("&amp;amp;", "and")
    text = text.replace("&amp;", "and")

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


# =============================
# BUILD INDEXES
# =============================
def build_indexes(db_df):
    ci_exact_lookup = {}
    exact_lookup = {}
    entity_lookup = {}
    norm_lookup = {}
    norm_entity_lookup = {}
    grouped_entities = {}

    db_df = db_df.reset_index(drop=True)
    db_entities = db_df['Entity Name'].astype(str).tolist()

    for idx, row in db_df.iterrows():

        comp_raw = str(row['Company Name']).strip()
        entity_raw = str(row['Entity Name']).strip()
        ci_raw = str(row['Identifier']).strip()

        comp = comp_raw.lower()
        entity = entity_raw.lower()
        ci = ci_raw.lower()

        # ✅ FIXED: store correctly in ci_exact_lookup
        ci_exact_lookup.setdefault((comp, entity, ci), []).append(row)

        # ✅ FIXED: keep exact separate
        exact_lookup.setdefault((comp, entity), []).append(row)

        entity_lookup.setdefault(entity, []).append(row)

        n_comp = normalize(comp_raw)
        n_entity = normalize(entity_raw)

        norm_lookup.setdefault((n_comp, n_entity), []).append(row)
        norm_entity_lookup.setdefault(n_entity, []).append(row)

        key = entity[:1]
        if key:
            grouped_entities.setdefault(key, []).append(idx)

    return ci_exact_lookup, exact_lookup, entity_lookup, norm_lookup, norm_entity_lookup, db_entities, grouped_entities


# =============================
# MATCHING FUNCTION
# =============================
def perform_matching(client_df, db_df):

    (ci_exact_lookup,
     exact_lookup,
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
        ci = str(row['Identifier']).strip().lower()

        # ✅ TIER 1 (FIXED)
        if (comp, entity, ci) in ci_exact_lookup:
            matches = ci_exact_lookup[(comp, entity, ci)]
            match = matches[0]
            results.append([
                match['Company ID'], match['Company Name'],
                match['Entity Name'], match['Entity ID'],
                match.get('Identifier', ""),
                "Exact Company + Entity + Identifier Match", len(matches), ""
            ])
            continue

        # ✅ TIER 2
        if (comp, entity) in exact_lookup:
            matches = exact_lookup[(comp, entity)]
            match = matches[0]
            results.append([
                match['Company ID'], match['Company Name'],
                match['Entity Name'], match['Entity ID'],
                match.get('Identifier', ""),
                "Exact Company + Entity Match", len(matches), ""
            ])
            continue

        # ✅ TIER 3
        if entity in entity_lookup:
            matches = entity_lookup[entity]
            match = matches[0]
            results.append([
                match['Company ID'], match['Company Name'],
                match['Entity Name'], match['Entity ID'],
                match.get('Identifier', ""),
                "Exact Entity Match", len(matches), ""
            ])
            continue

        # ✅ TIER 4
        n_comp = normalize(comp)
        n_entity = normalize(entity)

        if (n_comp, n_entity) in norm_lookup:
            matches = norm_lookup[(n_comp, n_entity)]
            match = matches[0]
            # match = norm_lookup[(n_comp, n_entity)][0]
            results.append([
                match['Company ID'], match['Company Name'],
                match['Entity Name'], match['Entity ID'],
                match.get('Identifier', ""),
                "Normalized Company + Entity Match", len(matches), ""
            ])
            continue

        # ✅ TIER 5
        if n_entity in norm_entity_lookup:
            matches = norm_entity_lookup[n_entity]
            match = matches[0]
            results.append([
                match['Company ID'], match['Company Name'],
                match['Entity Name'], match['Entity ID'],
                match.get('Identifier', ""),
                "Normalized Entity Match", len(matches), ""
            ])
            continue

        # ✅ FUZZY
        if len(entity) < 4:
            results.append(["", "", "", "", "", "No Match", "0", ""])
            continue

        if entity in fuzzy_cache:
            results.append(fuzzy_cache[entity])
            continue

        key = entity[0]
        candidate_indices = grouped_entities.get(key, [])

        if not candidate_indices:
            results.append(["", "", "", "", "", "No Match", "0", ""])
            continue

        candidate_entities = [db_entities[i] for i in candidate_indices]

        match_name, score, idx = process.extractOne(entity, candidate_entities, scorer=fuzz.token_set_ratio)

        score = round(score, 2)
        best_match = db_df.iloc[candidate_indices[idx]]

        if score >= 65:
            result = [
                best_match['Company ID'], best_match['Company Name'],
                best_match['Entity Name'], best_match['Entity ID'],
                best_match.get('Identifier', ""),
                "Fuzzy Match", "1", score
            ]
        else:
            result = ["", "", "", "", "", "No Match", "0", ""]

        fuzzy_cache[entity] = result
        results.append(result)

    return results


# =============================
# MULTI MATCH OUTPUT
# =============================
def export_multi_match_details(client_df, ci_exact_lookup, exact_lookup,
                               entity_lookup, norm_lookup, norm_entity_lookup,
                               file_path):

    expanded_rows = []

    for _, row in client_df.iterrows():

        comp_raw = str(row['Company Name']).strip()
        entity_raw = str(row['Entity Name']).strip()
        ci_raw = str(row['Identifier']).strip()

        comp = comp_raw.lower()
        entity = entity_raw.lower()
        ci = ci_raw.lower()

        n_comp = normalize(comp_raw)
        n_entity = normalize(entity_raw)

        matches = None
        match_type = ""

        # ✅ Tier 1
        if (comp, entity, ci) in ci_exact_lookup:
            matches = ci_exact_lookup[(comp, entity, ci)]
            match_type = "Exact Company + Entity + Identifier Match"

        elif (comp, entity) in exact_lookup:
            matches = exact_lookup[(comp, entity)]
            match_type = "Exact Company + Entity Match"

        elif entity in entity_lookup:
            matches = entity_lookup[entity]
            match_type = "Exact Entity Match"

        elif (n_comp, n_entity) in norm_lookup:
            matches = norm_lookup[(n_comp, n_entity)]
            match_type = "Normalized Company + Entity Match"

        elif n_entity in norm_entity_lookup:
            matches = norm_entity_lookup[n_entity]
            match_type = "Normalized Entity Match"

        if matches and len(matches) > 1:
            for match in matches:
                expanded_rows.append([
                    comp_raw, entity_raw,
                    match['Company ID'], match['Company Name'],
                    match['Entity Name'], match.get('Entity ID', ""),
                    match.get('Identifier', ""),
                    match_type, len(matches)
                ])

    expanded_df = pd.DataFrame(expanded_rows, columns=[
        "Client Company Name","Client Entity Name",
        "Database Company ID","Database Company Name",
        "Database Entity Name","Database Entity ID",
        "Database Identifier","Match Type","Total Matches"
    ])

    output_file = file_path.replace(".xlsx", "_multi_match_detail.xlsx")
    expanded_df.to_excel(output_file, index=False)






# =============================
# WRITE RESULTS
# =============================
def write_results(file_path):

    print(f"⏱ Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    client_df, db_df = load_data(file_path)

    results = perform_matching(client_df, db_df)
    
    # export_audit_report(client_df, results, file_path=file_path)

    (ci_exact_lookup,
     exact_lookup,
     entity_lookup,
     norm_lookup,
     norm_entity_lookup,
     db_entities,
     grouped_entities) = build_indexes(db_df)

    result_df = pd.DataFrame(results, columns=[
        "Database Company ID","Database Company Name",
        "Database Entity Name","Database Entity ID",
        "Database Identifier","Match Type",
        "Matches Count","Similarity Score"
    ])

    final_df = pd.concat([client_df, result_df], axis=1)

    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        final_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    export_multi_match_details(client_df, ci_exact_lookup, exact_lookup,
                               entity_lookup, norm_lookup, norm_entity_lookup,
                               file_path)

    output_file = file_path.replace(".xlsx", "_output.xlsx")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        final_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    print("✅ Main-Matching Completed")
    print("✅ Multi-Matching Completed")
    print("🗄️ Output Files Added To Repository")

    # =============================
# CLEAN
# =============================
def clear_results(file_path):
    client_df = pd.read_excel(file_path, sheet_name="Client Data", engine='openpyxl')
    db_df = pd.read_excel(file_path, sheet_name="Database Data", engine='openpyxl')

    client_df = client_df.iloc[:, :3]

    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        client_df.to_excel(writer, sheet_name="Client Data", index=False)
        db_df.to_excel(writer, sheet_name="Database Data", index=False)

    print("✅ Reset Completed")

    end_time = time.time()
    print(f"⏱ End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")


# =============================
# MAIN
# =============================
if __name__ == "__main__":
    write_results("matching_file.xlsx")
    clear_results("matching_file.xlsx")
