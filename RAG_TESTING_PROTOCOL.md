# 🧪 RAG System Testing & Verification Protocol

## Purpose
This document provides a systematic approach to test and verify the accuracy of your Malta Legal RAG system responses.

---

## 🎯 TEST CATEGORIES

### Category 1: Single Document Queries
**Purpose**: Verify system retrieves correct info from one specific law

### Category 2: Multi-Document Queries  
**Purpose**: Verify system can search across different laws

### Category 3: Ambiguous Queries
**Purpose**: Verify system disambiguates correctly

### Category 4: Complex Legal Queries
**Purpose**: Verify system synthesizes multiple articles

---

## 📋 TESTING TEMPLATE

### STEP 1: PREPARE TEST QUERY
```
Query: [Your legal question]
Expected Document(s): [Which law should answer this?]
Expected Article Range: [Rough article numbers if known]
Expected Intent: [Definition/Procedural/Requirement/Penalty/Temporal]
```

### STEP 2: EXECUTE QUERY
1. Open http://localhost:8502
2. Enter your query in the search box
3. Click "Search"
4. Wait for results

### STEP 3: RECORD RESPONSE
```
RESPONSE RECEIVED:
------------------
Intent Detected: [What the system detected]
Results Found: [Number of results]
Confidence: [AI Overview confidence %]

Top 3 Citations:
1. [Document] [Article] (Page X) - [Match %]
2. [Document] [Article] (Page X) - [Match %]
3. [Document] [Article] (Page X) - [Match %]

AI Overview Summary:
[Copy the AI-generated summary here]
```

### STEP 4: VERIFY ACCURACY
For each citation, click "Read full article" and check:

```
CITATION 1 VERIFICATION:
------------------------
Article: [Document] [Article Number]
Expected Page: [From citation]

✓ Article exists in source? [YES/NO]
✓ Page number correct? [YES/NO]
✓ Content relevant to query? [YES/NO/PARTIAL]
✓ AI summary accurately reflects article? [YES/NO/HALLUCINATION]
✓ Did it cite the RIGHT document? [YES/NO - Check for confusion]

Key Quote from Source:
"[Copy exact text from article]"

AI Interpretation:
"[What AI said about this]"

Match Quality: [EXACT/PARAPHRASE/WRONG/HALLUCINATION]
```

### STEP 5: CROSS-CHECK DOCUMENT ATTRIBUTION
```
Document Attribution Check:
---------------------------
Query mentioned: [Commercial Code / Companies Act / S.L. X]
System returned: [Which documents?]

✓ Correct law? [YES/NO]
✓ No confusion between similar articles? [YES/NO]
✓ Proper disambiguation? [YES/NO]

Example Issues to Watch For:
- Commercial Code Art. 4 confused with Companies Act Art. 4?
- Wrong S.L. number cited?
- Mixed up articles from different regulations?
```

### STEP 6: SCORE THE RESPONSE
```
SCORING (1-10):
---------------
Accuracy: [__/10]
- 10: Perfectly accurate, no errors
- 7-9: Mostly accurate, minor issues
- 4-6: Partially accurate, missing key info
- 1-3: Mostly wrong or hallucinated

Completeness: [__/10]
- 10: All relevant articles found
- 7-9: Most key articles found
- 4-6: Missing important articles
- 1-3: Missed most relevant content

Relevance: [__/10]
- 10: All results highly relevant
- 7-9: Most results relevant
- 4-6: Mixed relevance
- 1-3: Mostly irrelevant

Citation Quality: [__/10]
- 10: All citations correct, precise, helpful
- 7-9: Citations mostly correct
- 4-6: Some citation errors
- 1-3: Many citation errors

Intent Detection: [__/10]
- 10: Perfect intent classification
- 7-9: Close enough
- 4-6: Wrong but understandable
- 1-3: Completely wrong

OVERALL GRADE: [__/50] → [EXCELLENT/GOOD/FAIR/POOR/FAIL]
```

