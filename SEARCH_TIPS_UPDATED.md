# Search Tips Updated with Real Questions

## Summary

The Streamlit search tips section has been updated with **47 authentic questions** based on the actual content of the legal documents in your database.

---

## What Changed

### Before
- Generic questions that may not match actual law content
- Questions about laws that might not be in the database
- No specific article references
- Not based on actual provisions

### After
- **47 questions** derived from actual law content
- Questions reference specific articles and provisions that exist
- Organized by legal practice area
- Based on real provisions found in the documents

---

## Questions Added (By Legal Area)

### **Stamp Duty & Property Transfer Tax (Cap. 364)** - 7 Questions
Based on: `364 - Duty on Documents and Transfers Act.txt`

Examples:
- "What is the duty rate on documents and transfers for residential property?"
- "What are the conditions for the 200,000 euro stamp duty exemption for first-time buyers?"
- "What is a structured arrangement for stamp duty purposes?"

**Real Content Referenced:**
- Article 2 (Definitions - "body of persons", "cohabitant")
- Article 32(4)(a) (First-time buyer relief)
- Structured arrangement provisions
- Commissioner for Revenue notice requirements

---

### **Notarial Profession (Cap. 55)** - 8 Questions
Based on: `55 - Notarial Profession and Notarial Archives Act.txt`

Examples:
- "What are the functions and powers of notaries according to Article 2?"
- "Can a notary practice as an advocate or work as a bank manager at the same time?"
- "What are the examination of title requirements for notaries under Article 84C?"

**Real Content Referenced:**
- Article 2 (Definition of office, powers and functions)
- Article 3 (Profession incompatibility)
- European Certificate of Succession powers
- Acts inter vivos and wills custody
- Mediator and Commissioner for Oaths functions
- Chief Notary to Government role

---

### **Money Laundering Prevention (Cap. 373)** - 7 Questions
Based on: `373 - Prevention of Money Laundering Act.txt`

Examples:
- "What is the maximum penalty for money laundering offences under Article 3?"
- "Can someone be convicted of money laundering without proving the underlying criminal activity?"
- "What are the sanctions for obliged entities who commit money laundering?"

**Real Content Referenced:**
- Article 3 (Offences and penalties)
- Maximum fine: 2,500,000 euro
- Maximum imprisonment: 18 years
- Aggravated offences within criminal organisations
- Additional sanctions for natural persons and bodies of persons
- Conviction without proving underlying activity
- Director liability provisions

---

### **EU Succession Regulation (650/2012)** - 3 Questions
Based on: `EU Succession Regulation - 650.2012.txt`

Examples:
- "What matters are excluded from the scope of EU Regulation 650/2012?"
- "Does the EU Succession Regulation apply to succession to estates of deceased persons?"

**Real Content Referenced:**
- Article 1 (Scope and application)
- Article 2 (Exclusions)
- Cross-border succession provisions

---

### **First-Time Buyers & Gozo Exemptions (S.L. 364.12)** - 5 Questions
Based on: `364.12 - First Time Buyers & Gozo Exemptions.txt`

Examples:
- "What is the deadline for final deed execution to qualify for first-time buyer exemption?"
- "Does acquisition of an undivided share of less than 25% count against first-time buyer status?"
- "What is the definition of residential property for Gozo exemption purposes?"

**Real Content Referenced:**
- 200,000 euro exemption (first-time buyers before 1 Jan 2024)
- 31 December 2023 final deed deadline
- 25% undivided share exception
- 30 square metre garage exception
- Pro-rata benefit calculation
- Residential property definition (includes garage within 500m)
- Gozo property reduced rate (2 euro per 100 euro)
- Notice submission deadlines

---

### **Tax on Property Transfers (S.L. 123.92)** - 3 Questions
Based on: `123.92 - Tax on Property Transfers Rules.txt`

Examples:
- "What is the reduced rate for property transfers made between 9 June 2020 and 1 January 2022?"
- "What conditions must be satisfied for the 1.50 euro per 100 euro reduced rate?"

**Real Content Referenced:**
- Temporary reduced rates during COVID period
- 1.50 euro per 100 euro rate on first 400,000 euro
- Conditions for exemption eligibility

---

### **Land Registration (Cap. 296)** - 3 Questions
Based on: `296 - Land Registration Act.txt`

**Real Content Referenced:**
- Registration requirements
- Required documents for Land Registrar
- Fees for registration and searches

---

### **Private Residential Leases (Cap. 604)** - 3 Questions
Based on: `604- Private Residential Leases Act.txt`

**Real Content Referenced:**
- Mandatory registration requirements
- Penalties for non-registration
- Tenant and landlord rights

---

### **Cohabitation Act (Cap. 614)** - 3 Questions
Based on: `614 - Cohabitation Act.txt`

**Real Content Referenced:**
- Definition of cohabitant
- Enrollment by public deed
- Rights and obligations

---

### **Civil Procedure (Cap. 12)** - 2 Questions
Based on: `12 - Code of Organization and Civil Procedure.txt`

**Real Content Referenced:**
- Civil litigation procedures
- Jurisdiction requirements

---

### **Income Tax (Cap. 123)** - 3 Questions
Based on: `123 - Income Tax Act.txt`

**Real Content Referenced:**
- Capital gains rules (S.L. 123.27)
- Property transfer exemptions
- UCA and vacant property provisions (S.L. 123.203)

---

## How Questions Were Generated

1. **Analyzed actual document content** - Read samples from key legal documents
2. **Identified common provisions** - Found frequently referenced articles and procedures
3. **Created specific questions** - Referenced exact article numbers and provisions
4. **Organized by practice area** - Grouped by legal domain for easy navigation
5. **Verified accuracy** - Cross-checked against actual document content

---

## Coverage

**Documents Analyzed:**
- 44 legal documents total
- 12 documents specifically sampled for questions
- 2,436 chunks in vector database

**Question Distribution:**
- Stamp Duty & Tax: 18 questions (38%)
- Notarial Practice: 8 questions (17%)
- AML/Compliance: 7 questions (15%)
- Other Practice Areas: 14 questions (30%)

---

## Benefits

### For Users:
- **Copy-paste ready questions** - Users can click and try real questions
- **Learn by example** - See what types of questions work well
- **Discover content** - Find out what laws are in the database
- **Practical guidance** - Real questions lawyers actually ask

### For System:
- **Test cases** - Built-in test queries for system validation
- **Quality assurance** - Verify AI responses against known provisions
- **Documentation** - Shows what the system can answer
- **Marketing** - Demonstrates system capabilities

---

## Testing Recommendations

Try these questions in Streamlit to verify:

**High-Priority Tests:**
1. "What is the maximum penalty for money laundering offences under Article 3 of Cap. 373?"
   - Should return: 2,500,000 euro fine or 18 years imprisonment

2. "What are the conditions for the 200,000 euro stamp duty exemption for first-time buyers?"
   - Should return: First property inter vivos, before 31 Dec 2023, notary declaration

3. "Can a notary practice as an advocate or work as a bank manager at the same time?"
   - Should return: No (Article 3 incompatibility provisions)

4. "Does acquisition of an undivided share of less than 25% count against first-time buyer status?"
   - Should return: No, not counted (specific proviso in S.L. 364.12)

---

## File Modified

**File:** [main.py:171-241](main.py)

**Section:** Search Tips & Context Optimization expander

**Lines Changed:** 70 lines (replaced generic questions with 47 specific questions)

---

**The search tips now reflect the actual content of your legal database!**
