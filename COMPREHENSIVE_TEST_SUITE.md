# 🚀 COMPREHENSIVE RAG TESTING SUITE
## 40+ Questions to Thoroughly Test Your Legal RAG System

---

## 🎯 HOW TO USE THIS TEST SUITE

### Quick Start:
1. Open http://localhost:8502
2. Copy questions from below (one at a time)
3. Paste into search box and click "Search"
4. Review results for accuracy, relevance, and proper citations
5. Mark each test as ✅ PASS / ⚠️ WARN / ❌ FAIL

### Success Criteria:
- **✅ PASS**: Accurate answer, correct citations, relevant articles, no hallucinations
- **⚠️ WARN**: Mostly correct but missing some info or minor citation issues
- **❌ FAIL**: Wrong answer, hallucination, or completely irrelevant results

### Target: 85%+ PASS rate for production readiness

---

## 📚 CATEGORY 1: DEFINITIONS & BASIC CONCEPTS
*Tests if system can accurately retrieve and explain legal terms*

### Commercial Code Definitions:
1. **What is a trader?**
   - Expected: Commercial Code Art. 4
   - Should get exact definition with profession requirement

2. **Define acts of trade**
   - Expected: Commercial Code Art. 5-6
   - Should list categories of commercial activities

3. **What is commercial representation?**
   - Expected: Commercial Code provisions on agents
   - Should explain agent-principal relationships

4. **What is a bill of exchange?**
   - Expected: Commercial Code Part II
   - Should define negotiable instruments

### Companies Act Definitions:
5. **What is a private limited liability company?**
   - Expected: Companies Act early articles
   - Should explain LLC structure and characteristics

6. **Define share capital**
   - Expected: Companies Act capital provisions
   - Should explain authorized vs issued capital

7. **What is a company secretary and what are their duties?**
   - Expected: Companies Act Art. on company officers
   - Should list qualifications and responsibilities

8. **What is the meaning of "shadow director"?**
   - Expected: Companies Act director definitions
   - Should explain indirect control concept

---

## ⚙️ CATEGORY 2: PROCEDURES & PROCESSES
*Tests if system can explain step-by-step legal processes*

### Company Formation & Operations:
9. **How do I register a new company in Malta?**
   - Expected: Companies Act registration articles
   - Should outline registration steps and requirements

10. **What are the steps for holding an AGM?**
    - Expected: Companies Act Art. 129+
    - Should list notice, quorum, voting requirements

11. **How does a company change its name?**
    - Expected: Companies Act amendment procedures
    - Should explain resolution and registration process

12. **What is the procedure for increasing share capital?**
    - Expected: Companies Act capital alteration provisions
    - Should explain resolution and filing requirements

### Commercial Procedures:
13. **How is bankruptcy declared?**
    - Expected: Commercial Code Art. 477+
    - Should explain conditions and process

14. **What is the process for protesting a bill of exchange?**
    - Expected: Commercial Code negotiable instruments section
    - Should explain notarial protest procedures

15. **How are commercial disputes resolved?**
    - Expected: Commercial Code dispute resolution provisions
    - Should mention courts, arbitration, jurisdiction

---

## 📋 CATEGORY 3: REQUIREMENTS & OBLIGATIONS
*Tests if system can identify legal requirements and compliance obligations*

### Director & Officer Duties:
16. **What are the duties of company directors?**
    - Expected: Companies Act Art. 136A, 137, 143
    - Should list fiduciary duties, care standards

17. **What are the reporting obligations for directors?**
    - Expected: Companies Act reporting provisions
    - Should mention annual returns, financial statements

18. **What conflicts of interest rules apply to directors?**
    - Expected: Companies Act conflict provisions
    - Should explain disclosure and approval requirements

### Company Compliance:
19. **What records must a company maintain?**
    - Expected: Companies Act record-keeping provisions
    - Should list registers, minutes, accounts

20. **What are the requirements for dividend distributions?**
    - Expected: Companies Act Art. 123-125
    - Should explain solvency test and restrictions

21. **What are the requirements for a company to give financial assistance?**
    - Expected: Companies Act financial assistance provisions
    - Should explain whitewash procedure if applicable

22. **What are beneficial ownership register requirements?**
    - Expected: Companies Act + S.L. 386.16 or 386.22
    - Should explain UBO identification and reporting

---

## 🔍 CATEGORY 4: SPECIFIC ARTICLE LOOKUPS
*Tests if system can retrieve specific articles correctly*

23. **Show me Article 4 of the Commercial Code**
    - Expected: Commercial Code Art. 4 (trader definition)
    - Test: Does it distinguish from Companies Act Art. 4?

24. **What does Article 136A of the Companies Act say?**
    - Expected: Companies Act Art. 136A (director duties)
    - Should provide exact article text

25. **Find Article 123 about dividends**
    - Expected: Companies Act Art. 123
    - Should recognize context clue "dividends"

26. **What is in Article 477 of the Commercial Code?**
    - Expected: Commercial Code Art. 477 (bankruptcy)
    - Should provide bankruptcy provisions

---