### STEP 7: DOCUMENT ISSUES
```
ISSUES FOUND:
-------------
[ ] Hallucination (AI made up info not in source)
[ ] Missing Information (Source has info AI didn't mention)
[ ] Wrong Citation (Cited wrong article/page)
[ ] Document Confusion (Mixed up different laws)
[ ] Low Relevance (Results not related to query)
[ ] Intent Misclassification (Wrong intent detected)
[ ] No Results (Should have found something)
[ ] Too Many Results (Noise in results)

Details:
[Describe each issue in detail]

Expected vs Actual:
Expected: [What should have happened]
Actual: [What actually happened]
```

---

## 🧪 RECOMMENDED TEST QUERIES

### **TEST SET 1: Single Document - Commercial Code**
```
1. "What is a trader?"
   Expected: Commercial Code Art. 4
   Expected Intent: Definition

2. "What are acts of trade?"
   Expected: Commercial Code Art. 5-6
   Expected Intent: Definition

3. "Bankruptcy procedures"
   Expected: Commercial Code Art. 477+
   Expected Intent: Procedural

4. "Bills of exchange requirements"
   Expected: Commercial Code Part II
   Expected Intent: Requirement
```

### **TEST SET 2: Single Document - Companies Act**
```
5. "What are the duties of company directors?"
   Expected: Companies Act Art. 136A, 137, 143
   Expected Intent: Requirement

6. "How to register a company in Malta?"
   Expected: Companies Act Art. 63+
   Expected Intent: Procedural

7. "Solvency test for dividend distributions"
   Expected: Companies Act Art. 123-125
   Expected Intent: Definition/Requirement

8. "AGM and EGM requirements for private companies"
   Expected: Companies Act Art. 129+
   Expected Intent: Requirement
```

### **TEST SET 3: Multi-Document Queries**
```
9. "beneficial ownership register requirements"
   Expected: Companies Act + S.L. 386.16/386.22
   Expected Intent: Requirement

10. "cell company regulations"
    Expected: Companies Act + S.L. 386.22
    Expected Intent: Definition/Requirement
```

### **TEST SET 4: Ambiguous Queries**
```
11. "Article 4"
    Challenge: Exists in BOTH Commercial Code and Companies Act
    Expected: System should show BOTH or ask for clarification

12. "director duties"
    Challenge: Could be Companies Act OR commercial partnership
    Expected: Should prioritize Companies Act (more relevant)
```

### **TEST SET 5: Complex Synthesis**
```
13. "What are all the reporting obligations for company directors?"
    Expected: Multiple articles from Companies Act (Art. 136A, 177, etc.)
    Expected: AI should synthesize into coherent list

14. "When can a company be declared bankrupt and what are the consequences?"
    Expected: Commercial Code bankruptcy provisions + Companies Act winding up
    Expected: AI should explain process and outcomes
```

---

## 🎯 VERIFICATION CHECKLIST

