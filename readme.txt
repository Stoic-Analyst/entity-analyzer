In an excel sheet there are two tabs/sheets.
Name of the first sheet is Client Data where three columns have been provided by the client:
Column A: Company Name
Column B: Entity Name
Name of the second sheet is Database Data where three columns have been populated from sql database:
Column A: Company Name
Column B: Company ID
Column C: Entity Name
python does the following:
1. Does a 6 tier matching system in hierarchal order.
a. First tier is exact company + entity names + identifier match of data in sheet 1 with sheet 2
b. Next is exact company + entity names match of data in sheet 1 with sheet 2
c. Next is for the entities not matched in tier 1, an exact first lookup of entity name in sheet 1 with entity name in sheet 2, also calculate count of exact matches in sheet 2
d. Then for entites not matched in first two tiers, a "Normalise" function that trims spaces,removes prefixes like "State Of" and "Republic of", and Suffixes like "Ltd:" or "Inc" etc, makes names lower case to make it case insensitive, removes special characters and accents on alphbets and ASCII characters from entity names on both sheets and then perform a match at company plus entity level.
e. Then for entites not matched in first three tiers, a "Normalise" function that trims spaces,removes prefixes like "State Of" and "Republic of", and Suffixes like "Ltd:" or "Inc" etc, makes names lower case to make it case insensitive, removes special characters and accents on alphbets and ASCII characters from entity names on both sheets and then find the first match at entity level and calculate the match count in case there are multiple matches
d.Then for entites not matched in first four tiers, perform a fuzzy lookup similar to power query fuzzy lookup at 85% similarity score.
2.After storing all of this in a scripting dictionary, please populate the following columns in Sheet1:
a. Column C: Database Company ID
b. Column D: Database Company Name
c. Column E: Database Entity Name
d. Column F: Database Identifier
e. Column F: Match Type
e. Column G: Matches Count
f. Column H: Similarity Score (For Fuzzy lookup)



✅ 🚀 Summary
This solution gives you:
✔ Structured 6-tier logic
✔ High-performance matching
✔ Excel-integrated workflow
✔ Button-driven execution
✔ Clean export + reset capabilities


Tools Needed:

✅ 🔧Python 3.13.13 64 bit
✅ 🔧VS Code
✅ 🔧 Shell/Terminal/Command Propmt
✅ 🔧 Py Libraries
✅ 🔧 Project Files

One time Steps;-

Save the documents/files in a folder titled "Entity Analyzer" 

Open Command Prompt (CMD) using windows key + r and install the following ext libs after making sure you are in correct path.
Write:
cd "C:\Users\abhishek.sharma1\OneDrive - S&P Global\Entity Analyzer"
py -3.13 -m venv venv (do once not everytime)
venv\Scripts\activate 
 pip install pandas openpyxl rapidfuzz unidecode tqdm xlwings (do once not everytime)
 python excel_match.py
 

 Open output file created in folder  to view result


 
For further analysis user the "Ent Analyzer" macro file.

Instructions:-
1. In hierarchal order press buttons Exact,Normalize and Fuzzy in sheet1 after pasting the client data in sheet1 and database data in sheet2 (Coulmn order my vary from excel file conected to python script)
2. Use export button in sheet 1 to export the result 
3. Create a new tab in exported sheet and paste database data there
