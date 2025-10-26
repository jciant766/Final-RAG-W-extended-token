# ⚡ Quick RAG Test Checklist

## 🎯 5-Minute Daily Test

### 1. Basic Functionality (2 min)
```
Query: "What is a trader?"
✓ Gets results?
✓ Intent = Definition?
✓ Top result = Commercial Code Art. 4?
✓ AI overview generated?
```

### 2. Multi-Document Test (2 min)
```
Query: "company director duties"
✓ Gets results?
✓ Results from Companies Act (not Commercial Code)?
✓ Multiple relevant articles?
✓ Citations have page numbers?
```

### 3. Quick Accuracy Check (1 min)
```
Click "Read full article" on top result
✓ Article text makes sense?
✓ AI summary matches article?
✓ No obvious hallucinations?
```

**PASS = All checkmarks ✓**
**FAIL = Missing any checkmark → Run full test protocol**

---

## 🚨 Red Flags to Watch For

| Issue | What It Looks Like | Action |
|-------|-------------------|--------|
| **No Results** | "Found 0 results" for valid query | Check database, run full test |
| **Wrong Document** | Asks about Companies Act, gets Commercial Code | Check document attribution logic |
| **Hallucination** | AI mentions info not in expanded article | Critical - investigate immediately |
| **Low Confidence** | All queries < 50% confidence | Check embedding model |
| **Slow Response** | Takes > 10 seconds | Check API quotas, server load |

---

## 📊 Quick Scoring

After each test query:
- ✅ PASS: Answer is accurate, relevant, properly cited
- ⚠️ WARN: Minor issues but usable
- ❌ FAIL: Wrong info, hallucination, or completely irrelevant

**3 FAILs in a row = Stop and investigate!**

---

## 🔄 When to Run Full Test Protocol

- [ ] After any code changes
- [ ] After adding new documents
- [ ] After changing embedding model
- [ ] Weekly (even if no changes)
- [ ] When user reports an issue
- [ ] Before any production deployment

---

## 📝 One-Line Test Log

Keep a simple log:
```
[Date] | [Query] | [Pass/Warn/Fail] | [Notes]
2025-10-24 | "What is trader?" | PASS | Perfect
2025-10-24 | "Director duties" | PASS | Good results
2025-10-24 | "Bankruptcy" | WARN | Missing Art. 480
```

---

## 🎯 Success Criteria

Your RAG system is healthy if:
- ✅ 90%+ queries PASS
- ✅ < 5% queries FAIL
- ✅ No hallucinations detected
- ✅ Response time < 5 seconds
- ✅ Confidence scores 60-85% range

---

**Test early, test often, stay confident in your RAG!** 🚀