### Before Marking Test as PASSED:
- [ ] All citations are accurate (correct article, page, document)
- [ ] No hallucinations (all info traceable to source)
- [ ] No document confusion (correct law cited)
- [ ] Relevant results (high match scores make sense)
- [ ] Complete answer (didn't miss obvious articles)
- [ ] Proper intent detection (makes sense for query type)
- [ ] AI overview is coherent and well-structured
- [ ] Page numbers are correct and helpful

### Red Flags (Mark as FAILED):
- [ ] Hallucination detected (info not in any source)
- [ ] Wrong document cited (e.g., cited Commercial Code when answer is in Companies Act)
- [ ] Article confusion (e.g., mixed up Art. 4 from different laws)
- [ ] No results when there should be
- [ ] All results irrelevant (< 50% relevance)
- [ ] Wrong intent by 2+ categories

---

## 📊 GRADING SCALE

### Per Query:
- **45-50/50**: EXCELLENT - Production ready
- **40-44/50**: GOOD - Minor improvements needed
- **30-39/50**: FAIR - Significant improvements needed
- **20-29/50**: POOR - Major issues to fix
- **0-19/50**: FAIL - System not working properly

### Overall System (after 10+ queries):
- **90%+ EXCELLENT**: System is production-ready
- **75-89% GOOD**: System works well, minor tuning needed
- **60-74% FAIR**: System functional but needs improvement
- **40-59% POOR**: Significant issues, needs major work
- **<40% FAIL**: System not ready for use

---

## 📝 EXAMPLE COMPLETED TEST

### Query: "What is a trader?"

**STEP 1: PREPARATION**
```
Query: "What is a trader?"
Expected Document: Commercial Code (Cap. 13)
Expected Article: Art. 4
Expected Intent: Definition
```

**STEP 2: RESPONSE RECEIVED**
```
Intent Detected: Definition ✓
Results Found: 5
Confidence: 71%

Top Citations:
1. Commercial Code Art. 4 (Page 7) - 84%
2. Commercial Code Art. 477 (Page 81) - 66%
3. Commercial Code Art. 7 (Page 7) - 64%
```

**STEP 3: VERIFICATION**

Citation 1 - Commercial Code Art. 4:
```
✓ Article exists? YES
✓ Page correct? YES (Page 7)
✓ Relevant? YES (Primary definition)
✓ AI accurate? YES

Source Text: "The term 'trader' means any person who, by profession, 
exercises acts of trade in his own name..."

AI Summary: "A 'trader' is defined as any person who, by profession, 
exercises acts of trade in their own name..."

Match: EXACT PARAPHRASE ✓
```

Citation 2 - Commercial Code Art. 477:
```
✓ Article exists? YES
✓ Page correct? YES (Page 81)
✓ Relevant? YES (Bankruptcy context)
✓ AI accurate? YES

Context: Broader definition for bankruptcy purposes
Match: ACCURATE ✓
```

**STEP 4: DOCUMENT ATTRIBUTION**
```
✓ Correct law cited? YES (All Commercial Code)
✓ No confusion? YES (Didn't cite Companies Act by mistake)
✓ Proper disambiguation? N/A (Only one law has this definition)
```

**STEP 5: SCORING**
```
Accuracy: 10/10 (Perfect)
Completeness: 9/10 (Got main definition + context)
Relevance: 10/10 (All results relevant)
Citation Quality: 10/10 (Precise, correct, helpful)
Intent Detection: 10/10 (Correctly identified as Definition)

OVERALL: 49/50 → EXCELLENT ✓
```

**STEP 6: ISSUES**
```
None found. System performed excellently.
```

---

## 🔄 CONTINUOUS TESTING

### Weekly Testing Routine:
1. Run 5 random queries from test sets
2. Check for any degradation
3. Test new edge cases discovered by users
4. Verify fixes for previously reported issues

### Monthly Deep Testing:
1. Run all test sets (20+ queries)
2. Calculate overall accuracy score
3. Document any new issues
4. Update test sets based on real user queries

---

## 📚 RESOURCES

### To Manually Verify Citations:
1. Open source document: `ocr/output/[Document].txt`
2. Search for article number in file
3. Compare against RAG response
4. Check page markers in text files

### To Check Database:
```bash
python -c "import chromadb; c = chromadb.PersistentClient(path='./chroma_db'); col = c.get_collection('malta_code_v2'); print(f'Total chunks: {col.count()}')"
```

### To View Logs:
- Query logs: `debug_logs/queries.log`
- Search logs: `debug_logs/search_engine.log`
- AI logs: `debug_logs/ai_assistant.log`

---

## ✅ CERTIFICATION

After completing comprehensive testing:

```
SYSTEM CERTIFICATION

Tested By: [Your Name]
Date: [Date]
Total Queries Tested: [Number]
Overall Accuracy: [%]
Overall Grade: [EXCELLENT/GOOD/FAIR/POOR/FAIL]

Critical Issues: [None / List]
Recommendation: [PRODUCTION READY / NEEDS WORK / NOT READY]

Signature: ___________________
```

---

**Use this protocol for every major update or monthly verification!**


