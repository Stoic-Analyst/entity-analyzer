In an excel sheet there are two tabs/sheets.
Name of the first sheet is Client Data where three columns have been provided by the client:
Column A: Company Name
Column B: Entity Name
Name of the second sheet is Database Data where three columns have been populated from sql database:
Column A: Company Name
Column B: Company ID
Column C: Entity Name
python does the following:
1. Does a 5 tier matching system in hierarchal order.
a. First tier is exact company + entity names match of data in sheet 1 with sheet 2
b. Second tier is for the entities not matched in tier 1, an exact first lookup of entity name in sheet 1 with entity name in sheet 2, also calculate count of exact matches in sheet 2
c. Third tier is for entites not matched in first two tiers, a "Normalise" function that trims spaces,removes prefixes like "State Of" and "Republic of", and Suffixes like "Ltd:" or "Inc" etc, makes names lower case to make it case insensitive, removes special characters and accents on alphbets and ASCII characters from entity names on both sheets and then perform a match at company plus entity level.
d. Fourth tier is for entites not matched in first three tiers, a "Normalise" function that trims spaces,removes prefixes like "State Of" and "Republic of", and Suffixes like "Ltd:" or "Inc" etc, makes names lower case to make it case insensitive, removes special characters and accents on alphbets and ASCII characters from entity names on both sheets and then find the first match at entity level and calculate the match count in case there are multiple matches
d. Fifth tier is for entites not matched in first four tiers, perform a fuzzy lookup similar to power query fuzzy lookup at 85% similarity score.
2.After storing all of this in a scripting dictionary, please populate the following columns in Sheet1:
a. Column C: Database Company ID
b. Column D: Database Company Name
c. Column E: Database Entity Name
d. Column F: Match Type:
First Tier:Exact Company + Entity Match
Second TIer: Exact Entity Mtach
Third Tier: Normalized Company + Entity Match
Fourth Tier: Normalized ENtity Match
Fifth Tier: Fuzzy Match
Write "No Match" for entites not found in any tier
e. Column G: Matches Count (For matches in Second and Fourth tier)
f. Column H: Similarity Score (For Fuzzy lookup)
3. After the previous step please export the data from sheet 1 in a new workbook
4. After the previous step clear contents in Column C through H from Sheet 1, with the headers
5. Please make sure to write the code in a way that eact tier, the option export and option to clear data are in different buttons.



✅ 🚀 Summary
This solution gives you:
✔ Structured 5-tier logic
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

1. Open Command Prompt (CMD) using windows key + r and install the following ext libs after making sure you are in correct path :

 pip install pandas openpyxl rapidfuzz unidecode xlwing
 
  pip install tqdm
 
 2. Next copy your folder's path and run the below in cmd prompt as an example to reach your project directory:
 
 cd "C:\Users\YourName\Documents\Entity Analyzer"
 
 RECURRING STEP
 
 3. Next line run:
 
 python excel_match.py
 
 Open output file createdin folder  to view result