## 🧩 CATEGORY 5: MULTI-DOCUMENT QUERIES
*Tests if system can search across multiple legal documents*

27. **What are all the rules about cell companies?**
    - Expected: Companies Act + S.L. 386.22
    - Should synthesize from multiple sources

28. **Tell me about protected cell companies**
    - Expected: Companies Act + relevant S.L.
    - Should explain PCC structure and regulations

29. **What are the rules for incorporated cell companies?**
    - Expected: Companies Act + S.L. 386.22
    - Should distinguish ICC from PCC

30. **What regulations apply to investment services companies?**
    - Expected: Multiple S.L. under 386
    - Should identify relevant subsidiary legislation

---

## 🤔 CATEGORY 6: AMBIGUOUS & CHALLENGING QUERIES
*Tests system's ability to disambiguate and handle complex queries*

31. **Article 4**
    - Challenge: Exists in BOTH Commercial Code and Companies Act
    - Expected: Should show BOTH or prioritize based on context

32. **Director duties**
    - Challenge: Could mean company directors OR partnership directors
    - Expected: Should prioritize Companies Act (more common)

33. **Bankruptcy**
    - Challenge: Individual vs corporate insolvency
    - Expected: Should cover Commercial Code provisions primarily

34. **Share transfer**
    - Challenge: Could be procedural, requirements, or restrictions
    - Expected: Should synthesize multiple aspects

35. **Company formation**
    - Challenge: Very broad topic
    - Expected: Should provide comprehensive overview

---

## 💰 CATEGORY 7: FINANCIAL & ACCOUNTING
*Tests knowledge of financial regulations and requirements*

36. **What is the solvency test for distributions?**
    - Expected: Companies Act solvency provisions
    - Should explain balance sheet and cash flow tests

37. **What are the rules for issuing debentures?**
    - Expected: Companies Act debt provisions
    - Should explain security and registration

38. **Can a company purchase its own shares?**
    - Expected: Companies Act share buyback provisions
    - Should explain conditions and restrictions

39. **What are the requirements for audited accounts?**
    - Expected: Companies Act audit provisions
    - Should explain thresholds and exemptions

40. **What are the capital maintenance rules?**
    - Expected: Companies Act capital provisions
    - Should explain minimum capital, distributions, reductions

---

## ⚖️ CATEGORY 8: PENALTIES & ENFORCEMENT
*Tests if system can identify legal consequences*

41. **What are the penalties for late filing of annual returns?**
    - Expected: Companies Act penalty provisions
    - Should specify fines and sanctions

42. **What happens if a director breaches their duties?**
    - Expected: Companies Act liability provisions
    - Should explain civil and criminal consequences

43. **What are the consequences of trading while insolvent?**
    - Expected: Commercial Code / Companies Act insolvency provisions
    - Should mention wrongful trading liability

---

## 🌐 CATEGORY 9: CROSS-BORDER & SPECIAL CASES
*Tests understanding of international and special entity rules*

44. **What are the rules for foreign companies operating in Malta?**
    - Expected: Companies Act foreign company provisions
    - Should explain registration and compliance

45. **What is a European company (SE)?**
    - Expected: Relevant S.L. implementing EU regulations
    - Should explain SE structure and requirements

46. **What are the rules for single member companies?**
    - Expected: Companies Act single member provisions
    - Should explain special requirements

---

## 🔬 CATEGORY 10: EDGE CASES & STRESS TESTS
*Tests system limits and error handling*

47. **Article 9999 of the Commercial Code**
    - Challenge: Non-existent article
    - Expected: Should say "not found" or "insufficient information"

48. **What is the legal definition of a unicorn company?**
    - Challenge: Not a legal term in corpus
    - Expected: Should respond with insufficient information

49. **Show me all articles about blockchain**
    - Challenge: Modern term likely not in corpus
    - Expected: Should handle gracefully with no results

50. **What does the law say about AI-generated contracts?**
    - Challenge: Topic not covered in corpus
    - Expected: Should indicate insufficient information

---

## 📊 SCORING SHEET

Use this to track your testing progress:

```
CATEGORY 1: DEFINITIONS (8 questions)
[ ] Q1  [ ] Q2  [ ] Q3  [ ] Q4  [ ] Q5  [ ] Q6  [ ] Q7  [ ] Q8
Pass Rate: __/8 = __%

CATEGORY 2: PROCEDURES (7 questions)
[ ] Q9  [ ] Q10 [ ] Q11 [ ] Q12 [ ] Q13 [ ] Q14 [ ] Q15
Pass Rate: __/7 = __%

CATEGORY 3: REQUIREMENTS (7 questions)
[ ] Q16 [ ] Q17 [ ] Q18 [ ] Q19 [ ] Q20 [ ] Q21 [ ] Q22
Pass Rate: __/7 = __%

CATEGORY 4: SPECIFIC ARTICLES (4 questions)
[ ] Q23 [ ] Q24 [ ] Q25 [ ] Q26
Pass Rate: __/4 = __%

CATEGORY 5: MULTI-DOCUMENT (4 questions)
[ ] Q27 [ ] Q28 [ ] Q29 [ ] Q30
Pass Rate: __/4 = __%

CATEGORY 6: AMBIGUOUS (5 questions)
[ ] Q31 [ ] Q32 [ ] Q33 [ ] Q34 [ ] Q35
Pass Rate: __/5 = __%

CATEGORY 7: FINANCIAL (5 questions)
[ ] Q36 [ ] Q37 [ ] Q38 [ ] Q39 [ ] Q40
Pass Rate: __/5 = __%

CATEGORY 8: PENALTIES (3 questions)
[ ] Q41 [ ] Q42 [ ] Q43
Pass Rate: __/3 = __%

CATEGORY 9: CROSS-BORDER (3 questions)
[ ] Q44 [ ] Q45 [ ] Q46
Pass Rate: __/3 = __%

CATEGORY 10: EDGE CASES (4 questions)
[ ] Q47 [ ] Q48 [ ] Q49 [ ] Q50
Pass Rate: __/4 = __%

-----------------------------------
OVERALL PASS RATE: __/50 = __%
-----------------------------------

FINAL GRADE:
- 90-100%: EXCELLENT ⭐⭐⭐⭐⭐
- 80-89%:  VERY GOOD ⭐⭐⭐⭐
- 70-79%:  GOOD ⭐⭐⭐
- 60-69%:  FAIR ⭐⭐
- Below 60%: NEEDS WORK ⭐
```

---

## 🎯 PRIORITY TESTING ORDER

If you have limited time, test in this order:

### HIGH PRIORITY (Must Pass):
1. Q1 (What is a trader?)
2. Q16 (Director duties)
3. Q9 (Company registration)
4. Q23 (Article 4 Commercial Code)
5. Q27 (Cell companies - multi-doc)

### MEDIUM PRIORITY (Should Pass):
6. Q20 (Dividend requirements)
7. Q13 (Bankruptcy procedure)
8. Q22 (Beneficial ownership)
9. Q32 (Ambiguous: Director duties)
10. Q36 (Solvency test)

### LOW PRIORITY (Nice to Pass):
11. All remaining questions for comprehensive testing

---

## 🔄 QUICK TEST PROTOCOL

For each question:

1. **Enter query** in http://localhost:8502
2. **Check intent** - Does detected intent make sense?
3. **Check results** - Are top 3 results relevant?
4. **Check citations** - Document, article, and page correct?
5. **Read full article** - Click to verify accuracy
6. **Check AI summary** - No hallucinations? Matches source?
7. **Mark result** - ✅ PASS / ⚠️ WARN / ❌ FAIL

---

## 🚨 CRITICAL FAILURES

Stop testing immediately and investigate if you see:
- ❌ 3+ hallucinations (AI inventing information)
- ❌ 5+ wrong document citations in a row
- ❌ System crashes or errors
- ❌ No results for 5+ valid queries
- ❌ All confidence scores below 40%

---

## 📝 TESTING NOTES TEMPLATE

```
Test Date: _______________
Tester: _________________
System Version: __________

HIGHLIGHTS:
- Strongest categories: _______________
- Weakest categories: ________________
- Surprising successes: ______________
- Unexpected failures: _______________

KEY ISSUES FOUND:
1. _________________________________
2. _________________________________
3. _________________________________

RECOMMENDED IMPROVEMENTS:
1. _________________________________
2. _________________________________
3. _________________________________

OVERALL ASSESSMENT:
[ ] Production Ready
[ ] Ready with minor tweaks
[ ] Needs significant work
[ ] Not ready for production

Notes: ____________________________
____________________________________
____________________________________
```

---

## ✅ CERTIFICATION

After completing this comprehensive test suite:

```
═══════════════════════════════════════
    MALTA LEGAL RAG SYSTEM
    COMPREHENSIVE TEST CERTIFICATION
═══════════════════════════════════════

Tested By: ____________________
Date: ________________________
Total Questions: 50
Questions Tested: _____
Pass Rate: _____%

CATEGORY BREAKDOWN:
Definitions:     ___% (___/8)
Procedures:      ___% (___/7)
Requirements:    ___% (___/7)
Specific Lookup: ___% (___/4)
Multi-Document:  ___% (___/4)
Ambiguous:       ___% (___/5)
Financial:       ___% (___/5)
Penalties:       ___% (___/3)
Cross-Border:    ___% (___/3)
Edge Cases:      ___% (___/4)

CRITICAL METRICS:
Hallucinations Detected: ____
Wrong Citations: ____
System Errors: ____
Avg Confidence Score: ____%
Avg Response Time: ____ sec

FINAL RECOMMENDATION:
[ ] PRODUCTION READY
[ ] READY WITH MINOR IMPROVEMENTS
[ ] NEEDS SIGNIFICANT WORK
[ ] NOT READY

Signature: ___________________
═══════════════════════════════════════
```

---

**🎯 TIP**: Test 10 questions per session to avoid fatigue. This comprehensive suite should take 3-5 sessions (30-60 minutes total) to complete thoroughly.

**🚀 GOOD LUCK TESTING! You're building something awesome!** 🇲🇹⚖️



